from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any

import requests
from dotenv import load_dotenv

from backend.app.models import PlaceResult

load_dotenv()


GEOAPIFY_GEOCODING_URL = (
    "https://api.geoapify.com/v1/geocode/search"
)

GEOAPIFY_PLACES_URL = (
    "https://api.geoapify.com/v2/places"
)


class PlaceSearchError(RuntimeError):
    """Raised when the live place provider cannot return results."""


@dataclass(frozen=True)
class SearchInterpretation:
    """
    Normalized interpretation of a user's place-search query.

    categories:
        Geoapify categories to request.

    conditions:
        Optional Geoapify dietary/access conditions.

    keywords:
        Words used to score and rank returned results.

    fallback_categories:
        Broader categories used when the specific search returns
        too few places.
    """

    categories: list[str]
    conditions: list[str]
    keywords: list[str]
    fallback_categories: list[str]


QUERY_RULES: list[dict[str, Any]] = [
    {
        "terms": [
            "italian",
            "italian restaurant",
            "pasta",
            "risotto",
        ],
        "categories": [
            "catering.restaurant.italian",
        ],
        "conditions": [],
        "keywords": [
            "italian",
            "pasta",
            "risotto",
            "trattoria",
            "osteria",
            "ristorante",
            "pizza",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "sushi",
            "japanese restaurant",
            "japanese food",
        ],
        "categories": [
            "catering.restaurant.sushi",
        ],
        "conditions": [],
        "keywords": [
            "sushi",
            "japanese",
            "ramen",
            "izakaya",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "indian",
            "indian restaurant",
            "indian food",
        ],
        "categories": [
            "catering.restaurant.indian",
        ],
        "conditions": [],
        "keywords": [
            "indian",
            "tandoor",
            "curry",
            "biryani",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "chinese",
            "chinese restaurant",
            "chinese food",
        ],
        "categories": [
            "catering.restaurant.chinese",
        ],
        "conditions": [],
        "keywords": [
            "chinese",
            "szechuan",
            "sichuan",
            "dim sum",
            "dumpling",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "thai",
            "thai restaurant",
            "thai food",
        ],
        "categories": [
            "catering.restaurant.thai",
        ],
        "conditions": [],
        "keywords": [
            "thai",
            "pad thai",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "mexican",
            "mexican restaurant",
            "tacos",
        ],
        "categories": [
            "catering.restaurant.mexican",
        ],
        "conditions": [],
        "keywords": [
            "mexican",
            "taco",
            "taqueria",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "vegan",
            "vegan restaurant",
            "plant based",
            "plant-based",
        ],
        "categories": [
            "catering.restaurant",
            "catering.cafe",
        ],
        "conditions": [
            "vegan",
        ],
        "keywords": [
            "vegan",
            "plant based",
            "plant-based",
        ],
        "fallback": [
            "vegan",
            "vegan.only",
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "vegetarian",
            "vegetarian restaurant",
            "meat free",
            "meat-free",
        ],
        "categories": [
            "catering.restaurant",
            "catering.cafe",
        ],
        "conditions": [
            "vegetarian",
        ],
        "keywords": [
            "vegetarian",
            "meat free",
            "meat-free",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "halal",
            "halal restaurant",
        ],
        "categories": [
            "catering.restaurant",
        ],
        "conditions": [
            "halal",
        ],
        "keywords": [
            "halal",
        ],
        "fallback": [
            "halal",
            "halal.only",
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "gluten free",
            "gluten-free",
        ],
        "categories": [
            "catering.restaurant",
            "catering.cafe",
        ],
        "conditions": [
            "gluten_free",
        ],
        "keywords": [
            "gluten free",
            "gluten-free",
        ],
        "fallback": [
            "catering.restaurant",
        ],
    },
    {
        "terms": [
            "dessert",
            "desserts",
            "ice cream",
            "bakery",
            "cake",
            "pastry",
            "sweets",
        ],
        "categories": [
            "catering.ice_cream",
            "catering.cafe",
        ],
        "conditions": [],
        "keywords": [
            "dessert",
            "ice cream",
            "gelato",
            "bakery",
            "cake",
            "pastry",
            "sweet",
            "chocolate",
        ],
        "fallback": [
            "catering",
        ],
    },
    {
        "terms": [
            "coffee",
            "cafe",
            "coffee shop",
        ],
        "categories": [
            "catering.cafe",
        ],
        "conditions": [],
        "keywords": [
            "coffee",
            "cafe",
            "espresso",
            "roastery",
        ],
        "fallback": [
            "catering",
        ],
    },
    {
        "terms": [
            "museum",
            "museums",
        ],
        "categories": [
            "entertainment.museum",
        ],
        "conditions": [],
        "keywords": [
            "museum",
            "gallery",
        ],
        "fallback": [
            "entertainment.culture",
        ],
    },
    {
        "terms": [
            "movie",
            "cinema",
            "movie theater",
            "movie theatre",
        ],
        "categories": [
            "entertainment.cinema",
        ],
        "conditions": [],
        "keywords": [
            "cinema",
            "movie",
            "theatre",
            "theater",
            "imax",
        ],
        "fallback": [
            "entertainment",
        ],
    },
    {
        "terms": [
            "park",
            "garden",
            "outdoor walk",
            "scenic walk",
        ],
        "categories": [
            "leisure.park",
        ],
        "conditions": [],
        "keywords": [
            "park",
            "garden",
            "common",
            "esplanade",
            "waterfront",
        ],
        "fallback": [
            "leisure",
        ],
    },
    {
        "terms": [
            "karaoke",
            "duo karaoke",
        ],
        # Geoapify does not always have a sufficiently specific
        # karaoke category, so search entertainment broadly and
        # strongly rank names containing "karaoke".
        "categories": [
            "entertainment",
        ],
        "conditions": [],
        "keywords": [
            "karaoke",
            "sing",
        ],
        "fallback": [
            "catering.bar",
            "adult.nightclub",
        ],
    },
]


GENERIC_QUERY_WORDS = {
    "a",
    "an",
    "and",
    "best",
    "find",
    "good",
    "in",
    "near",
    "nearby",
    "place",
    "places",
    "restaurant",
    "restaurants",
    "the",
}


def geoapify_is_configured() -> bool:
    """Return True when a Geoapify API key is configured."""
    return bool(os.getenv("GEOAPIFY_API_KEY"))


def _clean_text(value: str) -> str:
    """
    Normalize text for keyword comparisons.
    """
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\s-]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value


def _query_tokens(query: str) -> list[str]:
    """
    Extract useful search tokens while excluding generic words.
    """
    cleaned = _clean_text(query)

    return [
        token
        for token in cleaned.split()
        if token not in GENERIC_QUERY_WORDS
        and len(token) > 1
    ]


def interpret_query(
    query: str,
    supplied_category: str | None,
) -> SearchInterpretation:
    """
    Convert a human query into Geoapify categories, conditions,
    and local ranking keywords.

    An explicitly supplied category remains the default unless a
    more specific query rule is detected.
    """
    cleaned_query = _clean_text(query)

    for rule in QUERY_RULES:
        if any(
            _clean_text(term) in cleaned_query
            for term in rule["terms"]
        ):
            return SearchInterpretation(
                categories=list(rule["categories"]),
                conditions=list(rule["conditions"]),
                keywords=list(
                    dict.fromkeys(
                        [
                            *rule["keywords"],
                            *_query_tokens(query),
                        ]
                    )
                ),
                fallback_categories=list(rule["fallback"]),
            )

    categories = (
        [supplied_category]
        if supplied_category
        else ["catering.restaurant"]
    )

    return SearchInterpretation(
        categories=categories,
        conditions=[],
        keywords=_query_tokens(query),
        fallback_categories=[],
    )


def _extract_name(
    properties: dict[str, Any],
) -> str:
    return (
        properties.get("name")
        or properties.get("address_line1")
        or properties.get("formatted")
        or "Unnamed place"
    )


def _normalize_place(
    feature: dict[str, Any],
) -> PlaceResult:
    """
    Convert one Geoapify GeoJSON feature into PlaceResult.
    """
    properties = feature.get(
        "properties",
        {},
    )

    if not isinstance(properties, dict):
        properties = {}

    geometry = feature.get(
        "geometry",
        {},
    )

    if not isinstance(geometry, dict):
        geometry = {}

    coordinates = geometry.get(
        "coordinates",
        [0, 0],
    )

    if (
        not isinstance(coordinates, list)
        or len(coordinates) < 2
    ):
        coordinates = [0, 0]

    try:
        longitude = float(coordinates[0])
        latitude = float(coordinates[1])
    except (TypeError, ValueError):
        longitude = 0.0
        latitude = 0.0

    categories = properties.get(
        "categories",
        [],
    )

    if not isinstance(categories, list):
        categories = []

    distance = properties.get("distance")

    if distance is not None:
        try:
            distance = int(distance)
        except (TypeError, ValueError):
            distance = None

    datasource = properties.get(
        "datasource",
        {},
    )

    if not isinstance(datasource, dict):
        datasource = {}

    raw_datasource = datasource.get(
        "raw",
        {},
    )

    if not isinstance(raw_datasource, dict):
        raw_datasource = {}

    place_id = (
        properties.get("place_id")
        or raw_datasource.get("osm_id")
        or f"{latitude},{longitude}"
    )

    opening_hours = properties.get(
        "opening_hours"
    )

    website = (
        properties.get("website")
        or raw_datasource.get("website")
    )

    return PlaceResult(
        place_id=str(place_id),
        name=_extract_name(properties),
        formatted_address=str(
            properties.get(
                "formatted",
                "",
            )
        ),
        latitude=latitude,
        longitude=longitude,
        categories=[
            str(category)
            for category in categories
        ],
        city=(
            str(properties["city"])
            if properties.get("city")
            else None
        ),
        district=(
            str(properties["district"])
            if properties.get("district")
            else None
        ),
        suburb=(
            str(properties["suburb"])
            if properties.get("suburb")
            else None
        ),
        postcode=(
            str(properties["postcode"])
            if properties.get("postcode")
            else None
        ),
        state=(
            str(properties["state"])
            if properties.get("state")
            else None
        ),
        country=(
            str(properties["country"])
            if properties.get("country")
            else None
        ),
        distance_meters=distance,
        opening_hours=(
            str(opening_hours)
            if opening_hours
            else None
        ),
        website=(
            str(website)
            if website
            else None
        ),
        source="geoapify",
    )


def geocode_location(
    location: str,
    location_type: str | None = None,
) -> tuple[float, float]:
    """
    Convert a location name or address into coordinates.

    location_type can be set to values such as "city". For
    neighborhood searches such as Davis Square, it should remain
    None so Geoapify can determine the location type.
    """
    api_key = os.getenv(
        "GEOAPIFY_API_KEY"
    )

    if not api_key:
        raise PlaceSearchError(
            "GEOAPIFY_API_KEY is not configured."
        )

    params: dict[str, str | int] = {
        "text": location,
        "limit": 1,
        "format": "json",
        "apiKey": api_key,
    }

    if location_type:
        params["type"] = location_type

    response: requests.Response | None = None

    try:
        response = requests.get(
            GEOAPIFY_GEOCODING_URL,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        detail = (
            response.text
            if response is not None
            else str(exc)
        )

        raise PlaceSearchError(
            f"Location geocoding failed: {detail}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PlaceSearchError(
            "Location geocoding returned invalid JSON."
        ) from exc

    results = payload.get(
        "results",
        [],
    )

    if not results:
        raise PlaceSearchError(
            f"Could not locate: {location}"
        )

    result = results[0]

    try:
        return (
            float(result["lat"]),
            float(result["lon"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PlaceSearchError(
            "Location geocoding response did not include "
            "valid coordinates."
        ) from exc


def geocode_city(
    city: str,
) -> tuple[float, float]:
    """
    Convert a city name into latitude and longitude.
    """
    return geocode_location(
        location=city,
        location_type="city",
    )


def _request_places(
    *,
    latitude: float,
    longitude: float,
    categories: list[str],
    conditions: list[str],
    result_limit: int,
    api_key: str,
) -> list[PlaceResult]:
    """
    Execute one Geoapify Places API request.
    """
    if not categories:
        return []

    params: dict[str, str | int] = {
        "categories": ",".join(categories),
        "filter": (
            f"circle:{longitude},"
            f"{latitude},12000"
        ),
        "bias": (
            f"proximity:{longitude},"
            f"{latitude}"
        ),
        "limit": min(
            max(result_limit, 1),
            100,
        ),
        "apiKey": api_key,
    }

    if conditions:
        params["conditions"] = ",".join(conditions)

    response: requests.Response | None = None

    try:
        response = requests.get(
            GEOAPIFY_PLACES_URL,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        detail = (
            response.text
            if response is not None
            else str(exc)
        )

        raise PlaceSearchError(
            f"Place search failed: {detail}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PlaceSearchError(
            "Place search returned invalid JSON."
        ) from exc

    features = payload.get(
        "features",
        [],
    )

    if not isinstance(features, list):
        return []

    return [
        _normalize_place(feature)
        for feature in features
    ]


def _deduplicate_places(
    places: list[PlaceResult],
) -> list[PlaceResult]:
    """
    Remove duplicate places by provider ID and normalized
    name/address combination.
    """
    unique: list[PlaceResult] = []
    seen_ids: set[str] = set()
    seen_names: set[tuple[str, str]] = set()

    for place in places:
        normalized_key = (
            _clean_text(place.name),
            _clean_text(place.formatted_address),
        )

        if place.place_id in seen_ids:
            continue

        if normalized_key in seen_names:
            continue

        seen_ids.add(place.place_id)
        seen_names.add(normalized_key)
        unique.append(place)

    return unique


def _relevance_score(
    place: PlaceResult,
    interpretation: SearchInterpretation,
) -> float:
    """
    Score a place by keyword/category relevance and distance.
    """
    normalized_name = _clean_text(place.name)
    normalized_address = _clean_text(
        place.formatted_address
    )

    normalized_categories = [
        _clean_text(category)
        for category in place.categories
    ]

    score = 0.0

    for keyword in interpretation.keywords:
        normalized_keyword = _clean_text(keyword)

        if not normalized_keyword:
            continue

        if normalized_keyword == normalized_name:
            score += 80

        elif normalized_keyword in normalized_name:
            score += 40

        if normalized_keyword in normalized_address:
            score += 8

        if any(
            normalized_keyword in category
            for category in normalized_categories
        ):
            score += 25

    requested_categories = {
        category.lower()
        for category in interpretation.categories
    }

    returned_categories = {
        category.lower()
        for category in place.categories
    }

    for requested in requested_categories:
        if requested in returned_categories:
            score += 30
        elif any(
            category.startswith(
                f"{requested}."
            )
            for category in returned_categories
        ):
            score += 20

    if place.opening_hours:
        score += 2

    if place.website:
        score += 2

    if place.distance_meters is not None:
        # Nearby results receive a small bonus without letting
        # distance overwhelm query relevance.
        distance_bonus = max(
            0,
            10 - place.distance_meters / 1000,
        )

        score += distance_bonus

    return score


def _rank_places(
    places: list[PlaceResult],
    interpretation: SearchInterpretation,
) -> list[PlaceResult]:
    """
    Sort by relevance first, then by distance.
    """
    return sorted(
        places,
        key=lambda place: (
            -_relevance_score(
                place,
                interpretation,
            ),
            (
                place.distance_meters
                if place.distance_meters is not None
                else 999_999
            ),
            place.name.lower(),
        ),
    )


def search_places(
    query: str,
    city: str,
    category: str | None = None,
    limit: int = 10,
    center_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None,
) -> list[PlaceResult]:
    """
    Search Geoapify using query-aware category mapping.

    The process is:

    1. Interpret the natural-language query.
    2. Use explicit local coordinates when supplied.
    3. Otherwise fall back to the city center.
    4. Search using specific Geoapify categories/conditions.
    5. Search broader fallback categories if too few places return.
    6. Deduplicate and rank all candidates locally.

    V2.8 uses center_coordinates to bias venue recall around the
    user's actual starting area rather than the broad city center.
    """

    api_key = os.getenv(
        "GEOAPIFY_API_KEY"
    )

    if not api_key:
        raise PlaceSearchError(
            "GEOAPIFY_API_KEY is not configured."
        )

    if limit < 1:
        raise PlaceSearchError(
            "Search limit must be at least 1."
        )

    interpretation = interpret_query(
        query=query,
        supplied_category=category,
    )

    if center_coordinates is not None:
        latitude = float(
            center_coordinates[
                0
            ]
        )

        longitude = float(
            center_coordinates[
                1
            ]
        )

    else:
        latitude, longitude = (
            geocode_city(
                city
            )
        )

    primary_places = _request_places(
        latitude=latitude,
        longitude=longitude,
        categories=(
            interpretation.categories
        ),
        conditions=(
            interpretation.conditions
        ),
        result_limit=min(
            max(
                limit * 5,
                20,
            ),
            100,
        ),
        api_key=api_key,
    )

    all_places = list(
        primary_places
    )

    # Broaden only when the specific query did not produce enough
    # candidates. The same location bias is preserved for fallback
    # retrieval.
    if (
        len(
            primary_places
        ) < limit
        and interpretation.fallback_categories
    ):
        fallback_places = (
            _request_places(
                latitude=latitude,
                longitude=longitude,
                categories=(
                    interpretation
                    .fallback_categories
                ),
                conditions=[],
                result_limit=min(
                    max(
                        limit * 5,
                        20,
                    ),
                    100,
                ),
                api_key=api_key,
            )
        )

        all_places.extend(
            fallback_places
        )

    unique_places = (
        _deduplicate_places(
            all_places
        )
    )

    ranked_places = (
        _rank_places(
            unique_places,
            interpretation,
        )
    )

    return ranked_places[
        :limit
    ]

