from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
)
from typing import Any

from .models import (
    Itinerary,
    PlanRequest,
)


@dataclass(frozen=True)
class EvaluationMetric:
    """
    One objective PlanPilot evaluation result.
    """

    name: str
    passed: bool
    score: float
    details: str


@dataclass(frozen=True)
class PlanEvaluation:
    """
    Complete deterministic evaluation for one itinerary.
    """

    overall_score: float

    budget_compliance: EvaluationMetric

    required_stop_coverage: EvaluationMetric

    travel_constraint_compliance: EvaluationMetric

    plan_has_stops: EvaluationMetric

    no_hard_validation_errors: EvaluationMetric

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


def clamp_score(
    value: float,
) -> float:
    """
    Keep evaluation scores inside [0, 1].
    """

    return max(
        0.0,
        min(
            1.0,
            float(
                value
            ),
        ),
    )


def normalize_category(
    category: str,
) -> str:
    """
    Normalize planner terminology for evaluation.

    PlanPilot requests use "dinner" while venue stops use the
    category "restaurant".
    """

    normalized = (
        category
        .strip()
        .lower()
    )

    aliases = {
        "dinner": "restaurant",
        "food": "restaurant",
    }

    return aliases.get(
        normalized,
        normalized,
    )


def evaluate_budget(
    *,
    request: PlanRequest,
    plan: Itinerary,
) -> EvaluationMetric:
    """
    Check whether the itinerary stays inside the requested budget.
    """

    passed = (
        plan.total_cost
        <= request.budget_total
    )

    if passed:
        score = 1.0
        details = (
            f"${plan.total_cost:.2f} is within "
            f"the ${request.budget_total:.2f} budget."
        )

    else:
        overage = (
            plan.total_cost
            - request.budget_total
        )

        ratio = (
            request.budget_total
            / plan.total_cost
            if plan.total_cost > 0
            else 0.0
        )

        score = clamp_score(
            ratio
        )

        details = (
            f"${plan.total_cost:.2f} exceeds "
            f"the ${request.budget_total:.2f} budget "
            f"by ${overage:.2f}."
        )

    return EvaluationMetric(
        name="budget_compliance",
        passed=passed,
        score=score,
        details=details,
    )


def evaluate_required_stops(
    *,
    request: PlanRequest,
    plan: Itinerary,
) -> EvaluationMetric:
    """
    Measure coverage of required itinerary categories.
    """

    required = {
        normalize_category(
            category
        )
        for category
        in request.must_include
    }

    actual = {
        normalize_category(
            stop.category
        )
        for stop
        in plan.stops
    }

    if not required:
        return EvaluationMetric(
            name="required_stop_coverage",
            passed=True,
            score=1.0,
            details=(
                "The request had no required stop categories."
            ),
        )

    covered = (
        required
        & actual
    )

    missing = (
        required
        - actual
    )

    score = (
        len(
            covered
        )
        / len(
            required
        )
    )

    passed = (
        not missing
    )

    if passed:
        details = (
            "All requested stop categories are present."
        )

    else:
        details = (
            "Missing required categories: "
            + ", ".join(
                sorted(
                    missing
                )
            )
        )

    return EvaluationMetric(
        name="required_stop_coverage",
        passed=passed,
        score=clamp_score(
            score
        ),
        details=details,
    )


def evaluate_travel_constraints(
    *,
    request: PlanRequest,
    plan: Itinerary,
) -> EvaluationMetric:
    """
    Check every route leg against max_leg_minutes.
    """

    if not plan.route_legs:
        return EvaluationMetric(
            name="travel_constraint_compliance",
            passed=True,
            score=1.0,
            details=(
                "No route legs were available to violate "
                "the travel constraint."
            ),
        )

    compliant_legs = [
        leg
        for leg
        in plan.route_legs
        if (
            leg.duration_minutes
            <= request.max_leg_minutes
        )
    ]

    score = (
        len(
            compliant_legs
        )
        / len(
            plan.route_legs
        )
    )

    passed = (
        len(
            compliant_legs
        )
        == len(
            plan.route_legs
        )
    )

    if passed:
        details = (
            "All route legs satisfy the requested "
            f"{request.max_leg_minutes}-minute limit."
        )

    else:
        violations = [
            (
                f"{leg.from_name} -> "
                f"{leg.to_name}: "
                f"{leg.duration_minutes} min"
            )
            for leg
            in plan.route_legs
            if (
                leg.duration_minutes
                > request.max_leg_minutes
            )
        ]

        details = (
            "Travel constraint violations: "
            + "; ".join(
                violations
            )
        )

    return EvaluationMetric(
        name="travel_constraint_compliance",
        passed=passed,
        score=clamp_score(
            score
        ),
        details=details,
    )


def evaluate_plan_has_stops(
    *,
    plan: Itinerary,
) -> EvaluationMetric:
    """
    Ensure the planner produced a non-empty itinerary.
    """

    passed = (
        len(
            plan.stops
        )
        > 0
    )

    return EvaluationMetric(
        name="plan_has_stops",
        passed=passed,
        score=(
            1.0
            if passed
            else 0.0
        ),
        details=(
            f"Plan contains {len(plan.stops)} stop(s)."
        ),
    )


def evaluate_validation_failures(
    *,
    plan: Itinerary,
) -> EvaluationMetric:
    """
    Check that the itinerary contains no hard validation errors.

    Warnings do not fail this metric.
    """

    hard_failures = [
        failure
        for failure
        in plan.validation_failures
        if (
            getattr(
                failure,
                "severity",
                "",
            )
            == "error"
        )
    ]

    passed = (
        not hard_failures
    )

    return EvaluationMetric(
        name="no_hard_validation_errors",
        passed=passed,
        score=(
            1.0
            if passed
            else 0.0
        ),
        details=(
            "No hard validation errors."
            if passed
            else (
                f"{len(hard_failures)} hard validation "
                "error(s) remain."
            )
        ),
    )


def evaluate_plan(
    *,
    request: PlanRequest,
    plan: Itinerary,
) -> PlanEvaluation:
    """
    Run PlanPilot's deterministic objective evaluation suite.

    Every metric is normalized to [0, 1].

    The initial V2.11 score weights hard constraints more heavily
    than softer structural checks.
    """

    budget = (
        evaluate_budget(
            request=request,
            plan=plan,
        )
    )

    required = (
        evaluate_required_stops(
            request=request,
            plan=plan,
        )
    )

    travel = (
        evaluate_travel_constraints(
            request=request,
            plan=plan,
        )
    )

    has_stops = (
        evaluate_plan_has_stops(
            plan=plan,
        )
    )

    validation = (
        evaluate_validation_failures(
            plan=plan,
        )
    )

    weighted_score = (
        budget.score
        * 0.25
        + required.score
        * 0.30
        + travel.score
        * 0.20
        + has_stops.score
        * 0.10
        + validation.score
        * 0.15
    )

    return PlanEvaluation(
        overall_score=round(
            clamp_score(
                weighted_score
            ),
            4,
        ),
        budget_compliance=budget,
        required_stop_coverage=required,
        travel_constraint_compliance=travel,
        plan_has_stops=has_stops,
        no_hard_validation_errors=validation,
    )
