from __future__ import annotations

from dataclasses import (
    dataclass,
)
from enum import (
    Enum,
)


class WeatherRiskLevel(
    str,
    Enum,
):
    """
    Overall weather suitability for an itinerary.
    """

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class WeatherSnapshot:
    """
    Normalized weather data consumed by PlanPilot.

    Values remain provider-independent so live weather services can be
    replaced without changing graph decision logic.
    """

    condition: str

    temperature_c: float

    precipitation_probability: float

    wind_speed_kph: float

    severe_weather: bool = False

    source: str = "deterministic"


@dataclass(frozen=True)
class WeatherAssessment:
    """
    Deterministic interpretation of one WeatherSnapshot.
    """

    risk_level: WeatherRiskLevel

    outdoor_safe: bool

    reasons: list[
        str
    ]


def clamp_probability(
    value: float,
) -> float:
    """
    Normalize a probability to the inclusive 0..1 range.
    """

    return max(
        0.0,
        min(
            1.0,
            float(
                value
            ),
        ),
    )


def assess_weather(
    snapshot: WeatherSnapshot,
) -> WeatherAssessment:
    """
    Convert normalized weather into deterministic itinerary risk.

    High risk:
    - severe weather
    - >= 70% precipitation
    - >= 50 kph wind
    - extreme heat >= 38 C
    - extreme cold <= -10 C

    Moderate risk:
    - >= 40% precipitation
    - >= 30 kph wind
    - heat >= 32 C
    - cold <= 0 C

    Anything else is considered low risk.
    """

    precipitation = (
        clamp_probability(
            snapshot
            .precipitation_probability
        )
    )

    reasons: list[
        str
    ] = []

    high_risk = False

    moderate_risk = False

    if snapshot.severe_weather:
        high_risk = True

        reasons.append(
            "severe weather is present"
        )

    if precipitation >= 0.70:
        high_risk = True

        reasons.append(
            (
                "precipitation probability "
                f"is {precipitation:.0%}"
            )
        )

    elif precipitation >= 0.40:
        moderate_risk = True

        reasons.append(
            (
                "precipitation probability "
                f"is {precipitation:.0%}"
            )
        )

    if snapshot.wind_speed_kph >= 50:
        high_risk = True

        reasons.append(
            (
                "wind speed is "
                f"{snapshot.wind_speed_kph:.0f} kph"
            )
        )

    elif snapshot.wind_speed_kph >= 30:
        moderate_risk = True

        reasons.append(
            (
                "wind speed is "
                f"{snapshot.wind_speed_kph:.0f} kph"
            )
        )

    if snapshot.temperature_c >= 38:
        high_risk = True

        reasons.append(
            (
                "temperature is extremely hot "
                f"at {snapshot.temperature_c:.1f} C"
            )
        )

    elif snapshot.temperature_c >= 32:
        moderate_risk = True

        reasons.append(
            (
                "temperature is hot "
                f"at {snapshot.temperature_c:.1f} C"
            )
        )

    if snapshot.temperature_c <= -10:
        high_risk = True

        reasons.append(
            (
                "temperature is extremely cold "
                f"at {snapshot.temperature_c:.1f} C"
            )
        )

    elif snapshot.temperature_c <= 0:
        moderate_risk = True

        reasons.append(
            (
                "temperature is cold "
                f"at {snapshot.temperature_c:.1f} C"
            )
        )

    if high_risk:
        return WeatherAssessment(
            risk_level=(
                WeatherRiskLevel.HIGH
            ),
            outdoor_safe=False,
            reasons=reasons,
        )

    if moderate_risk:
        return WeatherAssessment(
            risk_level=(
                WeatherRiskLevel.MODERATE
            ),
            outdoor_safe=True,
            reasons=reasons,
        )

    if not reasons:
        reasons.append(
            "weather conditions are suitable"
        )

    return WeatherAssessment(
        risk_level=(
            WeatherRiskLevel.LOW
        ),
        outdoor_safe=True,
        reasons=reasons,
    )


class DeterministicWeatherProvider:
    """
    Offline provider used by tests and development.

    A caller can inject a WeatherSnapshot to simulate any weather
    condition without an external API.
    """

    def __init__(
        self,
        snapshot: (
            WeatherSnapshot
            | None
        ) = None,
    ) -> None:
        self.snapshot = (
            snapshot
            or WeatherSnapshot(
                condition="clear",
                temperature_c=20.0,
                precipitation_probability=0.0,
                wind_speed_kph=5.0,
                severe_weather=False,
                source="deterministic",
            )
        )

    def get_weather(
        self,
        *,
        city: str,
        date: str,
        start_time: str = "18:00",
    ) -> WeatherSnapshot:
        """
        Return the configured deterministic weather snapshot.

        The arguments mirror the live-provider interface.
        """

        _ = (
            city,
            date,
            start_time,
        )

        return self.snapshot
