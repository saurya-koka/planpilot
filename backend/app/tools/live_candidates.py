from __future__ import annotations

import re
from typing import Any

from backend.app.data import VENUES
from backend.app.models import PlaceResult, PlanRequest, Venue
from backend.app.tools.places import (
    PlaceSearchError,
    search_places,
)


CATEGORY_SEARCH_CONFIG = {
    "activity": {
        "default_category": "entertainment",
        "limit_per_query": 8,
        "final_limit": 12,
    },
    "restaurant": {
        "default_category": "catering.restaurant",
        "limit_per_query": 10,
        "final_limit": 12,
    },
    "dessert": {
        "default_category": "catering",
        "limit_per_query": 10,
        "final_limit": 10,
    },
}


OUTING_PROFILES: dict[str, dict[str, Any]] = {
    "romantic": {
        "activity_queries": [
            "garden",
            "park",
            "scenic walk",
            "art gallery",
            "museum",
        ],
        "positive_keywords": [
            "garden",
            "waterfront",
            "harbor",
            "view",
            "esplanade",
            "gallery",
            "art",
            "historic",
        ],
        "negative_keywords": [
            "medical",
            "military",
            "artillery",
            "children",
            "science",
        ],
        "restaurant_keywords": [
            "ristorante",
            "trattoria",
            "osteria",
            "cucina",
            "bistro",
            "rooftop",
            "waterfront",
        ],
        "dessert_keywords": [
            "gelato",
            "chocolate",
            "dessert",
            "pastry",
            "bakery",
            "ice cream",
        ],
    },
    "fun": {
        "activity_queries": [
            "karaoke",
            "cinema",
            "bowling",
            "arcade",
            "entertainment",
        ],
        "positive_keywords": [
            "karaoke",
            "bowling",
            "arcade",
            "game",
            "cinema",
            "comedy",
            "entertainment",
            "theater",
            "theatre",
        ],
        "negative_keywords": [],
        "restaurant_keywords": [
            "barbecue",
            "pizza",
            "grill",
            "tapas",
            "food hall",
        ],
        "dessert_keywords": [
            "ice cream",
            "donut",
            "cookie",
            "dessert",
            "candy",
        ],
    },
    "chill": {
        "activity_queries": [
            "park",
            "garden",
            "museum",
            "gallery",
            "library",
        ],
        "positive_keywords": [
            "park",
            "garden",
            "waterfront",
            "book",
            "library",
            "gallery",
        ],
        "negative_keywords": [
            "nightclub",
            "stadium",
        ],
        "restaurant_keywords": [
            "cafe",
            "bistro",
            "casual",
            "brunch",
        ],
        "dessert_keywords": [
            "bakery",
            "pastry",
            "gelato",
            "ice cream",
        ],
    },
    "active": {
        "activity_queries": [
            "park",
            "sports",
            "recreation",
            "bowling",
            "climbing",
        ],
        "positive_keywords": [
            "park",
            "sports",
            "climbing",
            "bowling",
            "skating",
            "recreation",
            "trail",
            "kayak",
        ],
        "negative_keywords": [
            "museum",
            "gallery",
            "cinema",
        ],
        "restaurant_keywords": [
            "grill",
            "healthy",
            "protein",
            "salad",
        ],
        "dessert_keywords": [
            "smoothie",
            "juice",
            "frozen yogurt",
        ],
    },
    "cultural": {
        "activity_queries": [
            "museum",
            "gallery",
            "historic site",
            "theater",
            "cinema",
        ],
        "positive_keywords": [
            "museum",
            "gallery",
            "historic",
            "history",
            "art",
            "culture",
            "theatre",
            "theater",
        ],
        "negative_keywords": [],
        "restaurant_keywords": [
            "local",
            "historic",
            "traditional",
            "bistro",
        ],
        "dessert_keywords": [
            "bakery",
            "pastry",
            "chocolate",
        ],
    },
    "nightlife": {
        "activity_queries": [
            "karaoke",
            "nightclub",
            "live music",
            "comedy",
            "entertainment",
        ],
        "positive_keywords": [
            "karaoke",
            "nightclub",
            "lounge",
            "bar",
            "music",
            "comedy",
            "late night",
        ],
        "negative_keywords": [
            "children",
            "library",
        ],
        "restaurant_keywords": [
            "lounge",
            "tapas",
            "bar",
            "rooftop",
            "late night",
        ],
        "dessert_keywords": [
            "late night",
            "dessert",
            "ice cream",
            "chocolate",
        ],
    },
    "family": {
        "activity_queries": [
            "science museum",
            "aquarium",
            "zoo",
            "park",
            "cinema",
            "entertainment",
        ],
        "positive_keywords": [
            "children",
            "science",
            "aquarium",
            "zoo",
            "park",
            "family",
            "interactive",
        ],
        "negative_keywords": [
            "nightclub",
            "bar",
            "lounge",
            "adult",
        ],
        "restaurant_keywords": [
            "pizza",
            "family",
            "grill",
            "casual",
        ],
        "dessert_keywords": [
            "ice cream",
            "cookie",
            "donut",
            "bakery",
        ],
    },
    "foodie": {
        "activity_queries": [
            "market",
            "food market",
            "historic market",
            "museum",
        ],
        "positive_keywords": [
            "market",
            "food",
            "culinary",
            "historic",
            "local",
        ],
        "negative_keywords": [],
        "restaurant_keywords": [
            "ristorante",
            "trattoria",
            "tasting",
            "chef",
            "kitchen",
            "bistro",
            "cuisine",
        ],
        "dessert_keywords": [
            "gelato",
            "chocolate",
            "patisserie",
            "pastry",
            "bakery",
            "dessert",
        ],
    },
    "budget": {
        "activity_queries": [
            "park",
            "garden",
            "monument",
            "museum",
        ],
        "positive_keywords": [
            "park",
            "garden",
            "monument",
            "walk",
            "public",
            "free",
        ],
        "negative_keywords": [
            "luxury",
            "private",
        ],
        "restaurant_keywords": [
            "pizza",
            "sandwich",
            "falafel",
            "food court",
            "casual",
        ],
        "dessert_keywords": [
            "ice cream",
            "donut",
            "bakery",
        ],
    },
    "rainy-day": {
        "activity_queries": [
            "museum",
            "cinema",
            "bowling",
            "karaoke",
            "gallery",
            "entertainment",
        ],
        "positive_keywords": [
            "museum",
            "cinema",
            "indoor",
            "karaoke",
            "bowling",
            "gallery",
            "theater",
            "theatre",
        ],
        "negative_keywords": [
            "park",
            "garden",
            "beach",
            "trail",
            "outdoor",
        ],
        "restaurant_keywords": [
            "cozy",
            "cafe",
            "bistro",
            "restaurant",
        ],
        "dessert_keywords": [
            "bakery",
            "chocolate",
            "pastry",
            "gelato",
            "ice cream",
        ],
    },
    "work-friendly": {
        "activity_queries": [
            "library",
            "coworking",
            "coffee",
        ],
        "positive_keywords": [
            "coffee",
            "cafe",
            "library",
            "workspace",
            "wifi",
            "internet",
            "coworking",
        ],
        "negative_keywords": [
            "nightclub",
            "karaoke",
            "bowling",
        ],
        "restaurant_keywords": [
            "cafe",
            "coffee",
            "bakery",
            "brunch",
        ],
        "dessert_keywords": [
            "bakery",
            "pastry",
        ],
    },
    "group": {
        "activity_queries": [
            "karaoke",
            "bowling",
            "arcade",
            "entertainment",
            "cinema",
        ],
        "positive_keywords": [
            "karaoke",
            "bowling",
            "game",
            "arcade",
            "entertainment",
            "cinema",
            "theater",
            "theatre",
        ],
        "negative_keywords": [],
        "restaurant_keywords": [
            "food hall",
            "pizza",
            "barbecue",
            "tapas",
            "grill",
        ],
        "dessert_keywords": [
            "ice cream",
            "dessert",
            "donut",
            "cookie",
        ],
    },
}


VIBE_ALIASES = {
    "relaxed": "chill",
    "casual": "chill",
    "cozy": "chill",
    "scenic": "romantic",
    "date": "romantic",
    "date-night": "romantic",
    "date night": "romantic",
    "adventure": "active",
    "outdoors": "active",
    "outdoor": "active",
    "culture": "cultural",
    "history": "cultural",
    "art": "cultural",
    "party": "nightlife",
    "night out": "nightlife",
    "kids": "family",
    "family-friendly": "family",
    "food": "foodie",
    "food-focused": "foodie",
    "cheap": "budget",
    "low-cost": "budget",
    "rainy": "rainy-day",
    "indoor": "rainy-day",
    "work": "work-friendly",
    "study": "work-friendly",
    "friends": "group",
}


GENERIC_CHAIN_KEYWORDS = {
    "starbucks",
    "dunkin",
    "caffè nero",
    "caffe nero",
    "mcdonald",
    "burger king",
    "subway",
}


FOOD_VENUE_KEYWORDS = {
    "restaurant",
    "cafe",
    "café",
    "coffee",
    "bakery",
    "bistro",
    "grill",
    "kitchen",
    "diner",
    "barbecue",
    "pizza",
    "pizzeria",
    "tavern",
    "food court",
}


ACTIVITY_KEYWORDS = {
    "museum",
    "gallery",
    "cinema",
    "theater",
    "theatre",
    "karaoke",
    "bowling",
    "arcade",
    "game",
    "park",
    "garden",
    "aquarium",
    "zoo",
    "monument",
    "historic",
    "history",
    "library",
    "sports",
    "recreation",
    "climbing",
    "skating",
    "trail",
    "beach",
    "music",
    "comedy",
    "nightclub",
    "entertainment",
    "market",
}


OUTDOOR_ACTIVITY_KEYWORDS = {
    "park",
    "garden",
    "beach",
    "trail",
    "outdoor",
    "waterfront walk",
    "scenic walk",
    "playground",
}


INDOOR_ACTIVITY_KEYWORDS = {
    "museum",
    "gallery",
    "cinema",
    "theater",
    "theatre",
    "karaoke",
    "bowling",
    "arcade",
    "library",
    "aquarium",
    "indoor",
    "nightclub",
    "comedy",
}


DESSERT_KEYWORDS = {
    "dessert",
    "gelato",
    "ice cream",
    "frozen yogurt",
    "chocolate",
    "cake",
    "cupcake",
    "cookie",
    "donut",
    "doughnut",
    "pastry",
    "patisserie",
    "bakery",
    "candy",
    "sweet",
    "macaron",
}


RESTAURANT_KEYWORDS = {
    "restaurant",
    "ristorante",
    "trattoria",
    "osteria",
    "cucina",
    "bistro",
    "grill",
    "barbecue",
    "pizza",
    "pizzeria",
    "tapas",
    "food hall",
    "kitchen",
    "diner",
    "tavern",
    "sushi",
    "ramen",
}


CAFE_KEYWORDS = {
    "cafe",
    "café",
    "coffee",
    "espresso",
    "roastery",
}


GROUP_RESTAURANT_KEYWORDS = {
    "food hall",
    "pizza",
    "pizzeria",
    "barbecue",
    "bbq",
    "tapas",
    "grill",
    "family",
    "buffet",
}


def _clean_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(
        r"[^a-z0-9\s-]",
        " ",
        value,
    )
    value = re.sub(
        r"\s+",
        " ",
        value,
    )
    return value


def _place_text(
    place: PlaceResult,
) -> str:
    return _clean_text(
        " ".join(
            [
                place.name,
                place.formatted_address,
                *place.categories,
            ]
        )
    )


def _contains_any(
    text: str,
    keywords: set[str] | list[str],
) -> bool:
    return any(
        _clean_text(keyword) in text
        for keyword in keywords
    )


def _request_intents(
    request: PlanRequest,
) -> list[str]:
    """
    Normalize free-form request vibes into supported profiles.
    """
    intents: list[str] = []

    for raw_vibe in request.vibe:
        cleaned = _clean_text(
            raw_vibe
        )

        if cleaned in OUTING_PROFILES:
            intents.append(cleaned)
            continue

        alias = VIBE_ALIASES.get(
            cleaned
        )

        if alias:
            intents.append(alias)

    if request.budget_total <= 80:
        intents.append("budget")

    if request.party_size >= 4:
        intents.append("group")

    if not intents:
        intents.append("fun")

    return list(
        dict.fromkeys(intents)
    )


def _profile_values(
    intents: list[str],
    key: str,
) -> list[str]:
    values: list[str] = []

    for intent in intents:
        profile = OUTING_PROFILES.get(
            intent,
            {},
        )

        values.extend(
            str(value)
            for value in profile.get(
                key,
                [],
            )
        )

    return list(
        dict.fromkeys(values)
    )


def _infer_area(
    place: PlaceResult,
) -> str:
    if place.suburb:
        return place.suburb

    if place.district:
        return place.district

    if place.city:
        return place.city

    address = place.formatted_address.lower()

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

    for area in known_areas:
        if area.lower() in address:
            return area

    return "Unknown area"


def _is_generic_chain(
    place: PlaceResult,
) -> bool:
    text = _place_text(place)

    return _contains_any(
        text,
        GENERIC_CHAIN_KEYWORDS,
    )


def _is_valid_activity(
    place: PlaceResult,
    request: PlanRequest,
) -> bool:
    """
    Validate whether a place can reasonably serve as an activity.
    """
    text = _place_text(place)
    intents = set(
        _request_intents(request)
    )

    has_activity_signal = _contains_any(
        text,
        ACTIVITY_KEYWORDS,
    )

    has_food_signal = _contains_any(
        text,
        FOOD_VENUE_KEYWORDS,
    )

    is_library_or_workspace = _contains_any(
        text,
        {
            "library",
            "coworking",
            "workspace",
        },
    )

    # Work/study outings may intentionally use a library or workspace
    # as the main destination.
    if "work-friendly" in intents:
        if is_library_or_workspace:
            return True

        if _contains_any(
            text,
            CAFE_KEYWORDS,
        ):
            return not _is_generic_chain(
                place
            )

    # A normal café, bakery, or restaurant should not become an activity.
    if has_food_signal and not has_activity_signal:
        return False

    if not has_activity_signal:
        return False

    # Rainy-day outings require genuinely indoor activity signals.
    if "rainy-day" in intents:
        if _contains_any(
            text,
            OUTDOOR_ACTIVITY_KEYWORDS,
        ):
            return False

        if not _contains_any(
            text,
            INDOOR_ACTIVITY_KEYWORDS,
        ):
            return False

    # Active outings should not receive purely passive cultural venues
    # unless another requested intent explicitly supports them.
    if (
        "active" in intents
        and not {
            "cultural",
            "rainy-day",
        }
        & intents
    ):
        if _contains_any(
            text,
            {
                "museum",
                "gallery",
                "cinema",
                "theater",
                "theatre",
            },
        ):
            return False

    # Family outings should not use adult nightlife venues.
    if "family" in intents:
        if _contains_any(
            text,
            {
                "nightclub",
                "adult",
                "strip club",
            },
        ):
            return False

    return True


def _is_valid_restaurant(
    place: PlaceResult,
    request: PlanRequest,
) -> bool:
    """
    Validate whether a place is suitable as a meal stop.
    """
    text = _place_text(place)
    intents = set(
        _request_intents(request)
    )

    has_restaurant_signal = _contains_any(
        text,
        RESTAURANT_KEYWORDS,
    )

    has_cafe_signal = _contains_any(
        text,
        CAFE_KEYWORDS,
    )

    if has_restaurant_signal:
        return True

    # Café-style meal stops are allowed only for matching outing types.
    if has_cafe_signal:
        return bool(
            {
                "chill",
                "work-friendly",
                "budget",
                "foodie",
            }
            & intents
        )

    return False


def _is_valid_dessert(
    place: PlaceResult,
    *,
    allow_cafe_fallback: bool,
) -> bool:
    """
    Require a genuine dessert signal.

    Generic coffee chains are always excluded as planned dessert
    destinations.
    """
    text = _place_text(place)

    if _is_generic_chain(place):
        return False

    if _contains_any(
        text,
        DESSERT_KEYWORDS,
    ):
        return True

    if allow_cafe_fallback:
        return _contains_any(
            text,
            CAFE_KEYWORDS,
        )

    return False


def _is_valid_candidate(
    place: PlaceResult,
    category: str,
    request: PlanRequest,
    *,
    allow_dessert_cafe_fallback: bool = False,
) -> bool:
    if category == "activity":
        return _is_valid_activity(
            place,
            request,
        )

    if category == "restaurant":
        return _is_valid_restaurant(
            place,
            request,
        )

    if category == "dessert":
        return _is_valid_dessert(
            place,
            allow_cafe_fallback=(
                allow_dessert_cafe_fallback
            ),
        )

    return False


def _infer_activity_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

    if _contains_any(
        text,
        {
            "park",
            "garden",
            "monument",
            "viewpoint",
            "beach",
            "trail",
            "library",
        },
    ):
        return 0.0

    if _contains_any(
        text,
        {
            "cinema",
            "movie theater",
            "movie theatre",
            "theater",
            "theatre",
            "imax",
            "omni theater",
            "omni theatre",
        },
    ):
        return 22.0

    if "museum" in text:
        return 25.0

    if "karaoke" in text:
        return 35.0

    if "bowling" in text:
        return 30.0

    if _contains_any(
        text,
        {
            "arcade",
            "game",
        },
    ):
        return 25.0

    if _contains_any(
        text,
        {
            "aquarium",
            "zoo",
        },
    ):
        return 32.0

    if _contains_any(
        text,
        {
            "climbing",
            "skating",
            "sports",
            "recreation",
        },
    ):
        return 30.0

    return 28.0


def _infer_restaurant_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

    if _contains_any(
        text,
        {
            "fast food",
            "food court",
            "falafel",
            "shawarma",
            "sandwich",
        },
    ):
        return 20.0

    if _contains_any(
        text,
        {
            "pizza",
            "pizzeria",
            "cafe",
            "diner",
        },
    ):
        return 28.0

    if _contains_any(
        text,
        {
            "fine dining",
            "steakhouse",
            "seafood room",
            "ristorante",
            "rooftop",
            "tasting",
        },
    ):
        return 48.0

    return 36.0


def _infer_dessert_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

    if _contains_any(
        text,
        {
            "gelato",
            "ice cream",
            "frozen yogurt",
        },
    ):
        return 9.0

    if _contains_any(
        text,
        {
            "chocolate",
            "cake",
            "cupcake",
            "bakery",
            "pastry",
            "patisserie",
            "cookie",
            "donut",
            "doughnut",
        },
    ):
        return 13.0

    return 11.0


def _infer_cost(
    place: PlaceResult,
    category: str,
) -> float:
    if category == "activity":
        return _infer_activity_cost(
            place
        )

    if category == "restaurant":
        return _infer_restaurant_cost(
            place
        )

    if category == "dessert":
        return _infer_dessert_cost(
            place
        )

    return 25.0


def _infer_duration(
    category: str,
) -> int:
    durations = {
        "activity": 90,
        "restaurant": 90,
        "dessert": 40,
    }

    return durations.get(
        category,
        60,
    )


def _infer_vibes(
    place: PlaceResult,
    category: str,
) -> list[str]:
    text = _place_text(place)

    vibe_keywords = {
        "romantic": [
            "italian",
            "ristorante",
            "garden",
            "waterfront",
            "harbor",
            "view",
            "rooftop",
        ],
        "fun": [
            "karaoke",
            "cinema",
            "theater",
            "theatre",
            "game",
            "bowling",
            "arcade",
            "entertainment",
            "comedy",
        ],
        "chill": [
            "park",
            "cafe",
            "coffee",
            "book",
            "library",
            "garden",
            "gallery",
        ],
        "scenic": [
            "park",
            "garden",
            "waterfront",
            "harbor",
            "view",
            "beach",
        ],
        "cozy": [
            "cafe",
            "bakery",
            "coffee",
            "gelato",
            "bistro",
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
            "theater",
            "theatre",
            "restaurant",
            "cafe",
            "bowling",
            "karaoke",
            "arcade",
        ],
        "active": [
            "park",
            "sports",
            "bowling",
            "game",
            "trail",
            "recreation",
            "climbing",
            "skating",
        ],
        "cultural": [
            "museum",
            "gallery",
            "historic",
            "history",
            "art",
            "theatre",
            "theater",
        ],
        "nightlife": [
            "nightclub",
            "lounge",
            "bar",
            "karaoke",
            "music",
            "comedy",
        ],
        "family": [
            "children",
            "science",
            "aquarium",
            "zoo",
            "family",
        ],
        "group": [
            "karaoke",
            "bowling",
            "arcade",
            "food hall",
            "pizza",
            "barbecue",
        ],
        "work-friendly": [
            "coffee",
            "cafe",
            "library",
            "internet",
            "wifi",
            "workspace",
            "coworking",
        ],
        "rainy-day": [
            "museum",
            "gallery",
            "cinema",
            "theater",
            "theatre",
            "karaoke",
            "bowling",
            "arcade",
            "indoor",
        ],
    }

    vibes: list[str] = []

    for vibe, keywords in vibe_keywords.items():
        if any(
            _clean_text(keyword) in text
            for keyword in keywords
        ):
            vibes.append(vibe)

    if not vibes:
        defaults = {
            "activity": ["fun"],
            "restaurant": ["cozy"],
            "dessert": ["casual"],
        }

        vibes = defaults.get(
            category,
            ["casual"],
        )

    return list(
        dict.fromkeys(vibes)
    )


def _infer_food_tags(
    place: PlaceResult,
) -> list[str]:
    text = _place_text(place)
    tags: list[str] = []

    if _contains_any(
        text,
        {
            "italian",
            "bistro",
            "restaurant",
            "grill",
        },
    ):
        tags.append(
            "chicken options"
        )

    if _contains_any(
        text,
        {
            "italian",
            "risotto",
            "ristorante",
            "trattoria",
            "cucina",
            "osteria",
        },
    ):
        tags.append("risotto")

    if "vegan" in text:
        tags.append("vegan")

    if "vegetarian" in text:
        tags.append("vegetarian")

    if "sushi" in text:
        tags.append("seafood")

    return list(
        dict.fromkeys(tags)
    )


def place_to_venue(
    place: PlaceResult,
    category: str,
) -> Venue:
    return Venue(
        name=place.name,
        category=category,
        area=_infer_area(place),
        estimated_cost_per_person=(
            _infer_cost(
                place,
                category,
            )
        ),
        duration_minutes=(
            _infer_duration(category)
        ),
        vibe=_infer_vibes(
            place,
            category,
        ),
        food_tags=(
            _infer_food_tags(place)
            if category == "restaurant"
            else []
        ),
        latitude=place.latitude,
        longitude=place.longitude,
        formatted_address=(
            place.formatted_address
        ),
        website=place.website,
        opening_hours=(
            place.opening_hours
        ),
        source=place.source,
    )


def _restaurant_queries(
    request: PlanRequest,
) -> list[str]:
    preferences = {
        _clean_text(preference)
        for preference
        in request.food_preferences
    }

    intents = set(
        _request_intents(request)
    )

    queries: list[str] = []

    if "risotto" in preferences:
        queries.append(
            "Italian restaurant"
        )

    if "vegan" in preferences:
        queries.append(
            "vegan restaurant"
        )

    if "vegetarian" in preferences:
        queries.append(
            "vegetarian restaurant"
        )

    if "seafood" in preferences:
        queries.append("sushi")

    if "indian" in preferences:
        queries.append(
            "Indian restaurant"
        )

    if "chinese" in preferences:
        queries.append(
            "Chinese restaurant"
        )

    if "thai" in preferences:
        queries.append(
            "Thai restaurant"
        )

    if "mexican" in preferences:
        queries.append(
            "Mexican restaurant"
        )

    if "group" in intents:
        queries.extend(
            [
                "pizza restaurant",
                "barbecue restaurant",
                "grill",
                "food hall",
            ]
        )

    if not queries:
        queries.append(
            "restaurant"
        )

    return list(
        dict.fromkeys(queries)
    )


def _activity_queries(
    request: PlanRequest,
) -> list[str]:
    intents = _request_intents(
        request
    )

    queries = _profile_values(
        intents,
        "activity_queries",
    )

    return queries or [
        "museum"
    ]


def _dessert_queries(
    request: PlanRequest,
) -> list[str]:
    intents = _request_intents(
        request
    )

    preferred_keywords = (
        _profile_values(
            intents,
            "dessert_keywords",
        )
    )

    candidates = [
        "gelato",
        "ice cream",
        "bakery",
        "pastry",
        "chocolate",
        "dessert",
    ]

    prioritized = [
        query
        for query in candidates
        if any(
            query in keyword
            or keyword in query
            for keyword in preferred_keywords
        )
    ]

    return prioritized or [
        "gelato",
        "ice cream",
        "bakery",
        "dessert",
    ]


def _queries_for_category(
    request: PlanRequest,
    category: str,
) -> list[str]:
    if category == "activity":
        return _activity_queries(
            request
        )

    if category == "restaurant":
        return _restaurant_queries(
            request
        )

    if category == "dessert":
        return _dessert_queries(
            request
        )

    return []


def _deduplicate_places(
    places: list[PlaceResult],
) -> list[PlaceResult]:
    unique: list[PlaceResult] = []
    seen_ids: set[str] = set()
    seen_locations: set[
        tuple[str, float, float]
    ] = set()

    for place in places:
        location_key = (
            _clean_text(place.name),
            round(place.latitude, 5),
            round(place.longitude, 5),
        )

        if place.place_id in seen_ids:
            continue

        if location_key in seen_locations:
            continue

        seen_ids.add(place.place_id)
        seen_locations.add(
            location_key
        )
        unique.append(place)

    return unique


def _place_quality_score(
    place: PlaceResult,
    category: str,
    request: PlanRequest,
) -> float:
    """
    Rank validated candidates by intent, role quality, and distance.
    """
    text = _place_text(place)
    name_text = _clean_text(
        place.name
    )

    intents = _request_intents(
        request
    )

    intent_set = set(intents)

    positive_keywords = (
        _profile_values(
            intents,
            "positive_keywords",
        )
    )

    negative_keywords = (
        _profile_values(
            intents,
            "negative_keywords",
        )
    )

    if category == "restaurant":
        positive_keywords.extend(
            _profile_values(
                intents,
                "restaurant_keywords",
            )
        )

    if category == "dessert":
        positive_keywords.extend(
            _profile_values(
                intents,
                "dessert_keywords",
            )
        )

    score = 0.0

    for keyword in set(
        positive_keywords
    ):
        cleaned_keyword = (
            _clean_text(keyword)
        )

        if cleaned_keyword in text:
            score += 20

            if cleaned_keyword in name_text:
                score += 15

    for keyword in set(
        negative_keywords
    ):
        if _clean_text(
            keyword
        ) in text:
            score -= 50

    if category == "activity":
        if _contains_any(
            text,
            ACTIVITY_KEYWORDS,
        ):
            score += 25

        if "rainy-day" in intent_set:
            if _contains_any(
                text,
                INDOOR_ACTIVITY_KEYWORDS,
            ):
                score += 45

        if {
            "fun",
            "group",
        } & intent_set:
            if _contains_any(
                text,
                {
                    "karaoke",
                    "bowling",
                    "arcade",
                    "game",
                    "cinema",
                    "theater",
                    "theatre",
                    "comedy",
                },
            ):
                score += 40

    if category == "restaurant":
        preferences = {
            _clean_text(preference)
            for preference
            in request.food_preferences
        }

        if "risotto" in preferences:
            if _contains_any(
                text,
                {
                    "ristorante",
                    "trattoria",
                    "osteria",
                    "cucina",
                    "italian",
                },
            ):
                score += 45

        if "group" in intent_set:
            if _contains_any(
                text,
                GROUP_RESTAURANT_KEYWORDS,
            ):
                score += 45

            if _contains_any(
                text,
                {
                    "vegan only",
                    "vegan.only",
                    "juice",
                    "smoothie",
                },
            ):
                score -= 20

    if category == "dessert":
        if _contains_any(
            text,
            DESSERT_KEYWORDS,
        ):
            score += 45

        if _contains_any(
            name_text,
            {
                "gelato",
                "ice cream",
                "bakery",
                "pastry",
                "chocolate",
                "cookie",
                "donut",
                "doughnut",
                "dessert",
            },
        ):
            score += 25

        if _is_generic_chain(place):
            score -= 100

    if place.website:
        score += 3

    if place.opening_hours:
        score += 3

    if place.distance_meters is not None:
        score += max(
            0,
            10
            - place.distance_meters
            / 1500,
        )

    return score


def _rank_places(
    places: list[PlaceResult],
    category: str,
    request: PlanRequest,
) -> list[PlaceResult]:
    return sorted(
        places,
        key=lambda place: (
            -_place_quality_score(
                place,
                category,
                request,
            ),
            (
                place.distance_meters
                if place.distance_meters
                is not None
                else 999_999
            ),
            place.name.lower(),
        ),
    )


def _requested_categories(
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


def _filter_valid_places(
    places: list[PlaceResult],
    category: str,
    request: PlanRequest,
) -> list[PlaceResult]:
    """
    Apply strict role validation before ranking.

    Dessert searches get a controlled non-chain café fallback only
    when no genuine dessert destination is available.
    """
    strict_results = [
        place
        for place in places
        if _is_valid_candidate(
            place=place,
            category=category,
            request=request,
            allow_dessert_cafe_fallback=False,
        )
    ]

    if strict_results:
        return strict_results

    if category == "dessert":
        return [
            place
            for place in places
            if _is_valid_candidate(
                place=place,
                category=category,
                request=request,
                allow_dessert_cafe_fallback=True,
            )
        ]

    return []


def _search_category_places(
    request: PlanRequest,
    category: str,
) -> list[PlaceResult]:
    config = CATEGORY_SEARCH_CONFIG[
        category
    ]

    queries = _queries_for_category(
        request,
        category,
    )

    places: list[PlaceResult] = []

    for query in queries:
        try:
            query_results = search_places(
                query=query,
                city=request.city,
                category=config[
                    "default_category"
                ],
                limit=config[
                    "limit_per_query"
                ],
            )

            places.extend(
                query_results
            )

        except PlaceSearchError:
            # A failed sub-search should not erase successful results
            # from other intent queries.
            continue

    unique_places = (
        _deduplicate_places(
            places
        )
    )

    valid_places = (
        _filter_valid_places(
            places=unique_places,
            category=category,
            request=request,
        )
    )

    ranked_places = _rank_places(
        places=valid_places,
        category=category,
        request=request,
    )

    return ranked_places[
        : config["final_limit"]
    ]


def build_live_venues(
    request: PlanRequest,
) -> list[Venue]:
    """
    Search, validate, rank, and normalize live venue candidates.
    """
    categories = (
        _requested_categories(
            request
        )
    )

    live_venues: list[Venue] = []

    for category in categories:
        places = _search_category_places(
            request=request,
            category=category,
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
    Return validated live venues when all required roles exist.

    Otherwise fall back to the sample dataset so the planner remains
    usable.
    """
    try:
        live_venues = (
            build_live_venues(
                request
            )
        )

        required_categories = set(
            _requested_categories(
                request
            )
        )

        returned_categories = {
            venue.category
            for venue in live_venues
        }

        if required_categories.issubset(
            returned_categories
        ):
            return live_venues, True

    except PlaceSearchError:
        pass

    return list(VENUES), False
