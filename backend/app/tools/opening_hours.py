from __future__ import annotations

import re
from datetime import time


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


def parse_clock_time(value: str) -> time | None:
    """
    Convert values such as 17:00, 5 PM, or 5:30pm into time.
    """
    cleaned = value.strip().lower()

    twelve_hour = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)",
        cleaned,
    )

    if twelve_hour:
        hour = int(twelve_hour.group(1))
        minute = int(twelve_hour.group(2) or 0)
        period = twelve_hour.group(3)

        if hour < 1 or hour > 12 or minute > 59:
            return None

        if period == "am":
            hour = 0 if hour == 12 else hour
        else:
            hour = 12 if hour == 12 else hour + 12

        return time(hour, minute)

    twenty_four_hour = re.fullmatch(
        r"(\d{1,2})(?::(\d{2}))?",
        cleaned,
    )

    if twenty_four_hour:
        hour = int(twenty_four_hour.group(1))
        minute = int(twenty_four_hour.group(2) or 0)

        if hour > 23 or minute > 59:
            return None

        return time(hour, minute)

    return None


def normalize_day(value: str) -> str | None:
    cleaned = value.strip().lower()

    if cleaned in DAY_ORDER:
        return cleaned

    return DAY_ALIASES.get(cleaned[:2])


def expand_day_range(
    start_day: str,
    end_day: str,
) -> list[str]:
    start = normalize_day(start_day)
    end = normalize_day(end_day)

    if start is None or end is None:
        return []

    start_index = DAY_ORDER.index(start)
    end_index = DAY_ORDER.index(end)

    if start_index <= end_index:
        return DAY_ORDER[start_index : end_index + 1]

    return (
        DAY_ORDER[start_index:]
        + DAY_ORDER[: end_index + 1]
    )


def parse_day_expression(
    expression: str,
) -> list[str]:
    cleaned = expression.strip()

    if "-" in cleaned:
        start, end = cleaned.split("-", 1)
        return expand_day_range(start, end)

    normalized = normalize_day(cleaned)

    return [normalized] if normalized else []


def is_time_in_interval(
    current: time,
    opening: time,
    closing: time,
) -> bool:
    """
    Support both ordinary and overnight intervals.
    """
    if closing > opening:
        return opening <= current < closing

    return current >= opening or current < closing


def venue_open_status(
    opening_hours: str | None,
    weekday: str,
    arrival_time: time,
) -> bool | None:
    """
    Return:

    True  -> venue appears open
    False -> venue appears closed
    None  -> hours are missing or could not be interpreted
    """
    if not opening_hours:
        return None

    target_day = normalize_day(weekday)

    if target_day is None:
        return None

    rules = [
        rule.strip()
        for rule in opening_hours.split(";")
        if rule.strip()
    ]

    matched_day = False

    for rule in rules:
        if rule.lower().endswith(" off"):
            day_expression = rule[:-4].strip()
            days = parse_day_expression(day_expression)

            if target_day in days:
                return False

            continue

        match = re.fullmatch(
            r"([A-Za-z]{2}(?:-[A-Za-z]{2})?)\s+"
            r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})",
            rule,
        )

        if not match:
            continue

        day_expression = match.group(1)
        days = parse_day_expression(day_expression)

        if target_day not in days:
            continue

        matched_day = True

        opening = parse_clock_time(match.group(2))
        closing = parse_clock_time(match.group(3))

        if opening is None or closing is None:
            return None

        if is_time_in_interval(
            arrival_time,
            opening,
            closing,
        ):
            return True

    if matched_day:
        return False

    return None
