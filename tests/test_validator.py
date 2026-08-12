from backend.app.models import (
    Itinerary,
    PlanRequest,
    RouteLeg,
    Stop,
)
from backend.app.validator import (
    build_closed_venue_failures,
    validate_budget,
    validate_itinerary,
    validate_opening_hours,
    validate_route_legs,
    validate_route_sources,
)


def make_request(
    *,
    budget_total: float = 150,
    max_leg_minutes: int = 30,
) -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=budget_total,
        party_size=2,
        transport="walking",
        vibe=["chill"],
        must_include=[
            "activity",
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=max_leg_minutes,
    )


def make_itinerary(
    *,
    total_cost: float = 100,
    leg_minutes: int = 20,
    fallback_used: bool = False,
    opening_hours: str | None = "Mo-Su 09:00-22:00",
    source: str = "geoapify",
) -> Itinerary:
    stop = Stop(
        name="Test Venue",
        category="activity",
        area="Back Bay",
        estimated_cost=50,
        duration_minutes=60,
        latitude=42.35,
        longitude=-71.08,
        opening_hours=opening_hours,
        source=source,
    )

    leg = RouteLeg(
        from_name="Back Bay",
        to_name="Test Venue",
        duration_minutes=leg_minutes,
        distance_meters=1200,
        mode="walking",
        geometry=[],
        provider=(
            "estimate"
            if fallback_used
            else "geoapify"
        ),
        fallback_used=fallback_used,
    )

    return Itinerary(
        label="Candidate",
        title="Test Venue",
        stops=[stop],
        total_cost=total_cost,
        total_duration_minutes=(
            60 + leg_minutes
        ),
        estimated_travel_minutes=leg_minutes,
        score=100,
        route_legs=[leg],
        validation_failures=[],
        reasons=[],
        warnings=[],
    )


def test_budget_validation_passes_when_within_budget() -> None:
    request = make_request(
        budget_total=150
    )

    itinerary = make_itinerary(
        total_cost=120
    )

    failures = validate_budget(
        request=request,
        itinerary=itinerary,
    )

    assert failures == []


def test_budget_validation_returns_structured_failure() -> None:
    request = make_request(
        budget_total=150
    )

    itinerary = make_itinerary(
        total_cost=175
    )

    failures = validate_budget(
        request=request,
        itinerary=itinerary,
    )

    assert len(failures) == 1

    failure = failures[0]

    assert failure.code == "budget_exceeded"
    assert failure.severity == "error"
    assert failure.details["budget_total"] == 150
    assert failure.details["actual_total"] == 175
    assert failure.details["overage"] == 25


def test_route_leg_validation_detects_long_leg() -> None:
    request = make_request(
        max_leg_minutes=30
    )

    itinerary = make_itinerary(
        leg_minutes=42
    )

    failures = validate_route_legs(
        request=request,
        itinerary=itinerary,
    )

    assert len(failures) == 1

    failure = failures[0]

    assert (
        failure.code
        == "travel_leg_too_long"
    )

    assert failure.severity == "error"

    assert (
        failure.details[
            "actual_minutes"
        ]
        == 42
    )

    assert (
        failure.details[
            "max_minutes"
        ]
        == 30
    )


def test_route_source_validation_detects_fallback() -> None:
    itinerary = make_itinerary(
        fallback_used=True
    )

    failures = validate_route_sources(
        itinerary=itinerary
    )

    assert len(failures) == 1

    failure = failures[0]

    assert (
        failure.code
        == "route_fallback_used"
    )

    assert (
        failure.severity
        == "warning"
    )

    assert (
        failure.details[
            "provider"
        ]
        == "estimate"
    )


def test_opening_hours_validation_detects_unknown_hours() -> None:
    itinerary = make_itinerary(
        opening_hours=None,
        source="geoapify",
    )

    failures = validate_opening_hours(
        itinerary=itinerary
    )

    assert len(failures) == 1

    failure = failures[0]

    assert (
        failure.code
        == "opening_hours_unknown"
    )

    assert (
        failure.severity
        == "warning"
    )

    assert (
        failure.details[
            "venue_name"
        ]
        == "Test Venue"
    )


def test_opening_hours_validation_ignores_sample_venue() -> None:
    itinerary = make_itinerary(
        opening_hours=None,
        source="sample",
    )

    failures = validate_opening_hours(
        itinerary=itinerary
    )

    assert failures == []


def test_closed_venue_failure_is_error() -> None:
    failures = build_closed_venue_failures(
        closed_venues=[
            "Closed Restaurant"
        ]
    )

    assert len(failures) == 1

    failure = failures[0]

    assert (
        failure.code
        == "venue_closed"
    )

    assert (
        failure.severity
        == "error"
    )

    assert (
        failure.details[
            "venue_name"
        ]
        == "Closed Restaurant"
    )


def test_validate_itinerary_is_valid_without_errors() -> None:
    request = make_request()

    itinerary = make_itinerary(
        total_cost=100,
        leg_minutes=20,
        fallback_used=False,
        opening_hours=(
            "Mo-Su 09:00-22:00"
        ),
    )

    result = validate_itinerary(
        request=request,
        itinerary=itinerary,
    )

    assert result.is_valid is True
    assert result.failures == []


def test_validate_itinerary_allows_warnings_without_invalidating() -> None:
    request = make_request()

    itinerary = make_itinerary(
        fallback_used=True,
        opening_hours=None,
    )

    result = validate_itinerary(
        request=request,
        itinerary=itinerary,
    )

    assert result.is_valid is True

    codes = {
        failure.code
        for failure
        in result.failures
    }

    assert (
        "route_fallback_used"
        in codes
    )

    assert (
        "opening_hours_unknown"
        in codes
    )


def test_validate_itinerary_becomes_invalid_with_error() -> None:
    request = make_request(
        budget_total=100,
        max_leg_minutes=20,
    )

    itinerary = make_itinerary(
        total_cost=150,
        leg_minutes=35,
    )

    result = validate_itinerary(
        request=request,
        itinerary=itinerary,
    )

    assert result.is_valid is False

    codes = {
        failure.code
        for failure
        in result.failures
    }

    assert (
        "budget_exceeded"
        in codes
    )

    assert (
        "travel_leg_too_long"
        in codes
    )
