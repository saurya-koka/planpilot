from __future__ import annotations

from backend.app.models import (
    Venue,
)
from backend.app.rag_documents import (
    build_venue_document_id,
    build_venue_metadata,
    build_venue_text,
    venue_to_vector_document,
    venues_to_vector_documents,
)


def make_venue(
    *,
    name: str = "Test Restaurant",
) -> Venue:
    return Venue(
        name=name,
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=28,
        duration_minutes=90,
        vibe=[
            "chill",
            "casual",
        ],
        food_tags=[
            "chicken",
            "ramen",
        ],
        latitude=42.3500,
        longitude=-71.0800,
        formatted_address=(
            "100 Boylston St, "
            "Boston, MA"
        ),
        website=(
            "https://example.com"
        ),
        opening_hours=(
            "Mo-Su 11:00-22:00"
        ),
        source="geoapify",
    )


def test_venue_document_id_is_stable() -> None:
    venue = make_venue()

    first = (
        build_venue_document_id(
            venue
        )
    )

    second = (
        build_venue_document_id(
            venue
        )
    )

    assert (
        first
        == second
    )

    assert (
        first.startswith(
            "venue-test-restaurant-"
        )
    )


def test_different_locations_produce_different_ids() -> None:
    first = make_venue()

    second = make_venue()

    second.longitude = (
        -71.0900
    )

    assert (
        build_venue_document_id(
            first
        )
        != build_venue_document_id(
            second
        )
    )


def test_venue_text_contains_retrieval_facts() -> None:
    venue = make_venue()

    text = build_venue_text(
        venue
    ).lower()

    assert (
        "restaurant"
        in text
    )

    assert (
        "back bay"
        in text
    )

    assert (
        "chill"
        in text
    )

    assert (
        "chicken"
        in text
    )

    assert (
        "28 dollars"
        in text
    )


def test_metadata_contains_scalar_fields() -> None:
    venue = make_venue()

    metadata = (
        build_venue_metadata(
            venue
        )
    )

    assert (
        metadata[
            "document_type"
        ]
        == "venue"
    )

    assert (
        metadata[
            "category"
        ]
        == "restaurant"
    )

    assert (
        metadata[
            "area"
        ]
        == "Back Bay"
    )

    assert (
        metadata[
            "has_coordinates"
        ]
        is True
    )

    assert (
        metadata[
            "food_tags"
        ]
        == "chicken, ramen"
    )


def test_venue_converts_to_vector_document() -> None:
    venue = make_venue()

    document = (
        venue_to_vector_document(
            venue
        )
    )

    assert (
        document.document_id
    )

    assert (
        "Test Restaurant"
        in document.text
    )

    assert (
        document.metadata[
            "name"
        ]
        == "Test Restaurant"
    )


def test_duplicate_venues_are_deduplicated() -> None:
    venue = make_venue()

    documents = (
        venues_to_vector_documents(
            [
                venue,
                venue.model_copy(
                    deep=True
                ),
            ]
        )
    )

    assert (
        len(
            documents
        )
        == 1
    )
