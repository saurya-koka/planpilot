from __future__ import annotations

import os
from typing import Protocol

from .graph_state import (
    PlanPilotGraphState,
)
from .live_weather import (
    OpenMeteoWeatherProvider,
)
from .weather import (
    DeterministicWeatherProvider,
    WeatherSnapshot,
    assess_weather,
)
from .weather_policy import (
    filter_venues_for_weather,
)


class WeatherProvider(
    Protocol,
):
    """
    Provider contract used by the LangGraph weather node.
    """

    def get_weather(
        self,
        *,
        city: str,
        date: str,
        start_time: str = "18:00",
    ) -> WeatherSnapshot:
        ...


def live_weather_is_enabled() -> bool:
    """
    Return True when PlanPilot should use live forecast data.
    """

    value = (
        os.getenv(
            "PLANPILOT_LIVE_WEATHER",
            "",
        )
        .strip()
        .lower()
    )

    return value in {
        "1",
        "true",
        "yes",
        "on",
    }


def build_graph_weather_provider() -> WeatherProvider:
    """
    Build the graph weather provider.

    Tests and ordinary offline development remain deterministic.

    Live Open-Meteo forecasts are enabled explicitly through:
        PLANPILOT_LIVE_WEATHER=1
    """

    if live_weather_is_enabled():
        return (
            OpenMeteoWeatherProvider()
        )

    return (
        DeterministicWeatherProvider()
    )


def retrieve_weather_context_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Retrieve and assess weather for the current planning request.

    Venue adaptation is handled separately by
    apply_weather_constraints_node().
    """

    request = state.get(
        "request"
    )

    if request is None:
        return {
            "weather_checked": False,
            "weather_condition": "",
            "weather_temperature_c": 0.0,
            "weather_precipitation_probability": 0.0,
            "weather_wind_speed_kph": 0.0,
            "weather_risk_level": "",
            "weather_outdoor_safe": True,
            "weather_reasons": [],
            "weather_source": "",
            "last_action": (
                "Weather check skipped because "
                "no planning request exists."
            ),
        }

    try:
        provider = (
            build_graph_weather_provider()
        )

        snapshot = (
            provider.get_weather(
                city=request.city,
                date=request.date,
                start_time=(
                    request.start_time
                ),
            )
        )

        assessment = (
            assess_weather(
                snapshot
            )
        )

    except Exception as exc:
        return {
            "weather_checked": False,
            "weather_condition": "",
            "weather_temperature_c": 0.0,
            "weather_precipitation_probability": 0.0,
            "weather_wind_speed_kph": 0.0,
            "weather_risk_level": "",
            "weather_outdoor_safe": True,
            "weather_reasons": [
                (
                    "weather provider "
                    f"failed: {exc}"
                )
            ],
            "weather_source": "",
            "last_action": (
                "Weather lookup was unavailable; "
                "planning will continue without "
                "weather constraints."
            ),
        }

    return {
        "weather_checked": True,
        "weather_condition": (
            snapshot.condition
        ),
        "weather_temperature_c": (
            snapshot.temperature_c
        ),
        "weather_precipitation_probability": (
            snapshot
            .precipitation_probability
        ),
        "weather_wind_speed_kph": (
            snapshot.wind_speed_kph
        ),
        "weather_risk_level": (
            assessment
            .risk_level
            .value
        ),
        "weather_outdoor_safe": (
            assessment.outdoor_safe
        ),
        "weather_reasons": list(
            assessment.reasons
        ),
        "weather_source": (
            snapshot.source
        ),
        "last_action": (
            "Weather assessed as "
            f"{assessment.risk_level.value} risk "
            f"using {snapshot.source}."
        ),
    }


def apply_weather_constraints_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Adapt the venue candidate pool to assessed weather.

    High-risk weather removes clearly outdoor activity venues before
    RAG retrieval and plan generation.

    Low/moderate weather preserves the original venue pool.
    """

    venues = list(
        state.get(
            "venues",
            [],
        )
    )

    weather_checked = (
        state.get(
            "weather_checked",
            False,
        )
    )

    outdoor_safe = (
        state.get(
            "weather_outdoor_safe",
            True,
        )
    )

    if not weather_checked:
        return {
            "weather_adjusted": False,
            "weather_original_venue_count": len(
                venues
            ),
            "weather_filtered_venue_count": len(
                venues
            ),
            "weather_removed_venue_names": [],
            "last_action": (
                "Weather constraints skipped because "
                "weather was not available."
            ),
        }

    result = (
        filter_venues_for_weather(
            venues=venues,
            outdoor_safe=(
                outdoor_safe
            ),
        )
    )

    if result.adjusted:
        action = (
            "Weather constraints removed "
            f"{len(result.removed_venue_names)} "
            "outdoor venue candidate(s)."
        )

    else:
        action = (
            "Weather constraints did not require "
            "venue-pool changes."
        )

    return {
        "venues": list(
            result.venues
        ),
        "weather_adjusted": (
            result.adjusted
        ),
        "weather_original_venue_count": (
            result.original_count
        ),
        "weather_filtered_venue_count": (
            result.filtered_count
        ),
        "weather_removed_venue_names": list(
            result.removed_venue_names
        ),
        "last_action": action,
    }
