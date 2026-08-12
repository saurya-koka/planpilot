from backend.app.models import (
    PlanRequest,
    Venue,
)
from backend.app.planner import (
    build_plans,
)


def make_request(
    *,
    budget_total: float = 200,
    max_leg_minutes: int = 180,
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
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=max_leg_minutes,
    )


def test_planner_attaches_budget_failure() -> None:
    """
    A plan that exceeds the user's budget should still carry
    machine-readable information explaining why it failed.
    """
    request = make_request(
        budget_total=50,
    )

    venue = Venue(
        name="Expensive Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=50,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="sample",
    )

    plans = build_plans(
        request=request,
        venues=[venue],
    )

    assert plans

    plan = plans[0]

    codes = {
        failure.code
        for failure
        in plan.validation_failures
    }

    assert (
        "budget_exceeded"
        in codes
    )

    budget_failure = next(
        failure
        for failure
        in plan.validation_failures
        if (
            failure.code
            == "budget_exceeded"
        )
    )

    assert (
        budget_failure.severity
        == "error"
    )

    assert (
        budget_failure.details[
            "budget_total"
        ]
        == 50
    )

    assert (
        budget_failure.details[
            "actual_total"
        ]
        == 100
    )


def test_planner_attaches_closed_venue_failure() -> None:
    """
    Closed venues should no longer disappear without explanation.

    They should produce a structured venue_closed error that the
    future repair agent can inspect.
    """
    request = make_request()

    venue = Venue(
        name="Lunch Only Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours=(
            "Mo-Fr 07:00-15:00"
        ),
        source="sample",
    )

    plans = build_plans(
        request=request,
        venues=[venue],
    )

    assert plans

    plan = plans[0]

    codes = {
        failure.code
        for failure
        in plan.validation_failures
    }

    assert (
        "venue_closed"
        in codes
    )

    failure = next(
        failure
        for failure
        in plan.validation_failures
        if (
            failure.code
            == "venue_closed"
        )
    )

    assert (
        failure.severity
        == "error"
    )

    assert (
        failure.details[
            "venue_name"
        ]
        == "Lunch Only Restaurant"
    )


def test_planner_attaches_unknown_hours_warning() -> None:
    """
    Missing live opening-hours data should produce a warning
    without making the itinerary invalid.
    """
    request = make_request()

    venue = Venue(
        name="Live Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours=None,
        source="geoapify",
    )

    plans = build_plans(
        request=request,
        venues=[venue],
    )

    assert plans

    plan = plans[0]

    failures = [
        failure
        for failure
        in plan.validation_failures
        if (
            failure.code
            == "opening_hours_unknown"
        )
    ]

    assert len(
        failures
    ) == 1

    assert (
        failures[0].severity
        == "warning"
    )

    error_failures = [
        failure
        for failure
        in plan.validation_failures
        if (
            failure.severity
            == "error"
        )
    ]

    assert (
        error_failures
        == []
    )


def test_validation_failures_are_serializable() -> None:
    """
    FastAPI uses model_dump() when serializing plans.

    This verifies structured validation data is therefore available
    to the API response without needing a custom serializer.
    """
    request = make_request(
        budget_total=50,
    )

    venue = Venue(
        name="Expensive Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=50,
        duration_minutes=60,
        vibe=["chill"],
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="sample",
    )

    plans = build_plans(
        request=request,
        venues=[venue],
    )

    assert plans

    serialized = (
        plans[0].model_dump()
    )

    assert (
        "validation_failures"
        in serialized
    )

    assert (
        serialized[
            "validation_failures"
        ]
    )

    first_failure = (
        serialized[
            "validation_failures"
        ][0]
    )

    assert (
        "code"
        in first_failure
    )

    assert (
        "severity"
        in first_failure
    )

    assert (
        "message"
        in first_failure
    )

    assert (
        "details"
        in first_failure
    )
