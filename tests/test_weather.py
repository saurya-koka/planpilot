from __future__ import annotations

from backend.app.weather import (
    DeterministicWeatherProvider,
    WeatherRiskLevel,
    WeatherSnapshot,
    assess_weather,
    clamp_probability,
)


def test_clamp_probability() -> None:
    assert (
        clamp_probability(
            -0.5
        )
        == 0.0
    )

    assert (
        clamp_probability(
            0.6
        )
        == 0.6
    )

    assert (
        clamp_probability(
            1.5
        )
        == 1.0
    )


def test_clear_weather_is_low_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="clear",
        temperature_c=22,
        precipitation_probability=0.10,
        wind_speed_kph=8,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.LOW
    )

    assert (
        result.outdoor_safe
        is True
    )


def test_heavy_rain_is_high_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="rain",
        temperature_c=18,
        precipitation_probability=0.85,
        wind_speed_kph=15,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.HIGH
    )

    assert (
        result.outdoor_safe
        is False
    )

    assert any(
        "precipitation"
        in reason
        for reason
        in result.reasons
    )


def test_moderate_rain_is_moderate_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="showers",
        temperature_c=18,
        precipitation_probability=0.50,
        wind_speed_kph=15,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.MODERATE
    )

    assert (
        result.outdoor_safe
        is True
    )


def test_severe_weather_is_high_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="thunderstorm",
        temperature_c=24,
        precipitation_probability=0.30,
        wind_speed_kph=20,
        severe_weather=True,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.HIGH
    )

    assert (
        result.outdoor_safe
        is False
    )


def test_high_wind_is_high_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="windy",
        temperature_c=20,
        precipitation_probability=0.10,
        wind_speed_kph=60,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.HIGH
    )

    assert (
        result.outdoor_safe
        is False
    )


def test_extreme_heat_is_high_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="hot",
        temperature_c=39,
        precipitation_probability=0.0,
        wind_speed_kph=5,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.HIGH
    )


def test_extreme_cold_is_high_risk() -> None:
    snapshot = WeatherSnapshot(
        condition="cold",
        temperature_c=-12,
        precipitation_probability=0.0,
        wind_speed_kph=5,
    )

    result = assess_weather(
        snapshot
    )

    assert (
        result.risk_level
        == WeatherRiskLevel.HIGH
    )


def test_deterministic_provider_returns_snapshot() -> None:
    expected = WeatherSnapshot(
        condition="rain",
        temperature_c=15,
        precipitation_probability=0.9,
        wind_speed_kph=20,
        source="test",
    )

    provider = (
        DeterministicWeatherProvider(
            snapshot=expected
        )
    )

    result = provider.get_weather(
        city="Boston",
        date="Friday",
    )

    assert (
        result
        == expected
    )
