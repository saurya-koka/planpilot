from __future__ import annotations

from itertools import product

from .data import AREA_TRAVEL_MINUTES, VENUES
from .models import Itinerary, PlanRequest, Stop, Venue


def travel_minutes(area_a: str, area_b: str) -> int:
    if area_a == area_b:
        return 8
    return AREA_TRAVEL_MINUTES.get((area_a, area_b), AREA_TRAVEL_MINUTES.get((area_b, area_a), 35))


def venue_matches_food(venue: Venue, preferences: list[str]) -> bool:
    if venue.category != "restaurant" or not preferences:
        return True
    wanted = {item.lower() for item in preferences}
    available = {item.lower() for item in venue.food_tags}
    return bool(wanted & available)


def build_plans(request: PlanRequest) -> list[Itinerary]:
    activities = [v for v in VENUES if v.category == "activity"]
    restaurants = [v for v in VENUES if v.category == "restaurant" and venue_matches_food(v, request.food_preferences)]
    desserts = [v for v in VENUES if v.category == "dessert"]

    plans: list[Itinerary] = []
    for activity, restaurant, dessert in product(activities, restaurants, desserts):
        legs = [travel_minutes(activity.area, restaurant.area), travel_minutes(restaurant.area, dessert.area)]
        total_travel = sum(legs)
        total_cost = request.party_size * sum(
            venue.estimated_cost_per_person for venue in (activity, restaurant, dessert)
        )
        total_duration = sum(v.duration_minutes for v in (activity, restaurant, dessert)) + total_travel

        warnings: list[str] = []
        if total_cost > request.budget_total:
            warnings.append(f"Estimated cost exceeds budget by ${total_cost - request.budget_total:.0f}.")
        if max(legs) > request.max_leg_minutes:
            warnings.append(f"One travel leg is approximately {max(legs)} minutes.")

        vibe_overlap = sum(len(set(v.vibe) & set(request.vibe)) for v in (activity, restaurant, dessert))
        score = 100 + vibe_overlap * 8 - total_travel * 0.7 - max(0, total_cost - request.budget_total) * 1.5
        if not warnings:
            score += 20

        reasons = [
            f"Matches {vibe_overlap} requested vibe tags.",
            f"Estimated at ${total_cost:.0f} for {request.party_size} people.",
            f"Approximately {total_travel} minutes of travel between stops.",
        ]

        plans.append(
            Itinerary(
                title=f"{activity.name} → {restaurant.name} → {dessert.name}",
                stops=[
                    Stop(name=v.name, category=v.category, area=v.area, estimated_cost=v.estimated_cost_per_person * request.party_size, duration_minutes=v.duration_minutes)
                    for v in (activity, restaurant, dessert)
                ],
                total_cost=round(total_cost, 2),
                total_duration_minutes=total_duration,
                estimated_travel_minutes=total_travel,
                score=round(score, 2),
                reasons=reasons,
                warnings=warnings,
            )
        )

    valid = [plan for plan in plans if not plan.warnings]
    ranked = valid if valid else plans
    return sorted(ranked, key=lambda plan: plan.score, reverse=True)[:3]
