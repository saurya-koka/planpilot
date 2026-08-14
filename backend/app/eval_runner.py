from __future__ import annotations

import json
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path
from typing import (
    Any,
    Literal,
)

from .data import (
    VENUES,
)
from .evaluation import (
    PlanEvaluation,
    evaluate_plan,
)
from .graph_orchestrator import (
    run_planpilot_graph,
)
from .llm import (
    parse_natural_language_request,
)
from .main import (
    geocode_start_area,
    parsed_to_plan_request,
)
from .models import (
    NaturalLanguageRequest,
    PlanRequest,
)
from .planner import (
    build_plans,
)


EvaluationMode = Literal[
    "deterministic",
    "agentic",
]


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    text: str
    start_area: str
    expected: dict[
        str,
        Any,
    ]


@dataclass(frozen=True)
class EvaluationCaseResult:
    case_id: str

    execution_success: bool

    passed: bool

    overall_score: float

    best_plan_title: str

    metrics: dict[
        str,
        Any,
    ]

    engine_metadata: dict[
        str,
        Any,
    ]

    error: str | None = None


@dataclass(frozen=True)
class EvaluationReport:
    mode: str

    total_cases: int

    executed_cases: int

    execution_failures: int

    passed_cases: int

    failed_cases: int

    execution_success_rate: float

    pass_rate: float

    average_score: float

    budget_compliance_rate: float

    required_stop_coverage_rate: float

    travel_constraint_compliance_rate: float

    plan_structure_rate: float

    validation_pass_rate: float

    cases: list[
        EvaluationCaseResult
    ]

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


def validate_mode(
    mode: str,
) -> EvaluationMode:
    normalized = (
        mode
        .strip()
        .lower()
    )

    if normalized not in {
        "deterministic",
        "agentic",
    }:
        raise ValueError(
            "Evaluation mode must be "
            "'deterministic' or 'agentic'."
        )

    return normalized


def load_evaluation_cases(
    path: str | Path,
) -> list[
    EvaluationCase
]:
    """
    Load benchmark cases from JSON.
    """

    path = Path(
        path
    )

    raw = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return [
        EvaluationCase(
            id=item[
                "id"
            ],
            text=item[
                "text"
            ],
            start_area=item.get(
                "start_area",
                "Davis Square",
            ),
            expected=item.get(
                "expected",
                {},
            ),
        )
        for item
        in raw
    ]


def case_to_request(
    case: EvaluationCase,
) -> PlanRequest:
    """
    Convert one benchmark prompt into PlanPilot's PlanRequest.
    """

    payload = (
        NaturalLanguageRequest(
            text=case.text,
            start_area=(
                case.start_area
            ),
            food_preferences=[],
        )
    )

    parsed = (
        parse_natural_language_request(
            case.text
        )
    )

    return (
        parsed_to_plan_request(
            parsed=parsed,
            payload=payload,
        )
    )


def evaluation_passed(
    evaluation: PlanEvaluation,
) -> bool:
    """
    A benchmark passes only when all objective constraints pass.
    """

    return all(
        [
            (
                evaluation
                .budget_compliance
                .passed
            ),
            (
                evaluation
                .required_stop_coverage
                .passed
            ),
            (
                evaluation
                .travel_constraint_compliance
                .passed
            ),
            (
                evaluation
                .plan_has_stops
                .passed
            ),
            (
                evaluation
                .no_hard_validation_errors
                .passed
            ),
        ]
    )


def run_deterministic_engine(
    *,
    request: PlanRequest,
) -> tuple[
    list[Any],
    dict[str, Any],
]:
    """
    Execute the normal deterministic planner benchmark.

    This preserves the original V2.11 baseline.
    """

    plans = (
        build_plans(
            request=request
        )
    )

    return (
        plans,
        {
            "engine": (
                "deterministic_planner"
            ),
            "graph_used": False,
            "graph_iterations": 0,
            "graph_search_count": 0,
            "graph_exhausted": False,
        },
    )


def run_agentic_engine(
    *,
    case: EvaluationCase,
    request: PlanRequest,
) -> tuple[
    list[Any],
    dict[str, Any],
]:
    """
    Run PlanPilot's complete LangGraph orchestration benchmark.

    Unlike the deterministic baseline, agentic mode resolves the
    user's starting area to coordinates before graph execution.

    Those coordinates are then available to:

        - hybrid retrieval
        - routing
        - LangGraph repair
        - live venue expansion
        - location-aware search

    This makes the benchmark representative of the production
    PlanPilot graph pipeline.
    """

    start_coordinates = (
        geocode_start_area(
            request
        )
    )

    result = (
        run_planpilot_graph(
            user_message=(
                case.text
            ),
            request=request,
            venues=list(
                VENUES
            ),
            start_coordinates=(
                start_coordinates
            ),
            max_iterations=4,
        )
    )

    plans = list(
        result.get(
            "plans",
            [],
        )
    )

    metadata = {
        "engine": (
            "langgraph_agentic"
        ),

        "graph_used": True,

        "start_coordinates_used": (
            start_coordinates
            is not None
        ),

        "start_coordinates": (
            list(
                start_coordinates
            )
            if start_coordinates
            is not None
            else None
        ),

        "graph_success": (
            result.get(
                "has_usable_plan",
                False,
            )
        ),

        "graph_iterations": (
            result.get(
                "iteration_count",
                0,
            )
        ),

        "graph_search_count": (
            result.get(
                "search_count",
                0,
            )
        ),

        "graph_exhausted": (
            result.get(
                "exhausted",
                False,
            )
        ),

        "searched_categories": (
            result.get(
                "searched_categories",
                [],
            )
        ),

        "rag_used": (
            result.get(
                "rag_used",
                False,
            )
        ),

        "rag_result_count": (
            result.get(
                "rag_result_count",
                0,
            )
        ),

        "weather_checked": (
            result.get(
                "weather_checked",
                False,
            )
        ),

        "weather_adjusted": (
            result.get(
                "weather_adjusted",
                False,
            )
        ),
    }

    return (
        plans,
        metadata,
    )


def execute_case(
    *,
    case: EvaluationCase,
    request: PlanRequest,
    mode: EvaluationMode,
) -> tuple[
    list[Any],
    dict[str, Any],
]:
    """
    Execute one case using the requested benchmark engine.
    """

    if mode == "agentic":
        return (
            run_agentic_engine(
                case=case,
                request=request,
            )
        )

    return (
        run_deterministic_engine(
            request=request
        )
    )


def evaluate_case(
    case: EvaluationCase,
    mode: str = "deterministic",
) -> EvaluationCaseResult:
    """
    Execute and objectively score one benchmark case.
    """

    selected_mode = (
        validate_mode(
            mode
        )
    )

    try:
        request = (
            case_to_request(
                case
            )
        )

        (
            plans,
            engine_metadata,
        ) = (
            execute_case(
                case=case,
                request=request,
                mode=selected_mode,
            )
        )

        if not plans:
            return (
                EvaluationCaseResult(
                    case_id=(
                        case.id
                    ),
                    execution_success=False,
                    passed=False,
                    overall_score=0.0,
                    best_plan_title="",
                    metrics={},
                    engine_metadata=(
                        engine_metadata
                    ),
                    error=(
                        "No itinerary "
                        "candidate produced."
                    ),
                )
            )

        evaluated = [
            (
                plan,
                evaluate_plan(
                    request=request,
                    plan=plan,
                ),
            )
            for plan
            in plans
        ]

        best_plan, best_eval = max(
            evaluated,
            key=lambda item: (
                item[
                    1
                ]
                .overall_score
            ),
        )

        return (
            EvaluationCaseResult(
                case_id=(
                    case.id
                ),
                execution_success=True,
                passed=(
                    evaluation_passed(
                        best_eval
                    )
                ),
                overall_score=(
                    best_eval
                    .overall_score
                ),
                best_plan_title=(
                    best_plan.title
                ),
                metrics=(
                    best_eval
                    .to_dict()
                ),
                engine_metadata=(
                    engine_metadata
                ),
                error=None,
            )
        )

    except Exception as exc:
        return (
            EvaluationCaseResult(
                case_id=(
                    case.id
                ),
                execution_success=False,
                passed=False,
                overall_score=0.0,
                best_plan_title="",
                metrics={},
                engine_metadata={
                    "engine": (
                        selected_mode
                    ),
                },
                error=str(
                    exc
                ),
            )
        )


def metric_pass_rate(
    *,
    results: list[
        EvaluationCaseResult
    ],
    metric_name: str,
) -> float:
    """
    Calculate pass rate for one objective metric.
    """

    executed = [
        result
        for result
        in results
        if (
            result.execution_success
            and result.metrics
        )
    ]

    if not executed:
        return 0.0

    passed_count = sum(
        1
        for result
        in executed
        if (
            result.metrics.get(
                metric_name,
                {},
            ).get(
                "passed",
                False,
            )
        )
    )

    return round(
        passed_count
        / len(
            executed
        ),
        4,
    )


def run_evaluation(
    cases: list[
        EvaluationCase
    ],
    mode: str = "deterministic",
) -> EvaluationReport:
    """
    Execute the benchmark using one PlanPilot engine.
    """

    selected_mode = (
        validate_mode(
            mode
        )
    )

    results = [
        evaluate_case(
            case,
            mode=selected_mode,
        )
        for case
        in cases
    ]

    total_cases = len(
        results
    )

    executed = [
        result
        for result
        in results
        if (
            result.execution_success
        )
    ]

    passed = [
        result
        for result
        in results
        if result.passed
    ]

    executed_cases = len(
        executed
    )

    execution_failures = (
        total_cases
        - executed_cases
    )

    passed_cases = len(
        passed
    )

    failed_cases = (
        total_cases
        - passed_cases
    )

    execution_success_rate = (
        executed_cases
        / total_cases
        if total_cases
        else 0.0
    )

    pass_rate = (
        passed_cases
        / total_cases
        if total_cases
        else 0.0
    )

    average_score = (
        sum(
            result.overall_score
            for result
            in executed
        )
        / executed_cases
        if executed_cases
        else 0.0
    )

    return EvaluationReport(
        mode=selected_mode,
        total_cases=(
            total_cases
        ),
        executed_cases=(
            executed_cases
        ),
        execution_failures=(
            execution_failures
        ),
        passed_cases=(
            passed_cases
        ),
        failed_cases=(
            failed_cases
        ),
        execution_success_rate=round(
            execution_success_rate,
            4,
        ),
        pass_rate=round(
            pass_rate,
            4,
        ),
        average_score=round(
            average_score,
            4,
        ),
        budget_compliance_rate=(
            metric_pass_rate(
                results=results,
                metric_name=(
                    "budget_compliance"
                ),
            )
        ),
        required_stop_coverage_rate=(
            metric_pass_rate(
                results=results,
                metric_name=(
                    "required_stop_coverage"
                ),
            )
        ),
        travel_constraint_compliance_rate=(
            metric_pass_rate(
                results=results,
                metric_name=(
                    "travel_constraint_compliance"
                ),
            )
        ),
        plan_structure_rate=(
            metric_pass_rate(
                results=results,
                metric_name=(
                    "plan_has_stops"
                ),
            )
        ),
        validation_pass_rate=(
            metric_pass_rate(
                results=results,
                metric_name=(
                    "no_hard_validation_errors"
                ),
            )
        ),
        cases=results,
    )
