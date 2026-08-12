from __future__ import annotations

import re
from datetime import datetime, timedelta
from itertools import product

from .data import AREA_TRAVEL_MINUTES, VENUES
from .models import (
    Itinerary,
    PlanRequest,
    RouteLeg,
    Stop,
    ValidationFailure,
    Venue,
)
from .tools.opening_hours import (
    DAY_ORDER,
    normalize_day,
    parse_clock_time,
    venue_open_for_interval,
)
from .tools.routing import get_route
from .validator import (
    failures_to_warning_messages,
    validate_itinerary,
    validation_has_errors,
)


Coordinates = tuple[float, float]

# Only this many preliminary plans are upgraded to live routing.
# This prevents hundreds of external routing calls.
LIVE_SHORTLIST_SIZE = 6


def fallback_travel_minutes(
    area_a: str,
    area_b: str,
) -> int:
    """
    Return an area-based estimate when coordinates are unavailable.
    """
    if area_a == area_b:
        return 8

    return AREA_TRAVEL_MINUTES.get(
        (area_a, area_b),
        AREA_TRAVEL_MINUTES.get(
            (area_b, area_a),
            35,
        ),
    )


def venue_coordinates(
    venue: Venue,
) -> Coordinates | None:
    if (
        venue.latitude is None
        or venue.longitude is None
    ):
        return None

    return (
        venue.latitude,
        venue.longitude,
    )


def calculate_leg_route(
    *,
    from_name: str,
    to_name: str,
    area_a: str,
    area_b: str,
    coordinates_a: Coordinates | None,
    coordinates_b: Coordinates | None,
    request: PlanRequest,
    prefer_live: bool = True,
) -> RouteLeg:
    """
    Build one normalized route leg.

    prefer_live=False:
        Use only PlanPilot's deterministic route estimate.
        No external API call is made.

    prefer_live=True:
        Use the routing provider when possible. The routing layer
        handles caching and deterministic fallback automatically.
    """
    if (
        coordinates_a is not None
        and coordinates_b is not None
    ):
        route = get_route(
            latitude_a=coordinates_a[0],
            longitude_a=coordinates_a[1],
            latitude_b=coordinates_b[0],
            longitude_b=coordinates_b[1],
            transport=request.transport,
            prefer_live=prefer_live,
        )

        return RouteLeg(
            from_name=from_name,
            to_name=to_name,
            duration_minutes=route.duration_minutes,
            distance_meters=route.distance_meters,
            mode=route.mode,
            geometry=route.geometry,
            provider=route.provider,
            fallback_used=route.fallback_used,
        )

    fallback_minutes = fallback_travel_minutes(
        area_a,
        area_b,
    )

    return RouteLeg(
        from_name=from_name,
        to_name=to_name,
        duration_minutes=fallback_minutes,
        distance_meters=0,
        mode=request.transport,
        geometry=[],
        provider="area_matrix",
        fallback_used=True,
    )


def venue_matches_food(
    venue: Venue,
    preferences: list[str],
) -> bool:
    """
    Check whether a restaurant matches at least one requested
    food preference.
    """
    if (
        venue.category != "restaurant"
        or not preferences
    ):
        return True

    wanted = {
        preference.lower()
        for preference in preferences
    }

    available = {
        tag.lower()
        for tag in venue.food_tags
    }

    return bool(
        wanted & available
    )


def get_requested_categories(
    request: PlanRequest,
) -> list[str]:
    categories: list[str] = []

    if "activity" in request.must_include:
        categories.append(
            "activity"
        )

    if "dinner" in request.must_include:
        categories.append(
            "restaurant"
        )

    if "dessert" in request.must_include:
        categories.append(
            "dessert"
        )

    if not categories:
        categories = [
            "activity",
            "restaurant",
        ]

    return categories


def get_candidates(
    category: str,
    request: PlanRequest,
    venues: list[Venue],
) -> list[Venue]:
    candidates = [
        venue
        for venue in venues
        if venue.category == category
    ]

    if category == "restaurant":
        candidates = [
            venue
            for venue in candidates
            if venue_matches_food(
                venue,
                request.food_preferences,
            )
        ]

    return candidates


def calculate_vibe_overlap(
    venues: list[Venue],
    requested_vibes: list[str],
) -> int:
    requested = {
        vibe.lower()
        for vibe in requested_vibes
    }

    return sum(
        len(
            {
                vibe.lower()
                for vibe in venue.vibe
            }
            & requested
        )
        for venue in venues
    )


def calculate_route_legs(
    *,
    request: PlanRequest,
    venues: list[Venue],
    start_coordinates: Coordinates | None,
    prefer_live: bool = True,
) -> list[RouteLeg]:
    """
    Calculate route legs from the starting point through every
    venue in itinerary order.
    """
    legs: list[RouteLeg] = []

    previous_name = request.start_area
    previous_area = request.start_area
    previous_coordinates = start_coordinates

    for venue in venues:
        current_coordinates = venue_coordinates(
            venue
        )

        leg = calculate_leg_route(
            from_name=previous_name,
            to_name=venue.name,
            area_a=previous_area,
            area_b=venue.area,
            coordinates_a=previous_coordinates,
            coordinates_b=current_coordinates,
            request=request,
            prefer_live=prefer_live,
        )

        legs.append(
            leg
        )

        previous_name = venue.name
        previous_area = venue.area
        previous_coordinates = current_coordinates

    return legs


def extract_weekday(
    date_text: str,
) -> str:
    """
    Extract a weekday from values such as:

    Friday
    This Friday
    Next Saturday
    """
    cleaned = (
        date_text
        .strip()
        .lower()
    )

    for weekday in DAY_ORDER:
        if re.search(
            rf"\b{re.escape(weekday)}\b",
            cleaned,
        ):
            return weekday

    normalized = normalize_day(
        cleaned
    )

    return (
        normalized
        or "friday"
    )


def build_start_datetime(
    request: PlanRequest,
) -> datetime:
    """
    Build a deterministic datetime anchor for itinerary scheduling.
    """
    weekday = extract_weekday(
        request.date
    )

    start_clock = parse_clock_time(
        request.start_time
    )

    if start_clock is None:
        start_clock = parse_clock_time(
            "17:00"
        )

    assert start_clock is not None

    monday_anchor = datetime(
        2024,
        1,
        1,
        start_clock.hour,
        start_clock.minute,
    )

    weekday_index = DAY_ORDER.index(
        weekday
    )

    return (
        monday_anchor
        + timedelta(
            days=weekday_index
        )
    )


def calculate_stop_schedule(
    *,
    request: PlanRequest,
    venues: list[Venue],
    legs: list[RouteLeg],
) -> tuple[
    list[datetime],
    list[str],
    list[str],
]:
    """
    Calculate arrivals and inspect venue opening-hour status.

    Returns:
        arrival_times
        confirmed_closed_venues
        unknown_hours_venues
    """
    current_datetime = build_start_datetime(
        request
    )

    arrival_times: list[datetime] = []
    closed_venues: list[str] = []
    unknown_hours: list[str] = []

    for venue, leg in zip(
        venues,
        legs,
        strict=True,
    ):
        current_datetime += timedelta(
            minutes=leg.duration_minutes
        )

        arrival_times.append(
            current_datetime
        )

        departure_datetime = (
            current_datetime
            + timedelta(
                minutes=venue.duration_minutes
            )
        )

        weekday = current_datetime.strftime(
            "%A"
        )

        open_status = venue_open_for_interval(
            opening_hours=venue.opening_hours,
            weekday=weekday,
            arrival_time=current_datetime.time(),
            departure_time=departure_datetime.time(),
        )

        if open_status is False:
            closed_venues.append(
                venue.name
            )

        elif (
            open_status is None
            and venue.source == "geoapify"
        ):
            unknown_hours.append(
                venue.name
            )

        current_datetime = departure_datetime

    return (
        arrival_times,
        closed_venues,
        unknown_hours,
    )


def format_time(
    value: datetime,
) -> str:
    """
    Format an itinerary timestamp for user-facing explanations.
    """
    return (
        value.strftime(
            "%I:%M %p"
        )
        .lstrip("0")
    )


def plan_has_errors(
    plan: Itinerary,
) -> bool:
    """
    Return True when a plan contains at least one structured
    validation error.

    Warnings do not invalidate an itinerary.
    """
    return validation_has_errors(
        plan.validation_failures
    )


def build_itinerary(
    *,
    request: PlanRequest,
    chosen_venues: list[Venue],
    start_coordinates: Coordinates | None,
    prefer_live: bool,
) -> Itinerary:
    """
    Build, score, and validate one itinerary.

    This function is used twice:

    1. Preliminary phase
       prefer_live=False

    2. Shortlisted final phase
       prefer_live=True

    V2.3 attaches machine-readable ValidationFailure objects to
    every generated itinerary.
    """
    legs = calculate_route_legs(
        request=request,
        venues=chosen_venues,
        start_coordinates=start_coordinates,
        prefer_live=prefer_live,
    )

    (
        arrival_times,
        closed_venues,
        unknown_hours,
    ) = calculate_stop_schedule(
        request=request,
        venues=chosen_venues,
        legs=legs,
    )

    total_travel = sum(
        leg.duration_minutes
        for leg in legs
    )

    total_cost = (
        request.party_size
        * sum(
            venue.estimated_cost_per_person
            for venue in chosen_venues
        )
    )

    total_duration = (
        sum(
            venue.duration_minutes
            for venue in chosen_venues
        )
        + total_travel
    )

    vibe_overlap = calculate_vibe_overlap(
        venues=chosen_venues,
        requested_vibes=request.vibe,
    )

    budget_penalty = max(
        0,
        total_cost
        - request.budget_total,
    )

    long_leg_penalty = sum(
        max(
            0,
            leg.duration_minutes
            - request.max_leg_minutes,
        )
        for leg in legs
    )

    unknown_hours_penalty = (
        len(unknown_hours)
        * 3
    )

    score = (
        100
        + vibe_overlap * 8
        - total_travel * 0.7
        - budget_penalty * 1.5
        - long_leg_penalty
        - unknown_hours_penalty
    )

    schedule_summary = " → ".join(
        (
            f"{venue.name} "
            f"at {format_time(arrival)}"
        )
        for venue, arrival in zip(
            chosen_venues,
            arrival_times,
            strict=True,
        )
    )

    live_route_count = sum(
        1
        for leg in legs
        if not leg.fallback_used
    )

    fallback_route_count = (
        len(legs)
        - live_route_count
    )

    routing_reason = (
        f"{live_route_count} route legs "
        "used live routing data."
    )

    if fallback_route_count:
        routing_reason += (
            f" {fallback_route_count} "
            f"leg"
            f"{'s' if fallback_route_count != 1 else ''} "
            "used fallback estimates."
        )

    reasons = [
        (
            f"Matches {vibe_overlap} "
            "requested vibe tags."
        ),
        (
            f"Estimated at ${total_cost:.0f} "
            f"for {request.party_size} people."
        ),
        (
            f"Approximately {total_travel} "
            "minutes of estimated travel."
        ),
        routing_reason,
        (
            f"Estimated schedule: "
            f"{schedule_summary}."
        ),
    ]

    stops = [
        Stop(
            name=venue.name,
            category=venue.category,
            area=venue.area,
            estimated_cost=round(
                venue.estimated_cost_per_person
                * request.party_size,
                2,
            ),
            duration_minutes=venue.duration_minutes,
            latitude=venue.latitude,
            longitude=venue.longitude,
            formatted_address=venue.formatted_address,
            website=venue.website,
            opening_hours=venue.opening_hours,
            source=venue.source,
        )
        for venue in chosen_venues
    ]

    title = " → ".join(
        venue.name
        for venue in chosen_venues
    )

    # ----------------------------------------------------------
    # BUILD PROVISIONAL ITINERARY
    # ----------------------------------------------------------
    #
    # Validation needs the completed stops, route legs, cost,
    # duration, and routing metadata. We therefore construct the
    # itinerary first and validate it immediately afterward.

    itinerary = Itinerary(
        label="Candidate",
        title=title,
        stops=stops,
        total_cost=round(
            total_cost,
            2,
        ),
        total_duration_minutes=total_duration,
        estimated_travel_minutes=total_travel,
        score=round(
            score,
            2,
        ),
        route_legs=legs,
        validation_failures=[],
        reasons=reasons,
        warnings=[],
    )

    # ----------------------------------------------------------
    # STRUCTURED VALIDATION
    # ----------------------------------------------------------

    validation_result = validate_itinerary(
        request=request,
        itinerary=itinerary,
        closed_venues=closed_venues,
    )

    itinerary.validation_failures = (
        validation_result.failures
    )

    # Preserve compatibility with the existing Streamlit UI.
    itinerary.warnings = (
        failures_to_warning_messages(
            validation_result.failures
        )
    )

    # Preserve the existing planner behavior where fully clean
    # plans receive a score bonus.
    if not itinerary.validation_failures:
        itinerary.score = round(
            itinerary.score + 20,
            2,
        )

    return itinerary


def build_candidate_plans(
    request: PlanRequest,
    venues: list[Venue] | None = None,
    start_coordinates: Coordinates | None = None,
    prefer_live: bool = True,
) -> list[Itinerary]:
    """
    Generate all candidate combinations.

    prefer_live defaults to True to preserve direct-call behavior.

    build_plans() deliberately calls this with prefer_live=False
    during preliminary ranking to avoid excessive API calls.
    """
    candidate_source = (
        venues
        if venues is not None
        else VENUES
    )

    requested_categories = get_requested_categories(
        request
    )

    candidate_groups = [
        get_candidates(
            category=category,
            request=request,
            venues=candidate_source,
        )
        for category in requested_categories
    ]

    if any(
        not group
        for group in candidate_groups
    ):
        return []

    plans: list[Itinerary] = []

    for selected_venues in product(
        *candidate_groups
    ):
        chosen_venues = list(
            selected_venues
        )

        plan = build_itinerary(
            request=request,
            chosen_venues=chosen_venues,
            start_coordinates=start_coordinates,
            prefer_live=prefer_live,
        )

        plans.append(
            plan
        )

    return plans


def plan_signature(
    plan: Itinerary,
) -> tuple[str, ...]:
    return tuple(
        stop.name
        for stop in plan.stops
    )


def select_distinct_plans(
    plans: list[Itinerary],
    request: PlanRequest,
    venue_source: list[Venue],
) -> list[Itinerary]:
    """
    Select up to three meaningfully different plans.

    V2.3 considers plans with no validation errors valid.

    Warning-level issues such as unknown opening hours or route
    fallback do not automatically invalidate an itinerary.
    """
    if not plans:
        return []

    valid_plans = [
        plan
        for plan in plans
        if not plan_has_errors(
            plan
        )
    ]

    # If every plan violates a hard constraint, keep the invalid
    # candidates available. This becomes important in V2.4 because
    # the repair agent needs failed plans to understand what must
    # be repaired.
    candidates = (
        valid_plans
        if valid_plans
        else plans
    )

    selected: list[Itinerary] = []

    used_signatures: set[
        tuple[str, ...]
    ] = set()

    def add_plan(
        plan: Itinerary,
        label: str,
        reason: str,
    ) -> None:
        signature = plan_signature(
            plan
        )

        if signature in used_signatures:
            return

        plan.label = label

        if reason not in plan.reasons:
            plan.reasons.insert(
                0,
                reason,
            )

        selected.append(
            plan
        )

        used_signatures.add(
            signature
        )

    best_overall = max(
        candidates,
        key=lambda plan: plan.score,
    )

    add_plan(
        best_overall,
        "Best overall",
        (
            "Highest combined score for budget, "
            "travel time, schedule, and requested vibe."
        ),
    )

    cheapest_candidates = [
        plan
        for plan in candidates
        if (
            plan_signature(plan)
            not in used_signatures
        )
    ]

    if cheapest_candidates:
        lowest_cost = min(
            cheapest_candidates,
            key=lambda plan: (
                plan.total_cost,
                -plan.score,
            ),
        )

        add_plan(
            lowest_cost,
            "Lowest cost",
            (
                "Lowest estimated total among "
                "the available valid plans."
            ),
        )

    vibe_candidates = [
        plan
        for plan in candidates
        if (
            plan_signature(plan)
            not in used_signatures
        )
    ]

    if vibe_candidates:
        requested_vibes = {
            vibe.lower()
            for vibe in request.vibe
        }

        venue_lookup = {
            venue.name: venue
            for venue in venue_source
        }

        def vibe_score(
            plan: Itinerary,
        ) -> tuple[int, float]:
            overlap = 0

            for stop in plan.stops:
                matching_venue = venue_lookup.get(
                    stop.name
                )

                if matching_venue is None:
                    continue

                overlap += len(
                    {
                        vibe.lower()
                        for vibe
                        in matching_venue.vibe
                    }
                    & requested_vibes
                )

            return (
                overlap,
                plan.score,
            )

        best_vibe = max(
            vibe_candidates,
            key=vibe_score,
        )

        add_plan(
            best_vibe,
            "Best vibe match",
            (
                "Strongest match for "
                "the requested atmosphere."
            ),
        )

    remaining = sorted(
        [
            plan
            for plan in candidates
            if (
                plan_signature(plan)
                not in used_signatures
            )
        ],
        key=lambda plan: plan.score,
        reverse=True,
    )

    fallback_labels = [
        "Alternative",
        "Backup option",
        "Additional option",
    ]

    for plan in remaining:
        if len(selected) >= 3:
            break

        label_index = min(
            len(selected),
            len(fallback_labels) - 1,
        )

        add_plan(
            plan,
            fallback_labels[
                label_index
            ],
            (
                "A strong alternative based "
                "on the current constraints."
            ),
        )

    return selected[:3]


def _venue_lookup(
    venue_source: list[Venue],
) -> dict[str, Venue]:
    """
    Build a name-to-venue lookup for rebuilding shortlisted plans.
    """
    return {
        venue.name: venue
        for venue in venue_source
    }


def _venues_for_plan(
    plan: Itinerary,
    venue_source: list[Venue],
) -> list[Venue]:
    """
    Recover the Venue objects represented by an itinerary.
    """
    lookup = _venue_lookup(
        venue_source
    )

    result: list[Venue] = []

    for stop in plan.stops:
        venue = lookup.get(
            stop.name
        )

        if venue is None:
            return []

        result.append(
            venue
        )

    return result


def build_live_shortlist(
    *,
    preliminary_plans: list[Itinerary],
    request: PlanRequest,
    venue_source: list[Venue],
) -> list[Itinerary]:
    """
    Build a small, diverse shortlist for expensive live routing.

    We first preserve the three recommendation styles:
      - best overall
      - lowest cost
      - best vibe

    Then fill remaining shortlist slots with the highest-scoring
    preliminary candidates.
    """
    if not preliminary_plans:
        return []

    shortlist: list[Itinerary] = []

    used_signatures: set[
        tuple[str, ...]
    ] = set()

    initial_selected = select_distinct_plans(
        plans=preliminary_plans,
        request=request,
        venue_source=venue_source,
    )

    for plan in initial_selected:
        signature = plan_signature(
            plan
        )

        if signature in used_signatures:
            continue

        shortlist.append(
            plan
        )

        used_signatures.add(
            signature
        )

    remaining = sorted(
        preliminary_plans,
        key=lambda plan: plan.score,
        reverse=True,
    )

    for plan in remaining:
        if (
            len(shortlist)
            >= LIVE_SHORTLIST_SIZE
        ):
            break

        signature = plan_signature(
            plan
        )

        if signature in used_signatures:
            continue

        shortlist.append(
            plan
        )

        used_signatures.add(
            signature
        )

    return shortlist


def rebuild_shortlist_with_live_routes(
    *,
    shortlist: list[Itinerary],
    request: PlanRequest,
    venue_source: list[Venue],
    start_coordinates: Coordinates | None,
) -> list[Itinerary]:
    """
    Upgrade only shortlisted itineraries to live route data.

    Every rebuilt itinerary is validated again using its final
    live route durations and route providers.
    """
    live_plans: list[Itinerary] = []

    for preliminary_plan in shortlist:
        chosen_venues = _venues_for_plan(
            preliminary_plan,
            venue_source,
        )

        if not chosen_venues:
            continue

        live_plan = build_itinerary(
            request=request,
            chosen_venues=chosen_venues,
            start_coordinates=start_coordinates,
            prefer_live=True,
        )

        live_plans.append(
            live_plan
        )

    return live_plans


def build_plans(
    request: PlanRequest,
    venues: list[Venue] | None = None,
    start_coordinates: Coordinates | None = None,
) -> list[Itinerary]:
    """
    Production-style two-stage itinerary planning.

    Stage 1
    -------
    Evaluate every candidate using local deterministic routing.
    This performs zero external routing API calls.

    Stage 2
    -------
    Select a small shortlist.

    Stage 3
    -------
    Upgrade only shortlisted plans with live routing.

    Stage 4
    -------
    Revalidate and re-score using final route data.

    Stage 5
    -------
    Return three distinct recommendations.
    """
    venue_source = (
        venues
        if venues is not None
        else VENUES
    )

    # ----------------------------------------------------------
    # PHASE 1 — FAST PRELIMINARY PLANNING
    # ----------------------------------------------------------

    preliminary_plans = build_candidate_plans(
        request=request,
        venues=venue_source,
        start_coordinates=start_coordinates,
        prefer_live=False,
    )

    if not preliminary_plans:
        return []

    # ----------------------------------------------------------
    # PHASE 2 — SHORTLIST
    # ----------------------------------------------------------

    shortlist = build_live_shortlist(
        preliminary_plans=preliminary_plans,
        request=request,
        venue_source=venue_source,
    )

    # ----------------------------------------------------------
    # PHASE 3 — LIVE ROUTING
    # ----------------------------------------------------------

    live_plans = rebuild_shortlist_with_live_routes(
        shortlist=shortlist,
        request=request,
        venue_source=venue_source,
        start_coordinates=start_coordinates,
    )

    # Graceful fallback if live rebuilding unexpectedly fails.
    if not live_plans:
        return select_distinct_plans(
            plans=preliminary_plans,
            request=request,
            venue_source=venue_source,
        )

    # ----------------------------------------------------------
    # PHASE 4 — FINAL SELECTION
    # ----------------------------------------------------------

    return select_distinct_plans(
        plans=live_plans,
        request=request,
        venue_source=venue_source,
    )
