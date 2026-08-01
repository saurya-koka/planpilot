from backend.app.models import PlaceResult
from backend.app.tools.places import (
    SearchInterpretation,
    _deduplicate_places,
    _rank_places,
    interpret_query,
)


def make_place(
    *,
    place_id: str,
    name: str,
    categories: list[str],
    distance_meters: int | None = None,
) -> PlaceResult:
    return PlaceResult(
        place_id=place_id,
        name=name,
        formatted_address=f"{name}, Boston, MA",
        latitude=42.36,
        longitude=-71.06,
        categories=categories,
        distance_meters=distance_meters,
        opening_hours=None,
        website=None,
        source="geoapify",
    )


def test_interprets_italian_restaurant_query() -> None:
    result = interpret_query(
        query="Italian restaurant",
        supplied_category="catering.restaurant",
    )

    assert result.categories == [
        "catering.restaurant.italian"
    ]

    assert "italian" in result.keywords


def test_interprets_sushi_query() -> None:
    result = interpret_query(
        query="sushi",
        supplied_category="catering.restaurant",
    )

    assert result.categories == [
        "catering.restaurant.sushi"
    ]

    assert "sushi" in result.keywords


def test_interprets_museum_query() -> None:
    result = interpret_query(
        query="museum",
        supplied_category="entertainment",
    )

    assert result.categories == [
        "entertainment.museum"
    ]


def test_interprets_vegan_query() -> None:
    result = interpret_query(
        query="vegan restaurant",
        supplied_category="catering.restaurant",
    )

    assert "vegan" in result.conditions
    assert "catering.restaurant" in result.categories


def test_deduplicates_places_by_id() -> None:
    first = make_place(
        place_id="same-id",
        name="Example Restaurant",
        categories=["catering.restaurant"],
    )

    second = make_place(
        place_id="same-id",
        name="Example Restaurant",
        categories=["catering.restaurant"],
    )

    deduplicated = _deduplicate_places(
        [first, second]
    )

    assert len(deduplicated) == 1


def test_ranking_prefers_matching_category() -> None:
    interpretation = SearchInterpretation(
        categories=[
            "catering.restaurant.italian"
        ],
        conditions=[],
        keywords=[
            "italian",
            "ristorante",
        ],
        fallback_categories=[
            "catering.restaurant"
        ],
    )

    italian = make_place(
        place_id="italian-1",
        name="Ristorante Example",
        categories=[
            "catering.restaurant",
            "catering.restaurant.italian",
        ],
        distance_meters=1000,
    )

    generic = make_place(
        place_id="generic-1",
        name="Downtown Restaurant",
        categories=[
            "catering.restaurant",
        ],
        distance_meters=100,
    )

    ranked = _rank_places(
        [generic, italian],
        interpretation,
    )

    assert ranked[0].place_id == "italian-1"


def test_ranking_uses_distance_as_tiebreaker() -> None:
    interpretation = SearchInterpretation(
        categories=[
            "entertainment.museum"
        ],
        conditions=[],
        keywords=[
            "museum",
        ],
        fallback_categories=[],
    )

    nearby = make_place(
        place_id="nearby",
        name="City Museum",
        categories=[
            "entertainment.museum"
        ],
        distance_meters=200,
    )

    farther = make_place(
        place_id="farther",
        name="History Museum",
        categories=[
            "entertainment.museum"
        ],
        distance_meters=1500,
    )

    ranked = _rank_places(
        [farther, nearby],
        interpretation,
    )

    assert ranked[0].place_id == "nearby"
