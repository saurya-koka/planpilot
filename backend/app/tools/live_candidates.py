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
        "limit_per_query": 6,
        "final_limit": 12,
    },
    "restaurant": {
        "default_category": "catering.restaurant",
        "limit_per_query": 8,
        "final_limit": 12,
    },
    "dessert": {
        "default_category": "catering",
        "limit_per_query": 6,
        "final_limit": 10,
    },
}


OUTING_PROFILES: dict[str, dict[str, Any]] = {
    "romantic": {
        "activity_queries": [
            "garden",
            "park",
            "scenic walk",
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
            "coffee",
        ],
        "positive_keywords": [
            "park",
            "garden",
            "waterfront",
            "book",
            "library",
            "gallery",
            "cafe",
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
            "coffee",
            "pastry",
            "gelato",
        ],
    },
    "active": {
        "activity_queries": [
            "park",
            "sports",
            "recreation",
            "bowling",
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
            "cinema",
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
            "museum",
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
            "museum",
            "park",
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
            "entertainment",
            "karaoke",
        ],
        "positive_keywords": [
            "museum",
            "cinema",
            "indoor",
            "karaoke",
            "bowling",
            "gallery",
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
            "cafe",
            "bakery",
            "chocolate",
            "pastry",
        ],
    },
    "work-friendly": {
        "activity_queries": [
            "coffee",
            "library",
        ],
        "positive_keywords": [
            "coffee",
            "cafe",
            "library",
            "workspace",
            "wifi",
            "internet",
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
            "coffee",
            "bakery",
            "pastry",
        ],
    },
    "group": {
        "activity_queries": [
            "karaoke",
            "bowling",
            "entertainment",
            "park",
        ],
        "positive_keywords": [
            "karaoke",
            "bowling",
            "game",
            "arcade",
            "entertainment",
            "park",
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
    "mcdonald",
    "burger king",
    "subway",
}


def _clean_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value


def _place_text(place: PlaceResult) -> str:
    return _clean_text(
        " ".join(
            [
                place.name,
                place.formatted_address,
                *place.categories,
            ]
        )
    )


def _venue_text(venue: Venue) -> str:
    return _clean_text(
        " ".join(
            [
                venue.name,
                venue.area,
                venue.formatted_address or "",
                *venue.vibe,
                *venue.food_tags,
            ]
        )
    )


def _request_intents(
    request: PlanRequest,
) -> list[str]:
    """
    Normalize free-form request vibes into supported outing profiles.
    """
    intents: list[str] = []

    for raw_vibe in request.vibe:
        cleaned = _clean_text(raw_vibe)

        if cleaned in OUTING_PROFILES:
            intents.append(cleaned)
            continue

        alias = VIBE_ALIASES.get(cleaned)

        if alias:
            intents.append(alias)

    if request.budget_total <= 80:
        intents.append("budget")

    if request.party_size >= 4:
        intents.append("group")

    if not intents:
        intents.append("fun")

    return list(dict.fromkeys(intents))


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

        raw_values = profile.get(
            key,
            [],
        )

        values.extend(
            str(value)
            for value in raw_values
        )

    return list(dict.fromkeys(values))


def _infer_area(place: PlaceResult) -> str:
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


def _infer_activity_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

    if any(
        keyword in text
        for keyword in [
            "park",
            "garden",
            "monument",
            "viewpoint",
            "beach",
            "trail",
        ]
    ):
        return 0.0

    if "museum" in text:
        return 25.0

    if "cinema" in text:
        return 22.0

    if "karaoke" in text:
        return 35.0

    if "bowling" in text:
        return 30.0

    return 28.0


def _infer_restaurant_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

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
            "rooftop",
        ]
    ):
        return 48.0

    return 36.0


def _infer_dessert_cost(
    place: PlaceResult,
) -> float:
    text = _place_text(place)

    if any(
        keyword in text
        for keyword in [
            "gelato",
            "ice cream",
            "frozen yogurt",
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
            "patisserie",
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
            "restaurant",
            "cafe",
            "bowling",
            "karaoke",
        ],
        "active": [
            "park",
            "sports",
            "bowling",
            "game",
            "trail",
            "recreation",
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
        ],
        "family": [
            "children",
            "science",
            "aquarium",
            "zoo",
            "family",
        ],
        "work-friendly": [
            "coffee",
            "cafe",
            "library",
            "internet",
            "wifi",
        ],
    }

    vibes: list[str] = []

    for vibe, keywords in vibe_keywords.items():
        if any(
            keyword in text
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

    return list(dict.fromkeys(vibes))


def _infer_food_tags(
    place: PlaceResult,
) -> list[str]:
    text = _place_text(place)

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
            "trattoria",
            "cucina",
            "osteria",
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
    return Venue(
        name=place.name,
        category=category,
        area=_infer_area(place),
        estimated_cost_per_person=_infer_cost(
            place,
            category,
        ),
        duration_minutes=_infer_duration(
            category
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
        formatted_address=place.formatted_address,
        website=place.website,
        opening_hours=place.opening_hours,
        source=place.source,
    )


def _restaurant_queries(
    request: PlanRequest,
) -> list[str]:
    preferences = {
        _clean_text(preference)
        for preference in request.food_preferences
    }

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

    if not queries:
        queries.append("restaurant")

    return list(dict.fromkeys(queries))


def _activity_queries(
    request: PlanRequest,
) -> list[str]:
    intents = _request_intents(request)

    queries = _profile_values(
        intents,
        "activity_queries",
    )

    return queries or ["museum"]


def _dessert_queries(
    request: PlanRequest,
) -> list[str]:
    intents = _request_intents(request)

    preferred_keywords = _profile_values(
        intents,
        "dessert_keywords",
    )

    prioritized = [
        query
        for query in [
            "gelato",
            "ice cream",
            "bakery",
            "dessert",
        ]
        if any(
            query in keyword
            or keyword in query
            for keyword in preferred_keywords
        )
    ]

    return prioritized or [
        "dessert",
        "ice cream",
        "bakery",
    ]


def _queries_for_category(
    request: PlanRequest,
    category: str,
) -> list[str]:
    if category == "activity":
        return _activity_queries(request)

    if category == "restaurant":
        return _restaurant_queries(request)

    if category == "dessert":
        return _dessert_queries(request)

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
        seen_locations.add(location_key)
        unique.append(place)

    return unique


def _place_quality_score(
    place: PlaceResult,
    category: str,
    request: PlanRequest,
) -> float:
    """
    Rank live candidates by outing intent, venue quality,
    specificity, distance, and undesirable-match penalties.
    """
    text = _place_text(place)
    intents = _request_intents(request)

    positive_keywords = _profile_values(
        intents,
        "positive_keywords",
    )

    negative_keywords = _profile_values(
        intents,
        "negative_keywords",
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

    for keyword in set(positive_keywords):
        cleaned_keyword = _clean_text(
            keyword
        )

        if cleaned_keyword in text:
            score += 20

            if cleaned_keyword in _clean_text(
                place.name
            ):
                score += 15

    for keyword in set(negative_keywords):
        if _clean_text(keyword) in text:
            score -= 45

    if category == "restaurant":
        requested_preferences = {
            _clean_text(preference)
            for preference
            in request.food_preferences
        }

        if "risotto" in requested_preferences:
            if any(
                keyword in text
                for keyword in [
                    "ristorante",
                    "trattoria",
                    "osteria",
                    "cucina",
                    "italian",
                ]
            ):
                score += 35

    if category == "dessert":
        if any(
            keyword in text
            for keyword in [
                "gelato",
                "ice cream",
                "chocolate",
                "dessert",
                "pastry",
                "bakery",
                "patisserie",
            ]
        ):
            score += 35
        else:
            score -= 20

        if any(
            chain in text
            for chain in GENERIC_CHAIN_KEYWORDS
        ):
            score -= 45

    if category == "activity":
        if any(
            category_name.startswith(
                "entertainment."
            )
            for category_name in place.categories
        ):
            score += 10

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

            places.extend(query_results)

        except PlaceSearchError:
            # One failed sub-search should not discard successful
            # results returned by the other intent queries.
            continue

    unique_places = _deduplicate_places(
        places
    )

    ranked_places = _rank_places(
        places=unique_places,
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
    Search multiple intent-aware place categories, rank the
    results, and convert them into planner Venue objects.
    """
    categories = _requested_categories(
        request
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
    Return intent-aware live venues when possible.

    Fall back to the sample dataset only when the live provider
    fails to produce enough categories for a usable itinerary.
    """
    try:
        live_venues = build_live_venues(
            request
        )

        required_categories = set(
            _requested_categories(request)
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
