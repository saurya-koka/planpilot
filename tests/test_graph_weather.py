from __future__ import annotations

from backend.app.graph_weather import (
    retrieve_weather_context_node,
)
from backend.app.models import (
    PlanRequest,
)
from backend.app.weather import (
    DeterministicWeatherProvider,
    WeatherSnapshot,
)


def make_request() -> PlanRequest:
    return PlanRequest(
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


def test_weather_node_low_risk(
    monkeypatch,
) -> None:
    provider = (
        DeterministicWeatherProvider(
            snapshot=WeatherSnapshot(
                condition="clear",
                temperature_c=22,
                precipitation_probability=0.10,
                wind_speed_kph=8,
                source="test",
            )
        )
    )

    monkeypatch.setattr(
        (
            "backend.app.graph_weather."
            "build_graph_weather_provider"
        ),
        lambda: provider,
    )

    result = (
        retrieve_weather_context_node(
            {
                "request": (
                    make_request()
                ),
            }
        )
    )

    assert (
        result[
            "weather_checked"
        ]
        is True
    )

    assert (
        result[
            "weather_risk_level"
        ]
        == "low"
    )

    assert (
        result[
            "weather_outdoor_safe"
        ]
        is True
    )

    assert (
        result[
            "weather_source"
        ]
        == "test"
    )


def test_weather_node_high_risk(
    monkeypatch,
) -> None:
    provider = (
        DeterministicWeatherProvider(
            snapshot=WeatherSnapshot(
                condition="heavy rain",
                temperature_c=17,
                precipitation_probability=0.90,
                wind_speed_kph=18,
                source="test",
            )
        )
    )

    monkeypatch.setattr(
        (
            "backend.app.graph_weather."
            "build_graph_weather_provider"
        ),
        lambda: provider,
    )

    result = (
        retrieve_weather_context_node(
            {
                "request": (
                    make_request()
                ),
            }
        )
    )

    assert (
        result[
            "weather_checked"
        ]
        is True
    )

    assert (
        result[
            "weather_risk_level"
        ]
        == "high"
    )

    assert (
        result[
            "weather_outdoor_safe"
        ]
        is False
    )

    assert any(
        "precipitation"
        in reason
        for reason
        in result[
            "weather_reasons"
        ]
    )


def test_weather_node_fails_open(
    monkeypatch,
) -> None:
    class BrokenProvider:
        def get_weather(
    		self,
    		*,
    		city: str,
    		date: str,
    		start_time: str = "18:00",
		) -> WeatherSnapshot:
            raise RuntimeError(
                "provider unavailable"
            )

    monkeypatch.setattr(
        (
            "backend.app.graph_weather."
            "build_graph_weather_provider"
        ),
        lambda: BrokenProvider(),
    )

    result = (
        retrieve_weather_context_node(
            {
                "request": (
                    make_request()
                ),
            }
        )
    )

    assert (
        result[
            "weather_checked"
        ]
        is False
    )

    assert (
        result[
            "weather_outdoor_safe"
        ]
        is True
    )

    assert any(
        "provider unavailable"
        in reason
        for reason
        in result[
            "weather_reasons"
        ]
    )


def test_weather_node_handles_missing_request() -> None:
    result = (
        retrieve_weather_context_node(
            {}
        )
    )

    assert (
        result[
            "weather_checked"
        ]
        is False
    )

    assert (
        result[
            "weather_outdoor_safe"
        ]
        is True
    )

def test_weather_constraints_remove_outdoor_venues() -> None:
    from backend.app.graph_weather import (
        apply_weather_constraints_node,
    )
    from backend.app.models import (
        Venue,
    )

    outdoor = Venue(
        name="Boston Public Garden",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=0,
        duration_minutes=60,
        vibe=[
            "outdoor",
        ],
        food_tags=[],
        latitude=42.354,
        longitude=-71.070,
        source="test",
    )

    indoor = Venue(
        name="Museum",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=90,
        vibe=[
            "indoor",
        ],
        food_tags=[],
        latitude=42.35,
        longitude=-71.08,
        source="test",
    )

    result = (
        apply_weather_constraints_node(
            {
                "venues": [
                    outdoor,
                    indoor,
                ],
                "weather_checked": True,
                "weather_outdoor_safe": False,
            }
        )
    )

    assert (
        result[
            "weather_adjusted"
        ]
        is True
    )

    assert (
        result[
            "weather_removed_venue_names"
        ]
        == [
            "Boston Public Garden",
        ]
    )

    assert [
        venue.name
        for venue
        in result[
            "venues"
        ]
    ] == [
        "Museum",
    ]


def test_weather_constraints_preserve_venues_when_safe() -> None:
    from backend.app.graph_weather import (
        apply_weather_constraints_node,
    )
    from backend.app.models import (
        Venue,
    )

    outdoor = Venue(
        name="Boston Public Garden",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=0,
        duration_minutes=60,
        vibe=[
            "outdoor",
        ],
        food_tags=[],
        latitude=42.354,
        longitude=-71.070,
        source="test",
    )

    result = (
        apply_weather_constraints_node(
            {
                "venues": [
                    outdoor,
                ],
                "weather_checked": True,
                "weather_outdoor_safe": True,
            }
        )
    )

    assert (
        result[
            "weather_adjusted"
        ]
        is False
    )

    assert (
        len(
            result[
                "venues"
            ]
        )
        == 1
    )
