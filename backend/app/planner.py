from __future__ import annotations

from itertools import product

from .data import AREA_TRAVEL_MINUTES, VENUES
from .models import Itinerary, PlanRequest, Stop, Venue


def travel_minutes(area_a: str, area_b: str) -> int:
    if area_a == area_b:
        return 8

    return AREA_TRAVEL_MINUTES.get(
        (area_a, area_b),
        AREA_TRAVEL_MINUTES.get((area_b, area_a), 35),
    )


def venue_matches_food(
    venue: Venue,
    preferences: list[str],
) -> bool:
    if venue.category != "restaurant" or not preferences:
        return True

    wanted = {item.lower() for item in preferences}
    available = {item.lower() for item in venue.food_tags}

    return bool(wanted & available)


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
        categories = ["activity", "restaurant"]

    return categories


def get_candidates(
    category: str,
    request: PlanRequest,
) -> list[Venue]:
    candidates = [
        venue
        for venue in VENUES
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


def build_plans(
    request: PlanRequest,
) -> list[Itinerary]:
    requested_categories = get_requested_categories(request)

    candidate_groups = [
        get_candidates(category, request)
        for category in requested_categories
    ]

    if any(not group for group in candidate_groups):
        return []

    plans: list[Itinerary] = []

    for selected_venues in product(*candidate_groups):
        venues = list(selected_venues)

        route_areas = [
            request.start_area,
            *[venue.area for venue in venues],
        ]

        legs = [
            travel_minutes(
                route_areas[index],
                route_areas[index + 1],
            )
            for index in range(len(route_areas) - 1)
        ]

        total_travel = sum(legs)

        total_cost = request.party_size * sum(
            venue.estimated_cost_per_person
            for venue in venues
        )

        total_duration = (
            sum(venue.duration_minutes for venue in venues)
            + total_travel
        )

        warnings: list[str] = []

        if total_cost > request.budget_total:
            overage = total_cost - request.budget_total
            warnings.append(
                f"Estimated cost exceeds budget by ${overage:.0f}."
            )

        if legs and max(legs) > request.max_leg_minutes:
            warnings.append(
                f"One travel leg is approximately {max(legs)} minutes."
            )

        requested_vibes = {
            vibe.lower()
            for vibe in request.vibe
        }

        vibe_overlap = sum(
            len(
                {
                    vibe.lower()
                    for vibe in venue.vibe
                }
                & requested_vibes
            )
            for venue in venues
        )

        score = (
            100
            + vibe_overlap * 8
            - total_travel * 0.7
            - max(
                0,
                total_cost - request.budget_total,
            )
            * 1.5
        )

        if not warnings:
            score += 20

        reasons = [
            (
                f"Matches {vibe_overlap} requested "
                "vibe tags."
            ),
            (
                f"Estimated at ${total_cost:.0f} "
                f"for {request.party_size} people."
            ),
            (
                f"Approximately {total_travel} minutes "
                "of travel including the first stop."
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
            )
            for venue in venues
        ]

        title = " → ".join(
            venue.name
            for venue in venues
        )

        plans.append(
            Itinerary(
                title=title,
                stops=stops,
                total_cost=round(total_cost, 2),
                total_duration_minutes=total_duration,
                estimated_travel_minutes=total_travel,
                score=round(score, 2),
                reasons=reasons,
                warnings=warnings,
            )
        )

    valid_plans = [
        plan
        for plan in plans
        if not plan.warnings
    ]

    ranked_plans = valid_plans if valid_plans else plans

    return sorted(
        ranked_plans,
        key=lambda plan: plan.score,
        reverse=True,
    )[:3]
