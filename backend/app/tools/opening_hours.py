from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta


DAY_ALIASES = {
    "mo": "monday",
    "tu": "tuesday",
    "we": "wednesday",
    "th": "thursday",
    "fr": "friday",
    "sa": "saturday",
    "su": "sunday",
}


DAY_ORDER = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


def parse_clock_time(
    value: str,
) -> time | None:
    """
    Convert values such as:

    17:00
    5 PM
    5:30pm
    """
    cleaned = value.strip().lower()

    twelve_hour = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        cleaned,
    )

    if twelve_hour:
        hour = int(
            twelve_hour.group(1)
        )
        minute = int(
            twelve_hour.group(2) or 0
        )
        period = twelve_hour.group(3)

        if (
            hour < 1
            or hour > 12
            or minute > 59
        ):
            return None

        if period == "am":
            hour = (
                0
                if hour == 12
                else hour
            )
        else:
            hour = (
                12
                if hour == 12
                else hour + 12
            )

        return time(
            hour,
            minute,
        )

    twenty_four_hour = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?",
        cleaned,
    )

    if twenty_four_hour:
        hour = int(
            twenty_four_hour.group(1)
        )
        minute = int(
            twenty_four_hour.group(2) or 0
        )

        if (
            hour > 23
            or minute > 59
        ):
            return None

        return time(
            hour,
            minute,
        )

    return None


def normalize_day(
    value: str,
) -> str | None:
    cleaned = value.strip().lower()

    if cleaned in DAY_ORDER:
        return cleaned

    if len(cleaned) < 2:
        return None

    return DAY_ALIASES.get(
        cleaned[:2]
    )


def expand_day_range(
    start_day: str,
    end_day: str,
) -> list[str]:
    start = normalize_day(
        start_day
    )
    end = normalize_day(
        end_day
    )

    if (
        start is None
        or end is None
    ):
        return []

    start_index = DAY_ORDER.index(
        start
    )
    end_index = DAY_ORDER.index(
        end
    )

    if start_index <= end_index:
        return DAY_ORDER[
            start_index : end_index + 1
        ]

    return (
        DAY_ORDER[start_index:]
        + DAY_ORDER[: end_index + 1]
    )


def parse_day_expression(
    expression: str,
) -> list[str]:
    """
    Parse day expressions such as:

    Mo
    Mo-Fr
    Sa,Su
    Sa[1]
    Mo-Fr,Su
    """
    cleaned = expression.strip()

    # Remove calendar modifiers such as Sa[1].
    cleaned = re.sub(
        r"\[[^\]]+\]",
        "",
        cleaned,
    )

    days: list[str] = []

    for part in cleaned.split(","):
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            start, end = part.split(
                "-",
                1,
            )

            days.extend(
                expand_day_range(
                    start,
                    end,
                )
            )

            continue

        normalized = normalize_day(
            part
        )

        if normalized:
            days.append(
                normalized
            )

    return list(
        dict.fromkeys(days)
    )


def is_time_in_interval(
    current: time,
    opening: time,
    closing: time,
) -> bool:
    """
    Support ordinary and overnight intervals.

    Examples:
        09:00-18:00
        18:00-02:00
    """
    if closing > opening:
        return (
            opening
            <= current
            < closing
        )

    return (
        current >= opening
        or current < closing
    )


def _normalize_opening_hours(
    opening_hours: str,
) -> str:
    """
    Normalize common Geoapify / OpenStreetMap separators.
    """
    normalized = opening_hours.replace(
        "|",
        ";",
    )

    normalized = re.sub(
        r"\s*;\s*",
        ";",
        normalized,
    )

    return normalized.strip()


def venue_open_status(
    opening_hours: str | None,
    weekday: str,
    arrival_time: time,
) -> bool | None:
    """
    Return:

    True:
        Venue appears open at the requested time.

    False:
        Venue appears closed at the requested time.

    None:
        Hours are missing or could not be interpreted.
    """
    if not opening_hours:
        return None

    target_day = normalize_day(
        weekday
    )

    if target_day is None:
        return None

    normalized_hours = (
        _normalize_opening_hours(
            opening_hours
        )
    )

    rules = [
        rule.strip()
        for rule
        in normalized_hours.split(";")
        if rule.strip()
    ]

    matched_day = False
    parsed_any_rule = False

    for rule in rules:
        lowered_rule = (
            rule.lower().strip()
        )

        # Closed-day rules, such as "Su off".
        off_match = re.fullmatch(
            r"(.+?)\s+off",
            lowered_rule,
        )

        if off_match:
            parsed_any_rule = True

            day_expression = (
                off_match.group(1)
            )

            days = parse_day_expression(
                day_expression
            )

            if target_day in days:
                return False

            continue

        # Daily hours with no weekday prefix, such as "10:00-17:00".
        daily_match = re.fullmatch(
            r"(\d{1,2}:\d{2})"
            r"-"
            r"(\d{1,2}:\d{2})",
            rule,
        )

        if daily_match:
            parsed_any_rule = True
            matched_day = True

            opening = parse_clock_time(
                daily_match.group(1)
            )

            closing = parse_clock_time(
                daily_match.group(2)
            )

            if (
                opening is None
                or closing is None
            ):
                return None

            if is_time_in_interval(
                arrival_time,
                opening,
                closing,
            ):
                return True

            continue

        # Weekday-specific hours such as:
        # Mo-Fr 09:00-17:00
        # Sa,Su 10:00-16:00
        # Sa[1] 10:00-16:00
        match = re.fullmatch(
            r"("
            r"[A-Za-z]{2}"
            r"(?:\[[^\]]+\])?"
            r"(?:-[A-Za-z]{2}"
            r"(?:\[[^\]]+\])?)?"
            r"(?:,[A-Za-z]{2}"
            r"(?:\[[^\]]+\])?"
            r"(?:-[A-Za-z]{2}"
            r"(?:\[[^\]]+\])?)?)*"
            r")\s+"
            r"(\d{1,2}:\d{2})"
            r"-"
            r"(\d{1,2}:\d{2})",
            rule,
        )

        if not match:
            continue

        parsed_any_rule = True

        day_expression = (
            match.group(1)
        )

        days = parse_day_expression(
            day_expression
        )

        if target_day not in days:
            continue

        matched_day = True

        opening = parse_clock_time(
            match.group(2)
        )

        closing = parse_clock_time(
            match.group(3)
        )

        if (
            opening is None
            or closing is None
        ):
            return None

        if is_time_in_interval(
            arrival_time,
            opening,
            closing,
        ):
            return True

    if matched_day:
        return False

    if parsed_any_rule:
        # The schedule was readable but no rule covered the target day.
        return False

    return None


def venue_open_for_interval(
    opening_hours: str | None,
    weekday: str,
    arrival_time: time,
    departure_time: time,
) -> bool | None:
    """
    Check whether a venue appears open for the full visit.

    Returns:

    True:
        Open from arrival through departure.

    False:
        Closed at arrival or closes before departure.

    None:
        Hours are missing or could not be interpreted.
    """
    arrival_status = venue_open_status(
        opening_hours=opening_hours,
        weekday=weekday,
        arrival_time=arrival_time,
    )

    if arrival_status is not True:
        return arrival_status

    # Closing times are exclusive, so check one minute before
    # the planned departure.
    departure_datetime = (
        datetime.combine(
            date.today(),
            departure_time,
        )
        - timedelta(minutes=1)
    )

    return venue_open_status(
        opening_hours=opening_hours,
        weekday=weekday,
        arrival_time=departure_datetime.time(),
    )
