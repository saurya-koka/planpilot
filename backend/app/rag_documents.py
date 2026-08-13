from __future__ import annotations

import re
from hashlib import sha256

from .models import (
    Venue,
)
from .vector_store import (
    VectorDocument,
)


def normalize_identifier(
    value: str,
) -> str:
    """
    Convert arbitrary text into a stable identifier fragment.
    """

    normalized = (
        value.strip()
        .lower()
    )

    normalized = re.sub(
        r"[^a-z0-9]+",
        "-",
        normalized,
    )

    normalized = normalized.strip(
        "-"
    )

    return (
        normalized
        or "unknown"
    )


def build_venue_document_id(
    venue: Venue,
) -> str:
    """
    Build a stable vector-document identifier for one venue.

    Coordinates are included when available so venues with identical
    names in different locations remain distinct.
    """

    location_key = (
        f"{venue.latitude:.5f},"
        f"{venue.longitude:.5f}"
        if (
            venue.latitude
            is not None
            and venue.longitude
            is not None
        )
        else (
            venue.formatted_address
            or venue.area
        )
    )

    identity = "|".join(
        [
            venue.name.strip().lower(),
            venue.category,
            str(
                location_key
            ).strip().lower(),
        ]
    )

    digest = sha256(
        identity.encode(
            "utf-8"
        )
    ).hexdigest()[:12]

    return (
        "venue-"
        f"{normalize_identifier(venue.name)}-"
        f"{digest}"
    )


def join_values(
    values: list[str],
) -> str:
    """
    Join non-empty string values into readable text.
    """

    cleaned = [
        value.strip()
        for value
        in values
        if value.strip()
    ]

    return ", ".join(
        cleaned
    )


def build_venue_text(
    venue: Venue,
) -> str:
    """
    Convert one Venue into retrieval-friendly natural language.

    The text deliberately preserves structured facts that are useful
    for semantic search:
    - category
    - area
    - vibe
    - food tags
    - estimated cost
    - opening hours
    - source
    """

    sentences: list[
        str
    ] = []

    sentences.append(
        (
            f"{venue.name} is a "
            f"{venue.category} in "
            f"{venue.area}."
        )
    )

    if venue.vibe:
        vibe_text = join_values(
            venue.vibe
        )

        sentences.append(
            (
                "It is suitable for "
                f"{vibe_text} outings."
            )
        )

    if venue.food_tags:
        food_text = join_values(
            venue.food_tags
        )

        sentences.append(
            (
                "Food options or tags "
                f"include {food_text}."
            )
        )

    sentences.append(
        (
            "Estimated cost is "
            f"{venue.estimated_cost_per_person:.0f} "
            "dollars per person."
        )
    )

    sentences.append(
        (
            "Typical visit duration is "
            f"{venue.duration_minutes} "
            "minutes."
        )
    )

    if venue.formatted_address:
        sentences.append(
            (
                "Address: "
                f"{venue.formatted_address}."
            )
        )

    if venue.opening_hours:
        sentences.append(
            (
                "Opening hours: "
                f"{venue.opening_hours}."
            )
        )

    if venue.website:
        sentences.append(
            (
                "A website is available "
                "for this venue."
            )
        )

    sentences.append(
        (
            "Data source: "
            f"{venue.source}."
        )
    )

    return " ".join(
        sentences
    )


def build_venue_metadata(
    venue: Venue,
) -> dict[
    str,
    str | int | float | bool,
]:
    """
    Convert Venue fields into Chroma-compatible scalar metadata.
    """

    metadata: dict[
        str,
        str | int | float | bool,
    ] = {
        "document_type": (
            "venue"
        ),
        "name": (
            venue.name
        ),
        "category": (
            venue.category
        ),
        "area": (
            venue.area
        ),
        "estimated_cost_per_person": (
            venue
            .estimated_cost_per_person
        ),
        "duration_minutes": (
            venue
            .duration_minutes
        ),
        "source": (
            venue.source
        ),
        "has_coordinates": (
            venue.latitude
            is not None
            and venue.longitude
            is not None
        ),
    }

    if venue.latitude is not None:
        metadata[
            "latitude"
        ] = venue.latitude

    if venue.longitude is not None:
        metadata[
            "longitude"
        ] = venue.longitude

    if venue.formatted_address:
        metadata[
            "formatted_address"
        ] = (
            venue.formatted_address
        )

    if venue.opening_hours:
        metadata[
            "opening_hours"
        ] = (
            venue.opening_hours
        )

    if venue.vibe:
        metadata[
            "vibe"
        ] = join_values(
            venue.vibe
        )

    if venue.food_tags:
        metadata[
            "food_tags"
        ] = join_values(
            venue.food_tags
        )

    return metadata


def venue_to_vector_document(
    venue: Venue,
) -> VectorDocument:
    """
    Convert one normalized PlanPilot Venue into a vector document.
    """

    return VectorDocument(
        document_id=(
            build_venue_document_id(
                venue
            )
        ),
        text=(
            build_venue_text(
                venue
            )
        ),
        metadata=(
            build_venue_metadata(
                venue
            )
        ),
    )


def venues_to_vector_documents(
    venues: list[
        Venue
    ],
) -> list[
    VectorDocument
]:
    """
    Convert a venue collection into vector documents.

    Duplicate document IDs are removed while preserving first-seen
    order.
    """

    documents: list[
        VectorDocument
    ] = []

    seen_ids: set[
        str
    ] = set()

    for venue in venues:
        document = (
            venue_to_vector_document(
                venue
            )
        )

        if (
            document.document_id
            in seen_ids
        ):
            continue

        seen_ids.add(
            document.document_id
        )

        documents.append(
            document
        )

    return documents
