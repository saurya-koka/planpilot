from __future__ import annotations

from datetime import (
    date,
)

from backend.app.live_weather import (
    normalize_city,
    normalize_start_time,
    resolve_forecast_date,
    weather_code_label,
)


def test_normalize_city_removes_state_suffix() -> None:
    assert (
        normalize_city(
            "Boston, MA"
        )
        == "Boston"
    )


def test_normalize_city_preserves_plain_city() -> None:
    assert (
        normalize_city(
            "Boston"
        )
        == "Boston"
    )


def test_resolve_iso_date() -> None:
    result = (
        resolve_forecast_date(
            "2026-08-15",
            today=date(
                2026,
                8,
                13,
            ),
        )
    )

    assert (
        result
        == date(
            2026,
            8,
            15,
        )
    )


def test_resolve_tomorrow() -> None:
    result = (
        resolve_forecast_date(
            "tomorrow",
            today=date(
                2026,
                8,
                13,
            ),
        )
    )

    assert (
        result
        == date(
            2026,
            8,
            14,
        )
    )


def test_resolve_weekday() -> None:
    result = (
        resolve_forecast_date(
            "Friday",
            today=date(
                2026,
                8,
                13,
            ),
        )
    )

    assert (
        result
        == date(
            2026,
            8,
            14,
        )
    )


def test_normalize_start_time() -> None:
    assert (
        normalize_start_time(
            "19:30"
        )
        == "19:30"
    )


def test_invalid_start_time_defaults_to_evening() -> None:
    assert (
        normalize_start_time(
            "dinner"
        )
        == "18:00"
    )


def test_weather_code_label() -> None:
    assert (
        weather_code_label(
            95
        )
        == "thunderstorm"
    )
