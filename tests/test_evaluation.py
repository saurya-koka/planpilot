from __future__ import annotations

from backend.app.evaluation import (
    clamp_score,
    evaluate_budget,
    evaluate_plan,
    evaluate_required_stops,
    normalize_category,
)
from backend.app.models import (
    Itinerary,
    PlanRequest,
    Stop,
)


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
        budget_total=120,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "activity",
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=30,
    )


def make_plan(
    *,
    total_cost: float = 100,
    include_activity: bool = True,
    include_restaurant: bool = True,
) -> Itinerary:
    stops: list[
        Stop
    ] = []

    if include_activity:
        stops.append(
            Stop(
                name="Test Gallery",
                category="activity",
                area="Back Bay",
                estimated_cost=20,
                duration_minutes=60,
                latitude=42.35,
                longitude=-71.08,
                source="test",
            )
        )

    if include_restaurant:
        stops.append(
            Stop(
                name="Test Chicken Restaurant",
                category="restaurant",
                area="Back Bay",
                estimated_cost=60,
                duration_minutes=90,
                latitude=42.351,
                longitude=-71.081,
                source="test",
            )
        )

    return Itinerary(
        label="Best overall",
        title="Test Plan",
        stops=stops,
        total_cost=total_cost,
        total_duration_minutes=150,
        estimated_travel_minutes=10,
        score=100,
        route_legs=[],
        validation_failures=[],
        reasons=[
            "Evaluation test plan."
        ],
        warnings=[],
    )


def test_clamp_score() -> None:
    assert (
        clamp_score(
            -1
        )
        == 0.0
    )

    assert (
        clamp_score(
            0.5
        )
        == 0.5
    )

    assert (
        clamp_score(
            2
        )
        == 1.0
    )


def test_normalize_dinner_category() -> None:
    assert (
        normalize_category(
            "dinner"
        )
        == "restaurant"
    )


def test_budget_passes_when_under_limit() -> None:
    metric = (
        evaluate_budget(
            request=make_request(),
            plan=make_plan(
                total_cost=100,
            ),
        )
    )

    assert (
        metric.passed
        is True
    )

    assert (
        metric.score
        == 1.0
    )


def test_budget_scores_over_budget_plan() -> None:
    metric = (
        evaluate_budget(
            request=make_request(),
            plan=make_plan(
                total_cost=150,
            ),
        )
    )

    assert (
        metric.passed
        is False
    )

    assert (
        0
        < metric.score
        < 1
    )


def test_required_stop_coverage_passes() -> None:
    metric = (
        evaluate_required_stops(
            request=make_request(),
            plan=make_plan(),
        )
    )

    assert (
        metric.passed
        is True
    )

    assert (
        metric.score
        == 1.0
    )


def test_required_stop_coverage_detects_missing_activity() -> None:
    metric = (
        evaluate_required_stops(
            request=make_request(),
            plan=make_plan(
                include_activity=False,
            ),
        )
    )

    assert (
        metric.passed
        is False
    )

    assert (
        metric.score
        == 0.5
    )

    assert (
        "activity"
        in metric.details
    )


def test_complete_plan_scores_one() -> None:
    evaluation = (
        evaluate_plan(
            request=make_request(),
            plan=make_plan(),
        )
    )

    assert (
        evaluation.overall_score
        == 1.0
    )

    assert (
        evaluation.budget_compliance.passed
        is True
    )

    assert (
        evaluation.required_stop_coverage.passed
        is True
    )

    assert (
        evaluation.no_hard_validation_errors.passed
        is True
    )


def test_evaluation_serializes_to_dictionary() -> None:
    evaluation = (
        evaluate_plan(
            request=make_request(),
            plan=make_plan(),
        )
    )

    result = (
        evaluation.to_dict()
    )

    assert (
        result[
            "overall_score"
        ]
        == 1.0
    )

    assert (
        result[
            "budget_compliance"
        ][
            "name"
        ]
        == "budget_compliance"
    )
