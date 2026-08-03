from datetime import time

from backend.app.tools.opening_hours import (
    parse_clock_time,
    venue_open_status,
)


def test_parses_24_hour_time() -> None:
    assert parse_clock_time("17:30") == time(17, 30)


def test_parses_12_hour_time() -> None:
    assert parse_clock_time("5:30 PM") == time(17, 30)


def test_venue_is_open_during_interval() -> None:
    result = venue_open_status(
        "Mo-Fr 11:00-22:00; Sa-Su 12:00-23:00",
        "Friday",
        time(18, 0),
    )

    assert result is True


def test_venue_is_closed_after_interval() -> None:
    result = venue_open_status(
        "Mo-Fr 07:00-15:00",
        "Friday",
        time(17, 0),
    )

    assert result is False


def test_venue_closed_on_off_day() -> None:
    result = venue_open_status(
        "Mo-Th 11:00-22:00; Fr-Sa 11:00-23:00; Su off",
        "Sunday",
        time(18, 0),
    )

    assert result is False


def test_missing_hours_are_unknown() -> None:
    result = venue_open_status(
        None,
        "Friday",
        time(18, 0),
    )

    assert result is None
