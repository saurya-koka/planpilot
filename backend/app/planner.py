from __future__ import annotations

from itertools import product

from .data import AREA_TRAVEL_MINUTES, VENUES
from .models import Itinerary, PlanRequest, Stop, Venue


def travel_minutes(area_a: str, area_b: str) -> int:
    """
    Return a temporary travel-time estimate between two areas.

    Live routing will replace this lookup table in a later phase.
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


def venue_matches_food(
    venue: Venue,
    preferences: list[str],
) -> bool:
    """
    Check whether a restaurant matches at least one requested
    food preference.

    Non-restaurant venues always pass this check.
    """
    if venue.category != "restaurant" or not preferences:
        return True

    wanted = {
        preference.lower()
        for preference in preferences
    }

    available = {
        tag.lower()
        for tag in venue.food_tags
    }

    return bool(wanted & available)


def get_requested_categories(
    request: PlanRequest,
) -> list[str]:
    """
    Convert user-facing categories into Venue category names.
    """
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
    """
    Filter the supplied venue collection by requested category
    and food preferences.
    """
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
    """
    Count how many requested vibe tags appear across the venues.
    """
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


def build_candidate_plans(
    request: PlanRequest,
    venues: list[Venue] | None = None,
) -> list[Itinerary]:
    """
    Build every valid itinerary combination from either:

    - custom live venues supplied by the caller, or
    - the original mock VENUES dataset.
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
        chosen_venues = list(selected_venues)

        route_areas = [
            request.start_area,
            *[
                venue.area
                for venue in chosen_venues
            ],
        ]

        legs = [
            travel_minutes(
                route_areas[index],
                route_areas[index + 1],
            )
            for index in range(
                len(route_areas) - 1
            )
        ]

        total_travel = sum(legs)

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

        vibe_overlap = calculate_vibe_overlap(
            venues=chosen_venues,
            requested_vibes=request.vibe,
        )

        budget_penalty = max(
            0,
            total_cost - request.budget_total,
        )

        score = (
            100
            + vibe_overlap * 8
            - total_travel * 0.7
            - budget_penalty * 1.5
        )

        if not warnings:
            score += 20

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
                "minutes of travel including "
                "the first stop."
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
    """
    Return a stable identifier for an itinerary's venue sequence.
    """
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
    Select three intentionally different options:

    1. Best overall
    2. Lowest cost
    3. Best vibe match
    """
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
        signature = plan_signature(plan)

        if signature in used_signatures:
            return

        plan.label = label

        if reason not in plan.reasons:
            plan.reasons.insert(
                0,
                reason,
            )

        selected.append(plan)
        used_signatures.add(signature)

    best_overall = max(
        candidates,
        key=lambda plan: plan.score,
    )

    add_plan(
        best_overall,
        "Best overall",
        (
            "Highest combined score for budget, "
            "travel time, and requested vibe."
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
) -> list[Itinerary]:
    """
    Build and rank itineraries using mock or live venue candidates.
    """
    venue_source = (
        venues
        if venues is not None
        else VENUES
    )

    candidate_plans = build_candidate_plans(
        request=request,
        venues=venue_source,
    )

    return select_distinct_plans(
        plans=candidate_plans,
        request=request,
        venue_source=venue_source,
    )
