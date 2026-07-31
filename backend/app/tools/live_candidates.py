from __future__ import annotations

import re

from backend.app.data import VENUES
from backend.app.models import PlaceResult, PlanRequest, Venue
from backend.app.tools.places import (
    PlaceSearchError,
    search_places,
)


CATEGORY_SEARCH_CONFIG = {
    "activity": {
        "default_query": "museum",
        "default_category": "entertainment",
        "limit": 6,
    },
    "restaurant": {
        "default_query": "restaurant",
        "default_category": "catering.restaurant",
        "limit": 8,
    },
    "dessert": {
        "default_query": "dessert",
        "default_category": "catering",
        "limit": 6,
    },
}


def _clean_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _infer_area(place: PlaceResult) -> str:
    """
    Infer a short area label from the formatted address.

    This is temporary. A future version will store neighborhood
    information directly from the provider response.
    """
    address = place.formatted_address

    known_areas = [
        "North End",
        "Back Bay",
        "Seaport",
        "Allston",
        "Cambridge",
        "Somerville",
        "Brookline",
        "West End",
        "Downtown",
        "South Boston",
        "Fenway",
        "Beacon Hill",
    ]

    lowered = address.lower()

    for area in known_areas:
        if area.lower() in lowered:
            return area

    if "boston" in lowered:
        return "Boston"

    return "Unknown area"


def _infer_activity_cost(place: PlaceResult) -> float:
    text = _clean_text(
        " ".join(
            [
                place.name,
                *place.categories,
            ]
        )
    )

    if any(
        keyword in text
        for keyword in [
            "park",
            "garden",
            "monument",
            "viewpoint",
            "beach",
        ]
    ):
        return 0.0

    if "museum" in text:
        return 25.0

    if "cinema" in text:
        return 22.0

    if "karaoke" in text:
        return 35.0

    return 28.0


def _infer_restaurant_cost(place: PlaceResult) -> float:
    text = _clean_text(
        " ".join(
            [
                place.name,
                *place.categories,
            ]
        )
    )

    if any(
        keyword in text
        for keyword in [
            "fast food",
            "food court",
            "falafel",
            "shawarma",
            "sandwich",
        ]
    ):
        return 20.0

    if any(
        keyword in text
        for keyword in [
            "fine dining",
            "steakhouse",
            "seafood room",
            "ristorante",
        ]
    ):
        return 48.0

    return 36.0


def _infer_dessert_cost(place: PlaceResult) -> float:
    text = _clean_text(
        " ".join(
            [
                place.name,
                *place.categories,
            ]
        )
    )

    if any(
        keyword in text
        for keyword in [
            "gelato",
            "ice cream",
        ]
    ):
        return 9.0

    if any(
        keyword in text
        for keyword in [
            "chocolate",
            "cake",
            "bakery",
            "pastry",
        ]
    ):
        return 13.0

    return 11.0


def _infer_cost(
    place: PlaceResult,
    category: str,
) -> float:
    if category == "activity":
        return _infer_activity_cost(place)

    if category == "restaurant":
        return _infer_restaurant_cost(place)

    if category == "dessert":
        return _infer_dessert_cost(place)

    return 25.0


def _infer_duration(category: str) -> int:
    durations = {
        "activity": 90,
        "restaurant": 90,
        "dessert": 40,
    }

    return durations.get(category, 60)


def _infer_vibes(
    place: PlaceResult,
    category: str,
) -> list[str]:
    text = _clean_text(
        " ".join(
            [
                place.name,
                place.formatted_address,
                *place.categories,
            ]
        )
    )

    vibes: list[str] = []

    vibe_keywords = {
        "romantic": [
            "italian",
            "ristorante",
            "garden",
            "waterfront",
            "view",
        ],
        "fun": [
            "karaoke",
            "cinema",
            "game",
            "bowling",
            "entertainment",
        ],
        "scenic": [
            "park",
            "garden",
            "waterfront",
            "harbor",
            "view",
        ],
        "cozy": [
            "cafe",
            "bakery",
            "coffee",
            "gelato",
        ],
        "stylish": [
            "bistro",
            "lounge",
            "modern",
            "rooftop",
        ],
        "indoor": [
            "museum",
            "cinema",
            "restaurant",
            "cafe",
        ],
        "active": [
            "park",
            "sports",
            "bowling",
            "game",
        ],
    }

    for vibe, keywords in vibe_keywords.items():
        if any(keyword in text for keyword in keywords):
            vibes.append(vibe)

    if not vibes:
        default_vibes = {
            "activity": ["fun"],
            "restaurant": ["cozy"],
            "dessert": ["casual"],
        }

        vibes = default_vibes.get(
            category,
            ["casual"],
        )

    return list(dict.fromkeys(vibes))


def _infer_food_tags(
    place: PlaceResult,
) -> list[str]:
    text = _clean_text(
        " ".join(
            [
                place.name,
                *place.categories,
            ]
        )
    )

    tags: list[str] = []

    if any(
        keyword in text
        for keyword in [
            "italian",
            "bistro",
            "restaurant",
            "grill",
        ]
    ):
        tags.append("chicken options")

    if any(
        keyword in text
        for keyword in [
            "italian",
            "risotto",
            "ristorante",
        ]
    ):
        tags.append("risotto")

    if "vegan" in text:
        tags.append("vegan")

    if "vegetarian" in text:
        tags.append("vegetarian")

    if "sushi" in text:
        tags.append("seafood")

    return list(dict.fromkeys(tags))


def place_to_venue(
    place: PlaceResult,
    category: str,
) -> Venue:
    """
    Convert a live provider result into the Venue model used by
    the existing planner.
    """
    return Venue(
        name=place.name,
        category=category,
        area=_infer_area(place),
        estimated_cost_per_person=_infer_cost(
            place,
            category,
        ),
        duration_minutes=_infer_duration(category),
        vibe=_infer_vibes(
            place,
            category,
        ),
        food_tags=(
            _infer_food_tags(place)
            if category == "restaurant"
            else []
        ),
    )


def _restaurant_query(
    request: PlanRequest,
) -> str:
    preferences = {
        preference.lower()
        for preference in request.food_preferences
    }

    if "risotto" in preferences:
        return "Italian restaurant"

    if "vegan" in preferences:
        return "vegan restaurant"

    if "vegetarian" in preferences:
        return "vegetarian restaurant"

    if "seafood" in preferences:
        return "sushi"

    return "restaurant"


def _activity_query(
    request: PlanRequest,
) -> str:
    vibes = {
        vibe.lower()
        for vibe in request.vibe
    }

    if "scenic" in vibes:
        return "park"

    if "indoor" in vibes:
        return "museum"

    if "fun" in vibes:
        return "museum"

    return "museum"


def _query_for_category(
    request: PlanRequest,
    category: str,
) -> str:
    if category == "restaurant":
        return _restaurant_query(request)

    if category == "activity":
        return _activity_query(request)

    if category == "dessert":
        return "dessert"

    return CATEGORY_SEARCH_CONFIG[category]["default_query"]


def build_live_venues(
    request: PlanRequest,
) -> list[Venue]:
    """
    Retrieve live place candidates and convert them to Venue objects.

    Raises PlaceSearchError if the provider request fails.
    """
    requested_categories: list[str] = []

    if "activity" in request.must_include:
        requested_categories.append("activity")

    if "dinner" in request.must_include:
        requested_categories.append("restaurant")

    if "dessert" in request.must_include:
        requested_categories.append("dessert")

    if not requested_categories:
        requested_categories = [
            "activity",
            "restaurant",
        ]

    live_venues: list[Venue] = []

    for category in requested_categories:
        config = CATEGORY_SEARCH_CONFIG[category]
        query = _query_for_category(
            request,
            category,
        )

        places = search_places(
            query=query,
            city=request.city,
            category=config["default_category"],
            limit=config["limit"],
        )

        live_venues.extend(
            place_to_venue(
                place,
                category,
            )
            for place in places
        )

    return live_venues


def build_live_venues_with_fallback(
    request: PlanRequest,
) -> tuple[list[Venue], bool]:
    """
    Return live venues when possible.

    If Geoapify fails or returns no candidates, return the existing
    sample venues so PlanPilot remains usable.

    The Boolean result is True when live data was used.
    """
    try:
        live_venues = build_live_venues(request)

        if live_venues:
            return live_venues, True

    except PlaceSearchError:
        pass

    return list(VENUES), False
