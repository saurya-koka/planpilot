from __future__ import annotations

from backend.app.models import (
    Itinerary,
    PlanRequest,
    ValidationFailure,
    ValidationResult,
)


def validate_budget(
    *,
    request: PlanRequest,
    itinerary: Itinerary,
) -> list[ValidationFailure]:
    """
    Validate the itinerary against the user's total budget.
    """
    if (
        itinerary.total_cost
        <= request.budget_total
    ):
        return []

    overage = (
        itinerary.total_cost
        - request.budget_total
    )

    return [
        ValidationFailure(
            code="budget_exceeded",
            severity="error",
            message=(
                "The itinerary exceeds the "
                "requested total budget."
            ),
            details={
                "budget_total": (
                    request.budget_total
                ),
                "actual_total": (
                    itinerary.total_cost
                ),
                "overage": round(
                    overage,
                    2,
                ),
            },
        )
    ]


def validate_route_legs(
    *,
    request: PlanRequest,
    itinerary: Itinerary,
) -> list[ValidationFailure]:
    """
    Validate travel legs against the maximum allowed duration.
    """
    failures: list[
        ValidationFailure
    ] = []

    for (
        leg_index,
        leg,
    ) in enumerate(
        itinerary.route_legs,
        start=1,
    ):
        if (
            leg.duration_minutes
            <= request.max_leg_minutes
        ):
            continue

        failures.append(
            ValidationFailure(
                code=(
                    "travel_leg_too_long"
                ),
                severity="error",
                message=(
                    f"Travel from "
                    f"{leg.from_name} to "
                    f"{leg.to_name} exceeds "
                    "the requested travel limit."
                ),
                details={
                    "leg_index": (
                        leg_index
                    ),
                    "from_name": (
                        leg.from_name
                    ),
                    "to_name": (
                        leg.to_name
                    ),
                    "actual_minutes": (
                        leg.duration_minutes
                    ),
                    "max_minutes": (
                        request.max_leg_minutes
                    ),
                    "distance_meters": (
                        leg.distance_meters
                    ),
                    "mode": (
                        leg.mode
                    ),
                },
            )
        )

    return failures


def validate_route_sources(
    *,
    itinerary: Itinerary,
) -> list[ValidationFailure]:
    """
    Report live-route attempts that had to fall back to an
    estimate.

    The legacy area_matrix provider is intentionally ignored here.
    It represents sample/offline planning rather than a failed live
    routing request.
    """
    failures: list[
        ValidationFailure
    ] = []

    for (
        leg_index,
        leg,
    ) in enumerate(
        itinerary.route_legs,
        start=1,
    ):
        if not (
            leg.fallback_used
        ):
            continue

        if (
            leg.provider
            == "area_matrix"
        ):
            continue

        failures.append(
            ValidationFailure(
                code=(
                    "route_fallback_used"
                ),
                severity="warning",
                message=(
                    f"Travel from "
                    f"{leg.from_name} to "
                    f"{leg.to_name} used "
                    "an estimated route."
                ),
                details={
                    "leg_index": (
                        leg_index
                    ),
                    "from_name": (
                        leg.from_name
                    ),
                    "to_name": (
                        leg.to_name
                    ),
                    "provider": (
                        leg.provider
                    ),
                    "duration_minutes": (
                        leg.duration_minutes
                    ),
                    "distance_meters": (
                        leg.distance_meters
                    ),
                    "mode": (
                        leg.mode
                    ),
                },
            )
        )

    return failures


def validate_opening_hours(
    *,
    itinerary: Itinerary,
) -> list[ValidationFailure]:
    """
    Report live venues whose opening hours could not be verified.

    Missing hours are warnings rather than errors because missing
    data does not prove that the venue is closed.
    """
    failures: list[
        ValidationFailure
    ] = []

    for (
        stop_index,
        stop,
    ) in enumerate(
        itinerary.stops,
        start=1,
    ):
        if (
            stop.source
            != "geoapify"
        ):
            continue

        if (
            stop.opening_hours
            is not None
            and stop.opening_hours.strip()
        ):
            continue

        failures.append(
            ValidationFailure(
                code=(
                    "opening_hours_unknown"
                ),
                severity="warning",
                message=(
                    f"Opening hours could "
                    f"not be verified for "
                    f"{stop.name}."
                ),
                details={
                    "stop_index": (
                        stop_index
                    ),
                    "venue_name": (
                        stop.name
                    ),
                    "area": (
                        stop.area
                    ),
                    "source": (
                        stop.source
                    ),
                },
            )
        )

    return failures


def build_closed_venue_failures(
    *,
    closed_venues: list[str],
) -> list[ValidationFailure]:
    """
    Convert confirmed closed venues into structured errors.
    """
    failures: list[
        ValidationFailure
    ] = []

    for venue_name in (
        closed_venues
    ):
        failures.append(
            ValidationFailure(
                code="venue_closed",
                severity="error",
                message=(
                    f"{venue_name} is closed "
                    "during the planned visit."
                ),
                details={
                    "venue_name": (
                        venue_name
                    ),
                },
            )
        )

    return failures


def validation_has_errors(
    failures: list[
        ValidationFailure
    ],
) -> bool:
    """
    Return True when at least one validation error exists.
    """
    return any(
        failure.severity
        == "error"
        for failure in failures
    )


def validate_itinerary(
    *,
    request: PlanRequest,
    itinerary: Itinerary,
    closed_venues: (
        list[str]
        | None
    ) = None,
) -> ValidationResult:
    """
    Run all deterministic PlanPilot validation rules.

    This result is intentionally machine-readable so V2.4's
    repair agent can inspect failure codes rather than attempting
    to understand human-written warning strings.
    """
    failures: list[
        ValidationFailure
    ] = []

    failures.extend(
        validate_budget(
            request=request,
            itinerary=itinerary,
        )
    )

    failures.extend(
        validate_route_legs(
            request=request,
            itinerary=itinerary,
        )
    )

    failures.extend(
        validate_route_sources(
            itinerary=itinerary,
        )
    )

    failures.extend(
        validate_opening_hours(
            itinerary=itinerary,
        )
    )

    if closed_venues:
        failures.extend(
            build_closed_venue_failures(
                closed_venues=(
                    closed_venues
                ),
            )
        )

    return ValidationResult(
        is_valid=not (
            validation_has_errors(
                failures
            )
        ),
        failures=failures,
    )


def failures_to_warning_messages(
    failures: list[
        ValidationFailure
    ],
) -> list[str]:
    """
    Convert structured failures back into strings for the existing
    frontend.

    V2.3 therefore exposes machine-readable failures without
    breaking the current warnings UI.
    """
    return [
        failure.message
        for failure in failures
    ]
