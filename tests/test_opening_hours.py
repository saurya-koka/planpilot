from datetime import time

from datetime import time

from backend.app.tools.opening_hours import (
    parse_clock_time,
    venue_open_for_interval,
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


def test_venue_closing_during_visit_is_rejected() -> None:
    result = venue_open_for_interval(
        opening_hours="Mo-Fr 09:00-18:00",
        weekday="Friday",
        arrival_time=time(17, 20),
        departure_time=time(18, 50),
    )

    assert result is False

def test_parses_comma_separated_days() -> None:
    result = venue_open_status(
        opening_hours=(
            "Mo-Fr 09:00-17:00; "
            "Sa,Su 10:00-16:00"
        ),
        weekday="Sunday",
        arrival_time=time(12, 0),
    )

    assert result is True


def test_ignores_day_modifier() -> None:
    result = venue_open_status(
        opening_hours=(
            "We-Su 09:00-16:00 | "
            "Sa[1] 10:00-16:00"
        ),
        weekday="Saturday",
        arrival_time=time(11, 0),
    )

    assert result is True


def test_pipe_separated_hours_are_parsed() -> None:
    result = venue_open_status(
        opening_hours=(
            "We-Su 09:00-16:00 | "
            "Sa[1] 10:00-16:00"
        ),
        weekday="Friday",
        arrival_time=time(17, 20),
    )

    assert result is False


def test_complex_hours_reject_full_visit_after_close() -> None:
    result = venue_open_for_interval(
        opening_hours=(
            "We-Su 09:00-16:00 | "
            "Sa[1] 10:00-16:00"
        ),
        weekday="Friday",
        arrival_time=time(15, 0),
        departure_time=time(16, 30),
    )

    assert result is False


def test_daily_hours_apply_to_every_day() -> None:
    result = venue_open_status(
        opening_hours="10:00-17:00",
        weekday="Friday",
        arrival_time=time(14, 0),
    )

    assert result is True


def test_daily_hours_reject_after_closing() -> None:
    result = venue_open_status(
        opening_hours="10:00-17:00",
        weekday="Friday",
        arrival_time=time(17, 15),
    )

    assert result is False


def test_daily_hours_reject_visit_past_closing() -> None:
    result = venue_open_for_interval(
        opening_hours="10:00-17:00",
        weekday="Friday",
        arrival_time=time(16, 0),
        departure_time=time(17, 30),
    )

    assert result is False



def test_multiple_daily_intervals_open_in_second_range() -> None:
    result = venue_open_status(
        opening_hours=(
            "00:00-02:00, 11:00-00:00"
        ),
        weekday="Friday",
        arrival_time=time(19, 0),
    )

    assert result is True


def test_multiple_daily_intervals_closed_between_ranges() -> None:
    result = venue_open_status(
        opening_hours=(
            "09:00-12:00, 14:00-18:00"
        ),
        weekday="Friday",
        arrival_time=time(13, 0),
    )

    assert result is False


def test_multiple_daily_intervals_reject_visit_past_close() -> None:
    result = venue_open_for_interval(
        opening_hours=(
            "09:00-12:00, 14:00-18:00"
        ),
        weekday="Friday",
        arrival_time=time(17, 30),
        departure_time=time(18, 30),
    )

    assert result is False
