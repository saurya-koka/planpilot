from __future__ import annotations

import re
from datetime import datetime, timedelta
from itertools import product

from .data import AREA_TRAVEL_MINUTES, VENUES
from .models import Itinerary, PlanRequest, Stop, Venue
from .tools.opening_hours import (
    DAY_ORDER,
    normalize_day,
    parse_clock_time,
    venue_open_for_interval,
)
from .tools.routing import estimate_travel_minutes


Coordinates = tuple[float, float]


def fallback_travel_minutes(
    area_a: str,
    area_b: str,
) -> int:
    """
    Return a temporary area-based estimate when coordinates are
    unavailable.
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


def calculate_leg_minutes(
    *,
    area_a: str,
    area_b: str,
    coordinates_a: Coordinates | None,
    coordinates_b: Coordinates | None,
    request: PlanRequest,
) -> int:
    """
    Use coordinates when possible and fall back to the temporary
    neighborhood matrix when they are unavailable.
    """
    if (
        coordinates_a is not None
        and coordinates_b is not None
    ):
        return estimate_travel_minutes(
            latitude_a=coordinates_a[0],
            longitude_a=coordinates_a[1],
            latitude_b=coordinates_b[0],
            longitude_b=coordinates_b[1],
            transport=request.transport,
        )

    return fallback_travel_minutes(
        area_a,
        area_b,
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
        categories.append("activity")

    if "dinner" in request.must_include:
        categories.append("restaurant")

    if "dessert" in request.must_include:
        categories.append("dessert")

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
) -> list[int]:
    """
    Calculate travel time from the starting point through every
    venue in itinerary order.
    """
    legs: list[int] = []

    previous_area = request.start_area
    previous_coordinates = start_coordinates

    for venue in venues:
        current_coordinates = venue_coordinates(
            venue
        )

        leg_minutes = calculate_leg_minutes(
            area_a=previous_area,
            area_b=venue.area,
            coordinates_a=previous_coordinates,
            coordinates_b=current_coordinates,
            request=request,
        )

        legs.append(
            leg_minutes
        )

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

    Defaults to Friday when no weekday is present.
    """
    cleaned = date_text.strip().lower()

    for weekday in DAY_ORDER:
        if re.search(
            rf"\b{re.escape(weekday)}\b",
            cleaned,
        ):
            return weekday

    normalized = normalize_day(
        cleaned
    )

    return normalized or "friday"


def build_start_datetime(
    request: PlanRequest,
) -> datetime:
    """
    Build a synthetic datetime used for itinerary arithmetic.

    The date itself is not intended to represent the real calendar
    date. It preserves the requested weekday and start time.
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

    # 2024-01-01 was a Monday. This creates a stable weekday anchor
    # for deterministic scheduling and tests.
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

    return monday_anchor + timedelta(
        days=weekday_index
    )


def calculate_stop_schedule(
    *,
    request: PlanRequest,
    venues: list[Venue],
    legs: list[int],
) -> tuple[
    list[datetime],
    list[str],
    list[str],
]:
    """
    Calculate arrival times and inspect whether each venue remains
    open for the full planned visit.

    Returns:
        arrival times
        confirmed-closed venue names
        live venues whose hours could not be verified
    """
    current_datetime = build_start_datetime(
        request
    )

    arrival_times: list[datetime] = []
    closed_venues: list[str] = []
    unknown_hours: list[str] = []

    for venue, leg_minutes in zip(
        venues,
        legs,
        strict=True,
    ):
        current_datetime += timedelta(
            minutes=leg_minutes
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
    Return a user-friendly 12-hour time.
    """
    return value.strftime(
        "%I:%M %p"
    ).lstrip("0")


def build_candidate_plans(
    request: PlanRequest,
    venues: list[Venue] | None = None,
    start_coordinates: Coordinates | None = None,
) -> list[Itinerary]:
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

        legs = calculate_route_legs(
            request=request,
            venues=chosen_venues,
            start_coordinates=start_coordinates,
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

        # A confirmed-closed venue invalidates the itinerary.
        if closed_venues:
            continue

        total_travel = sum(
            legs
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

        warnings: list[str] = []

        if total_cost > request.budget_total:
            overage = (
                total_cost
                - request.budget_total
            )

            warnings.append(
                "Estimated cost exceeds "
                f"budget by ${overage:.0f}."
            )

        if (
            legs
            and max(legs)
            > request.max_leg_minutes
        ):
            warnings.append(
                "One travel leg is approximately "
                f"{max(legs)} minutes."
            )

        if unknown_hours:
            displayed_names = ", ".join(
                unknown_hours[:3]
            )

            if len(unknown_hours) > 3:
                displayed_names += (
                    f" and {len(unknown_hours) - 3} more"
                )

            warnings.append(
                "Opening hours could not be verified for: "
                f"{displayed_names}."
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
                leg - request.max_leg_minutes,
            )
            for leg in legs
        )

        unknown_hours_penalty = (
            len(unknown_hours) * 3
        )

        score = (
            100
            + vibe_overlap * 8
            - total_travel * 0.7
            - budget_penalty * 1.5
            - long_leg_penalty
            - unknown_hours_penalty
        )

        if not warnings:
            score += 20

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
                duration_minutes=(
                    venue.duration_minutes
                ),
                latitude=venue.latitude,
                longitude=venue.longitude,
                formatted_address=(
                    venue.formatted_address
                ),
                website=venue.website,
                opening_hours=(
                    venue.opening_hours
                ),
                source=venue.source,
            )
            for venue in chosen_venues
        ]

        title = " → ".join(
            venue.name
            for venue in chosen_venues
        )

        plans.append(
            Itinerary(
                label="Candidate",
                title=title,
                stops=stops,
                total_cost=round(
                    total_cost,
                    2,
                ),
                total_duration_minutes=(
                    total_duration
                ),
                estimated_travel_minutes=(
                    total_travel
                ),
                score=round(
                    score,
                    2,
                ),
                reasons=reasons,
                warnings=warnings,
            )
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
    if not plans:
        return []

    valid_plans = [
        plan
        for plan in plans
        if not plan.warnings
    ]

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
        if plan_signature(plan)
        not in used_signatures
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
        if plan_signature(plan)
        not in used_signatures
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
                "Strongest match for the "
                "requested atmosphere."
            ),
        )

    remaining = sorted(
        [
            plan
            for plan in candidates
            if plan_signature(plan)
            not in used_signatures
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
            fallback_labels[label_index],
            (
                "A strong alternative based "
                "on the current constraints."
            ),
        )

    return selected[:3]


def build_plans(
    request: PlanRequest,
    venues: list[Venue] | None = None,
    start_coordinates: Coordinates | None = None,
) -> list[Itinerary]:
    venue_source = (
        venues
        if venues is not None
        else VENUES
    )

    candidate_plans = build_candidate_plans(
        request=request,
        venues=venue_source,
        start_coordinates=start_coordinates,
    )

    return select_distinct_plans(
        plans=candidate_plans,
        request=request,
        venue_source=venue_source,
    )
