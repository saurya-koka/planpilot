from __future__ import annotations

from backend.app.mcp_server import (
    check_planpilot_weather,
    parse_trip_request,
    plan_itinerary,
    planpilot_capabilities,
    search_planpilot_places,
)
from backend.app.models import (
    Itinerary,
    PlanRequest,
    Stop,
)
from backend.app.weather import (
    WeatherSnapshot,
)


def test_parse_trip_request() -> None:
    result = (
        parse_trip_request(
            (
                "Plan a chill chicken dinner "
                "in Boston for two people "
                "under 120 dollars."
            )
        )
    )

    assert isinstance(
        result,
        dict,
    )

    assert (
        result[
            "city"
        ]
        == "Boston"
    )


def test_capabilities_resource() -> None:
    result = (
        planpilot_capabilities()
    )

    assert (
        "PlanPilot MCP capabilities"
        in result
    )

    assert (
        "weather-aware itineraries"
        in result.lower()
    )


def test_place_search_failure_is_structured(
    monkeypatch,
) -> None:
    from backend.app import (
        mcp_server,
    )
    from backend.app.tools.places import (
        PlaceSearchError,
    )

    def fail_search(
        *,
        query: str,
        city: str,
        category: str | None,
        limit: int,
    ):
        raise PlaceSearchError(
            "provider unavailable"
        )

    monkeypatch.setattr(
        mcp_server,
        "search_places",
        fail_search,
    )

    result = (
        search_planpilot_places(
            query="chicken restaurant",
            city="Boston",
            category="restaurant",
            limit=5,
        )
    )

    assert (
        result[
            "success"
        ]
        is False
    )

    assert (
        result[
            "count"
        ]
        == 0
    )

    assert (
        "provider unavailable"
        in result[
            "error"
        ]
    )


def test_weather_tool_uses_planpilot_assessment(
    monkeypatch,
) -> None:
    from backend.app import (
        mcp_server,
    )

    snapshot = WeatherSnapshot(
        condition="heavy rain",
        temperature_c=18,
        precipitation_probability=0.90,
        wind_speed_kph=20,
        severe_weather=False,
        source="test-weather",
    )

    class FakeProvider:
        def get_weather(
            self,
            *,
            city: str,
            date: str,
            start_time: str,
        ) -> WeatherSnapshot:
            return snapshot

    monkeypatch.setattr(
        mcp_server,
        "OpenMeteoWeatherProvider",
        lambda: FakeProvider(),
    )

    result = (
        check_planpilot_weather(
            city="Boston",
            date="Friday",
            start_time="18:00",
        )
    )

    assert (
        result[
            "source"
        ]
        == "test-weather"
    )

    assert (
        result[
            "risk_level"
        ]
        == "high"
    )

    assert (
        result[
            "outdoor_safe"
        ]
        is False
    )


def test_plan_itinerary_runs_complete_graph(
    monkeypatch,
) -> None:
    from backend.app import (
        mcp_server,
    )

    request = PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
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

    plan = Itinerary(
        label="Best overall",
        title="Test Chicken Dinner",
        stops=[
            Stop(
                name="Test Restaurant",
                category="restaurant",
                area="Back Bay",
                estimated_cost=60,
                duration_minutes=90,
                latitude=42.35,
                longitude=-71.08,
                source="test",
            )
        ],
        total_cost=60,
        total_duration_minutes=90,
        estimated_travel_minutes=0,
        score=100,
        route_legs=[],
        validation_failures=[],
        reasons=[
            "Test itinerary"
        ],
        warnings=[],
    )

    monkeypatch.setattr(
        mcp_server,
        "parsed_to_plan_request",
        lambda **kwargs: request,
    )

    monkeypatch.setattr(
        mcp_server,
        "geocode_start_area",
        lambda request: (
            42.3507,
            -71.0797,
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "build_live_venues_with_fallback",
        lambda **kwargs: (
            [],
            True,
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "run_planpilot_graph",
        lambda **kwargs: {
            "plans": [
                plan,
            ],
            "venues": [],
            "has_usable_plan": True,
            "exhausted": False,
            "iteration_count": 0,
            "search_count": 0,
            "rag_used": True,
            "rag_result_count": 1,
            "rag_ranked_venue_names": [
                "Test Restaurant",
            ],
            "weather_checked": True,
            "weather_condition": "clear",
            "weather_risk_level": "low",
            "weather_outdoor_safe": True,
            "weather_adjusted": False,
            "weather_removed_venue_names": [],
        },
    )

    result = (
        plan_itinerary(
            text=(
                "Plan a chill chicken dinner "
                "in Boston."
            ),
            start_area="Back Bay",
            food_preferences=[
                "chicken",
            ],
        )
    )

    assert (
        result[
            "success"
        ]
        is True
    )

    assert (
        result[
            "graph_success"
        ]
        is True
    )

    assert (
        result[
            "rag_used"
        ]
        is True
    )

    assert (
        result[
            "weather_checked"
        ]
        is True
    )

    assert (
        len(
            result[
                "plans"
            ]
        )
        == 1
    )

    assert (
        result[
            "plans"
        ][0][
            "title"
        ]
        == "Test Chicken Dinner"
    )


def test_plan_itinerary_returns_structured_failure(
    monkeypatch,
) -> None:
    from backend.app import (
        mcp_server,
    )

    request = PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
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

    monkeypatch.setattr(
        mcp_server,
        "parsed_to_plan_request",
        lambda **kwargs: request,
    )

    monkeypatch.setattr(
        mcp_server,
        "geocode_start_area",
        lambda request: None,
    )

    monkeypatch.setattr(
        mcp_server,
        "build_live_venues_with_fallback",
        lambda **kwargs: (
            [],
            False,
        ),
    )

    monkeypatch.setattr(
        mcp_server,
        "run_planpilot_graph",
        lambda **kwargs: {
            "plans": [],
            "has_usable_plan": False,
            "exhausted": True,
        },
    )

    result = (
        plan_itinerary(
            text=(
                "Plan dinner in Boston."
            ),
            start_area="Back Bay",
        )
    )

    assert (
        result[
            "success"
        ]
        is False
    )

    assert (
        result[
            "plans"
        ]
        == []
    )

    assert (
        result[
            "graph_exhausted"
        ]
        is True
    )
