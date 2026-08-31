from __future__ import annotations

from backend.app.models import (
    Venue,
)
from backend.app.weather_policy import (
    filter_venues_for_weather,
    is_outdoor_venue,
)


def make_venue(
    *,
    name: str,
    category: str,
    vibe: list[str],
) -> Venue:
    return Venue(
        name=name,
        category=category,
        area="Back Bay",
        estimated_cost_per_person=20,
        duration_minutes=60,
        vibe=vibe,
        food_tags=[],
        latitude=42.35,
        longitude=-71.08,
        source="test",
    )


def test_park_activity_is_outdoor() -> None:
    venue = make_venue(
        name="Boston Public Garden",
        category="activity",
        vibe=[
            "romantic",
        ],
    )

    assert (
        is_outdoor_venue(
            venue
        )
        is True
    )


def test_outdoor_vibe_is_outdoor() -> None:
    venue = make_venue(
        name="River Walk",
        category="activity",
        vibe=[
            "outdoor",
        ],
    )

    assert (
        is_outdoor_venue(
            venue
        )
        is True
    )


def test_indoor_activity_is_not_outdoor() -> None:
    venue = make_venue(
        name="Museum of Art",
        category="activity",
        vibe=[
            "indoor",
            "cultural",
        ],
    )

    assert (
        is_outdoor_venue(
            venue
        )
        is False
    )


def test_restaurant_is_not_removed_for_waterfront_name() -> None:
    venue = make_venue(
        name="Waterfront Restaurant",
        category="restaurant",
        vibe=[
            "romantic",
        ],
    )

    assert (
        is_outdoor_venue(
            venue
        )
        is False
    )


def test_unsafe_weather_removes_outdoor_activity() -> None:
    outdoor = make_venue(
        name="Boston Public Garden",
        category="activity",
        vibe=[
            "outdoor",
        ],
    )

    indoor = make_venue(
        name="Museum of Art",
        category="activity",
        vibe=[
            "indoor",
        ],
    )

    restaurant = make_venue(
        name="Dinner Place",
        category="restaurant",
        vibe=[
            "indoor",
        ],
    )

    result = (
        filter_venues_for_weather(
            venues=[
                outdoor,
                indoor,
                restaurant,
            ],
            outdoor_safe=False,
        )
    )

    assert (
        result.adjusted
        is True
    )

    assert (
        result.original_count
        == 3
    )

    assert (
        result.filtered_count
        == 2
    )

    assert (
        result.removed_venue_names
        == [
            "Boston Public Garden",
        ]
    )

    assert {
        venue.name
        for venue
        in result.venues
    } == {
        "Museum of Art",
        "Dinner Place",
    }


def test_safe_weather_preserves_all_venues() -> None:
    outdoor = make_venue(
        name="Boston Public Garden",
        category="activity",
        vibe=[
            "outdoor",
        ],
    )

    result = (
        filter_venues_for_weather(
            venues=[
                outdoor,
            ],
            outdoor_safe=True,
        )
    )

    assert (
        result.adjusted
        is False
    )

    assert (
        result.filtered_count
        == 1
    )
