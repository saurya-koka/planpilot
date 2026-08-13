from __future__ import annotations

from backend.app.graph_orchestrator import (
    run_planpilot_graph,
)
from backend.app.models import (
    PlaceResult,
    PlanRequest,
    Venue,
)


def make_request(
    *,
    budget_total: float = 120,
) -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=budget_total,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=45,
    )


def make_expensive_venue() -> Venue:
    return Venue(
        name="Expensive Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=100,
        duration_minutes=60,
        vibe=[
            "chill",
        ],
        food_tags=[],
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="sample",
    )


def test_compiled_graph_finishes_without_search_when_plan_valid(
    monkeypatch,
) -> None:
    request = make_request(
        budget_total=250,
    )

    search_called = False

    def fake_search_places(
        **kwargs,
    ):
        nonlocal search_called

        search_called = True

        return []

    monkeypatch.setattr(
        "backend.app.graph_nodes.search_places",
        fake_search_places,
    )

    result = run_planpilot_graph(
        user_message=(
            "Plan a chill dinner."
        ),
        request=request,
        venues=[
            make_expensive_venue(),
        ],
        start_coordinates=None,
        max_iterations=4,
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )

    assert (
        result[
            "exhausted"
        ]
        is False
    )

    assert (
        search_called
        is False
    )


def test_compiled_graph_can_take_search_path(
    monkeypatch,
) -> None:
    request = make_request(
        budget_total=80,
    )

    live_place = PlaceResult(
        place_id="search-result-1",
        name="Affordable Live Restaurant",
        formatted_address=(
            "100 Boylston St, "
            "Boston, MA"
        ),
        latitude=42.3505,
        longitude=-71.0750,
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

    search_call_count = 0

    def fake_search_places(
        *,
        query,
        city,
        category,
        limit,
    ):
        nonlocal search_call_count

        search_call_count += 1

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

        return [
            live_place,
        ]

    monkeypatch.setattr(
        "backend.app.graph_nodes.search_places",
        fake_search_places,
    )

    result = run_planpilot_graph(
        user_message=(
            "Plan a cheap chill dinner."
        ),
        request=request,
        venues=[
            make_expensive_venue(),
        ],
        start_coordinates=None,
        max_iterations=4,
    )

    assert (
        search_call_count
        == 1
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

    assert any(
        venue.name
        == "Affordable Live Restaurant"
        for venue
        in result[
            "venues"
        ]
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )

    assert (
        result[
            "exhausted"
        ]
        is False
    )


def test_compiled_graph_stops_when_no_strategy_succeeds(
    monkeypatch,
) -> None:
    request = make_request(
        budget_total=20,
    )

    def fake_search_places(
        **kwargs,
    ):
        return []

    monkeypatch.setattr(
        "backend.app.graph_nodes.search_places",
        fake_search_places,
    )

    result = run_planpilot_graph(
        user_message=(
            "Plan an extremely cheap dinner."
        ),
        request=request,
        venues=[
            make_expensive_venue(),
        ],
        start_coordinates=None,
        max_iterations=2,
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is False
    )

    assert (
        result[
            "exhausted"
        ]
        is True
    )

    assert (
        result[
            "iteration_count"
        ]
        == 2
    )
