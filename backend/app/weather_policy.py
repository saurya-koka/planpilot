from __future__ import annotations

from dataclasses import (
    dataclass,
)

from .models import (
    Venue,
)


OUTDOOR_NAME_KEYWORDS = {
    "park",
    "garden",
    "beach",
    "trail",
    "esplanade",
    "waterfront walk",
    "scenic walk",
    "hiking",
    "hike",
    "playground",
    "outdoor",
}


OUTDOOR_VIBE_TAGS = {
    "outdoor",
    "outdoors",
}


@dataclass(frozen=True)
class WeatherVenueFilterResult:
    """
    Result of applying weather suitability rules to a venue pool.
    """

    venues: list[
        Venue
    ]

    removed_venue_names: list[
        str
    ]

    original_count: int

    filtered_count: int

    adjusted: bool


def normalize_text(
    value: str,
) -> str:
    """
    Normalize free-form text for deterministic keyword checks.
    """

    return (
        value
        .strip()
        .lower()
    )


def is_outdoor_venue(
    venue: Venue,
) -> bool:
    """
    Return True when a venue is clearly an outdoor activity.

    V2.9 intentionally uses conservative classification.

    Restaurants and dessert venues are never removed merely because
    their name or vibe contains an outdoor-related word.

    This prevents weather logic from accidentally deleting legitimate
    dinner destinations such as waterfront restaurants.
    """

    category = normalize_text(
        venue.category
    )

    if category != "activity":
        return False

    name = normalize_text(
        venue.name
    )

    vibes = {
        normalize_text(
            vibe
        )
        for vibe
        in venue.vibe
    }

    if any(
        tag in vibes
        for tag
        in OUTDOOR_VIBE_TAGS
    ):
        return True

    if any(
        keyword in name
        for keyword
        in OUTDOOR_NAME_KEYWORDS
    ):
        return True

    return False


def filter_venues_for_weather(
    *,
    venues: list[
        Venue
    ],
    outdoor_safe: bool,
) -> WeatherVenueFilterResult:
    """
    Filter clearly outdoor activity venues when weather is unsafe.

    Safe weather:
        preserve the entire venue pool.

    Unsafe weather:
        remove outdoor activities while preserving indoor activities,
        restaurants, and dessert venues.

    Fail-safe behavior:
        if filtering would remove every single venue, retain the
        original pool. Later V2.9 steps will add weather-aware live
        search/replanning for this edge case.
    """

    original = list(
        venues
    )

    if outdoor_safe:
        return WeatherVenueFilterResult(
            venues=original,
            removed_venue_names=[],
            original_count=len(
                original
            ),
            filtered_count=len(
                original
            ),
            adjusted=False,
        )

    retained: list[
        Venue
    ] = []

    removed: list[
        str
    ] = []

    for venue in original:
        if is_outdoor_venue(
            venue
        ):
            removed.append(
                venue.name
            )

        else:
            retained.append(
                venue
            )

    if (
        original
        and not retained
    ):
        return WeatherVenueFilterResult(
            venues=original,
            removed_venue_names=[],
            original_count=len(
                original
            ),
            filtered_count=len(
                original
            ),
            adjusted=False,
        )

    return WeatherVenueFilterResult(
        venues=retained,
        removed_venue_names=removed,
        original_count=len(
            original
        ),
        filtered_count=len(
            retained
        ),
        adjusted=bool(
            removed
        ),
    )
