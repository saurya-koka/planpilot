from __future__ import annotations

from backend.app.graph_orchestrator import (
    run_planpilot_graph,
)
from backend.app.models import (
    PlanRequest,
    Venue,
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
            "activity",
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=45,
    )


def make_outdoor_activity() -> Venue:
    return Venue(
        name="Boston Public Garden",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=0,
        duration_minutes=60,
        vibe=[
            "outdoor",
            "chill",
        ],
        food_tags=[],
        latitude=42.3540,
        longitude=-71.0700,
        source="test",
    )


def make_indoor_activity() -> Venue:
    return Venue(
        name="Back Bay Art Gallery",
        category="activity",
        area="Back Bay",
        estimated_cost_per_person=15,
        duration_minutes=60,
        vibe=[
            "indoor",
            "chill",
        ],
        food_tags=[],
        latitude=42.3500,
        longitude=-71.0800,
        source="test",
    )


def make_restaurant() -> Venue:
    return Venue(
        name="Back Bay Chicken Kitchen",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=90,
        vibe=[
            "indoor",
            "chill",
        ],
        food_tags=[
            "chicken",
            "chicken options",
        ],
        latitude=42.3495,
        longitude=-71.0810,
        source="test",
    )


def test_high_risk_weather_replans_away_from_outdoor_activity(
    monkeypatch,
    tmp_path,
) -> None:
    """
    Full V2.9 graph proof:

    storm
        ->
    weather assessment
        ->
    remove outdoor candidate
        ->
    RAG over weather-safe pool
        ->
    planner builds indoor itinerary
    """

    storm_provider = (
        DeterministicWeatherProvider(
            snapshot=WeatherSnapshot(
                condition="thunderstorm",
                temperature_c=18,
                precipitation_probability=0.90,
                wind_speed_kph=25,
                severe_weather=True,
                source="storm-test",
            )
        )
    )

    monkeypatch.setattr(
        (
            "backend.app.graph_weather."
            "build_graph_weather_provider"
        ),
        lambda: storm_provider,
    )

    # Keep the RAG database isolated from the normal persistent
    # PlanPilot Chroma collection.
    monkeypatch.setenv(
        "PLANPILOT_CHROMA_PATH",
        str(
            tmp_path
            / "weather_replan_chroma"
        ),
    )

    result = (
        run_planpilot_graph(
            user_message=(
                "Plan a chill activity and "
                "chicken dinner in Back Bay."
            ),
            request=make_request(),
            venues=[
                make_outdoor_activity(),
                make_indoor_activity(),
                make_restaurant(),
            ],
            start_coordinates=(
                42.3507,
                -71.0797,
            ),
            max_iterations=4,
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
            "weather_source"
        ]
        == "storm-test"
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

    assert (
        result[
            "weather_adjusted"
        ]
        is True
    )

    assert (
        result[
            "weather_original_venue_count"
        ]
        == 3
    )

    assert (
        result[
            "weather_filtered_venue_count"
        ]
        == 2
    )

    assert (
        result[
            "weather_removed_venue_names"
        ]
        == [
            "Boston Public Garden",
        ]
    )

    remaining_names = {
        venue.name
        for venue
        in result[
            "venues"
        ]
    }

    assert (
        "Boston Public Garden"
        not in remaining_names
    )

    assert (
        "Back Bay Art Gallery"
        in remaining_names
    )

    assert (
        "Back Bay Chicken Kitchen"
        in remaining_names
    )

    # Most importantly: no final itinerary may reintroduce the
    # weather-unsafe outdoor venue.
    for plan in result.get(
        "plans",
        [],
    ):
        stop_names = {
            stop.name
            for stop
            in plan.stops
        }

        assert (
            "Boston Public Garden"
            not in stop_names
        )
