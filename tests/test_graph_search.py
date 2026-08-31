from backend.app.graph_nodes import (
    build_search_query,
    required_search_categories,
    search_venues_node,
)
from backend.app.graph_orchestrator import (
    has_unsearched_categories,
    route_after_validation,
)
from backend.app.models import (
    PlaceResult,
    PlanRequest,
    Venue,
)


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=120,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=45,
    )


def make_existing_venue() -> Venue:
    return Venue(
        name="Existing Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=40,
        duration_minutes=60,
        vibe=[
            "chill",
        ],
        food_tags=[
            "chicken",
        ],
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="sample",
    )


def test_required_search_categories_maps_dinner() -> None:
    request = make_request()

    assert (
        required_search_categories(
            request
        )
        == [
            "restaurant",
        ]
    )


def test_search_query_uses_request_preferences() -> None:
    request = make_request()

    query = build_search_query(
        request=request,
        category="restaurant",
    )

    assert (
        "chill"
        in query
    )

    assert (
        "chicken"
        in query
    )

    assert (
        "restaurant"
        in query
    )


def test_unsearched_category_is_detected() -> None:
    request = make_request()

    assert (
        has_unsearched_categories(
            {
                "request": request,
                "searched_categories": [],
            }
        )
        is True
    )

    assert (
        has_unsearched_categories(
            {
                "request": request,
                "searched_categories": [
                    "restaurant",
                ],
            }
        )
        is False
    )


def test_validation_routes_to_search_after_repair() -> None:
    request = make_request()

    route = (
        route_after_validation(
            {
                "request": request,
                "has_usable_plan": False,
                "iteration_count": 1,
                "max_iterations": 4,
                "searched_categories": [],
            }
        )
    )

    assert (
        route
        == "search"
    )


def test_search_node_merges_live_venue(
    monkeypatch,
) -> None:
    request = make_request()

    place = PlaceResult(
        place_id="live-1",
        name="Live Restaurant",
        formatted_address=(
            "123 Newbury St, "
            "Boston, MA"
        ),
        latitude=42.3495,
        longitude=-71.0810,
        categories=[
            "catering.restaurant",
        ],
        city="Boston",
        district="Back Bay",
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="geoapify",
    )

    def fake_search_places(
        *,
        query,
        city,
        category,
        limit,
        center_coordinates=None,
    ):
        assert (
            city
            == "Boston"
        )

        assert (
            category
            == "catering.restaurant"
        )

        assert (
            limit
            == 10
        )

        assert (
            center_coordinates
            is None
        )

        return [
            place,
        ]

    monkeypatch.setattr(
        "backend.app.graph_nodes.search_places",
        fake_search_places,
    )

    result = search_venues_node(
        {
            "request": request,
            "venues": [
                make_existing_venue(),
            ],
            "plans": [],
            "searched_categories": [],
            "search_count": 0,
            "start_coordinates": None,
        }
    )

    assert (
        result[
            "search_count"
        ]
        == 1
    )

    assert (
        result[
            "searched_categories"
        ]
        == [
            "restaurant",
        ]
    )

    assert (
        len(
            result[
                "venues"
            ]
        )
        == 2
    )

    assert any(
        venue.name
        == "Live Restaurant"
        for venue
        in result[
            "venues"
        ]
    )

    assert (
        result[
            "plans"
        ]
    )


def test_search_node_does_not_repeat_category(
    monkeypatch,
) -> None:
    request = make_request()

    called = False

    def fake_search_places(
        **kwargs,
    ):
        nonlocal called

        called = True

        return []

    monkeypatch.setattr(
        "backend.app.graph_nodes.search_places",
        fake_search_places,
    )

    result = search_venues_node(
        {
            "request": request,
            "venues": [
                make_existing_venue(),
            ],
            "plans": [],
            "searched_categories": [
                "restaurant",
            ],
            "search_count": 1,
        }
    )

    assert (
        called
        is False
    )

    assert (
        "already searched"
        in result[
            "last_action"
        ].lower()
    )
