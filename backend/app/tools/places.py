from __future__ import annotations

import os
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


def geoapify_is_configured() -> bool:
    """Return True when a Geoapify API key is configured."""
    return bool(os.getenv("GEOAPIFY_API_KEY"))


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
    properties = feature.get(
        "properties",
        {},
    )

    geometry = feature.get(
        "geometry",
        {},
    )

    coordinates = geometry.get(
        "coordinates",
        [0, 0],
    )

    if len(coordinates) < 2:
        coordinates = [0, 0]

    longitude = float(coordinates[0])
    latitude = float(coordinates[1])

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

    raw_datasource = datasource.get(
        "raw",
        {},
    )

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
        formatted_address=properties.get(
            "formatted",
            "",
        ),
        latitude=latitude,
        longitude=longitude,
        categories=[
            str(category)
            for category in categories
        ],
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


def geocode_city(
    city: str,
) -> tuple[float, float]:
    """
    Convert a city or location name into latitude and longitude.
    """
    api_key = os.getenv(
        "GEOAPIFY_API_KEY"
    )

    if not api_key:
        raise PlaceSearchError(
            "GEOAPIFY_API_KEY is not configured."
        )

    try:
        response = requests.get(
            GEOAPIFY_GEOCODING_URL,
            params={
                "text": city,
                "type": "city",
                "limit": 1,
                "format": "json",
                "apiKey": api_key,
            },
            timeout=15,
        )

        response.raise_for_status()

    except requests.RequestException as exc:
        detail = (
            response.text
            if "response" in locals()
            else str(exc)
        )

        raise PlaceSearchError(
            f"City geocoding failed: {detail}"
        ) from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise PlaceSearchError(
            "City geocoding returned invalid JSON."
        ) from exc

    results = payload.get(
        "results",
        [],
    )

    if not results:
        raise PlaceSearchError(
            f"Could not locate city: {city}"
        )

    result = results[0]

    try:
        return (
            float(result["lat"]),
            float(result["lon"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PlaceSearchError(
            "City geocoding response did not include "
            "valid coordinates."
        ) from exc


def search_places(
    query: str,
    city: str,
    category: str | None = None,
    limit: int = 10,
) -> list[PlaceResult]:
    """
    Search Geoapify for places inside a radius around a city.

    The Places API requires at least one category. The query is
    used locally to prioritize matching names because Geoapify's
    Places API is primarily category- and location-based.
    """
    api_key = os.getenv(
        "GEOAPIFY_API_KEY"
    )

    if not api_key:
        raise PlaceSearchError(
            "GEOAPIFY_API_KEY is not configured."
        )

    if not category:
        raise PlaceSearchError(
            "A Geoapify place category is required."
        )

    latitude, longitude = geocode_city(
        city
    )

    params: dict[str, str | int] = {
        "categories": category,
        "filter": (
            f"circle:{longitude},"
            f"{latitude},12000"
        ),
        "bias": (
            f"proximity:{longitude},"
            f"{latitude}"
        ),
        # Retrieve extra candidates so the local query ranking
        # has enough results to work with.
        "limit": min(max(limit * 3, limit), 50),
        "apiKey": api_key,
    }

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
            if "response" in locals()
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

    places = [
        _normalize_place(feature)
        for feature in features
    ]

    cleaned_query = query.strip().lower()

    if cleaned_query:
        matching_places = [
            place
            for place in places
            if cleaned_query in place.name.lower()
            or cleaned_query
            in place.formatted_address.lower()
        ]

        non_matching_places = [
            place
            for place in places
            if place not in matching_places
        ]

        places = (
            matching_places
            + non_matching_places
        )

    return places[:limit]
