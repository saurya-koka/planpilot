from __future__ import annotations

import json

from backend.app.eval_runner import (
    EvaluationCase,
    evaluate_case,
    load_evaluation_cases,
    run_evaluation,
    validate_mode,
)


def test_validate_mode() -> None:
    assert (
        validate_mode(
            "deterministic"
        )
        == "deterministic"
    )

    assert (
        validate_mode(
            "AGENTIC"
        )
        == "agentic"
    )


def test_load_evaluation_cases(
    tmp_path,
) -> None:
    path = (
        tmp_path
        / "cases.json"
    )

    path.write_text(
        json.dumps(
            [
                {
                    "id": "case-1",
                    "text": (
                        "Plan dinner "
                        "in Boston."
                    ),
                    "start_area": (
                        "Back Bay"
                    ),
                    "expected": {
                        "city": (
                            "Boston"
                        )
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    cases = (
        load_evaluation_cases(
            path
        )
    )

    assert (
        len(
            cases
        )
        == 1
    )

    assert (
        cases[
            0
        ].id
        == "case-1"
    )


def test_deterministic_evaluate_case() -> None:
    case = EvaluationCase(
        id="basic",
        text=(
            "Plan a dinner "
            "in Boston for "
            "two people "
            "under 120 dollars."
        ),
        start_area="Back Bay",
        expected={},
    )

    result = (
        evaluate_case(
            case,
            mode="deterministic",
        )
    )

    assert (
        result.execution_success
        is True
    )

    assert (
        result.engine_metadata[
            "engine"
        ]
        == "deterministic_planner"
    )

    assert (
        result.engine_metadata[
            "graph_used"
        ]
        is False
    )

    assert (
        0
        <= result.overall_score
        <= 1
    )


def test_agentic_evaluate_case_uses_graph(
    monkeypatch,
) -> None:
    from backend.app import (
        eval_runner,
    )

    case = EvaluationCase(
        id="agentic",
        text=(
            "Plan dinner "
            "in Boston."
        ),
        start_area="Back Bay",
        expected={},
    )

    request = (
        eval_runner.case_to_request(
            case
        )
    )

    plans = (
        eval_runner.build_plans(
            request=request
        )
    )

    # Prevent this unit test from making a real
    # Geoapify geocoding request.
    monkeypatch.setattr(
        eval_runner,
        "geocode_start_area",
        lambda request: (
            42.3507,
            -71.0797,
        ),
    )

    captured: dict[
        str,
        object,
    ] = {}

    def fake_run_planpilot_graph(
        **kwargs,
    ):
        captured.update(
            kwargs
        )

        return {
            "plans": plans,
            "has_usable_plan": True,
            "iteration_count": 1,
            "search_count": 2,
            "exhausted": False,
            "searched_categories": [
                "restaurant",
            ],
            "rag_used": True,
            "rag_result_count": 3,
            "weather_checked": True,
            "weather_adjusted": False,
        }

    monkeypatch.setattr(
        eval_runner,
        "run_planpilot_graph",
        fake_run_planpilot_graph,
    )

    result = (
        evaluate_case(
            case,
            mode="agentic",
        )
    )

    assert (
        result.execution_success
        is True
    )

    assert (
        result.engine_metadata[
            "engine"
        ]
        == "langgraph_agentic"
    )

    assert (
        result.engine_metadata[
            "graph_used"
        ]
        is True
    )

    assert (
        result.engine_metadata[
            "graph_search_count"
        ]
        == 2
    )

    assert (
        result.engine_metadata[
            "rag_used"
        ]
        is True
    )

    assert (
        result.engine_metadata[
            "start_coordinates_used"
        ]
        is True
    )

    assert (
        result.engine_metadata[
            "start_coordinates"
        ]
        == [
            42.3507,
            -71.0797,
        ]
    )

    assert (
        captured[
            "start_coordinates"
        ]
        == (
            42.3507,
            -71.0797,
        )
    )

    assert (
        captured[
            "max_iterations"
        ]
        == 4
    )

    assert (
        captured[
            "request"
        ]
        == request
    )


def test_run_evaluation_records_mode() -> None:
    report = (
        run_evaluation(
            [],
            mode="agentic",
        )
    )

    assert (
        report.mode
        == "agentic"
    )

    assert (
        report.total_cases
        == 0
    )

    assert (
        report.executed_cases
        == 0
    )

    assert (
        report.execution_success_rate
        == 0.0
    )

    assert (
        report.pass_rate
        == 0.0
    )

    assert (
        report.average_score
        == 0.0
    )


def test_run_evaluation_aggregates_results() -> None:
    cases = [
        EvaluationCase(
            id="case-1",
            text=(
                "Plan dinner "
                "in Boston."
            ),
            start_area="Back Bay",
            expected={},
        )
    ]

    report = (
        run_evaluation(
            cases,
            mode="deterministic",
        )
    )

    assert (
        report.mode
        == "deterministic"
    )

    assert (
        report.total_cases
        == 1
    )

    assert (
        report.executed_cases
        <= 1
    )

    assert (
        report.passed_cases
        <= report.executed_cases
    )

    assert (
        0
        <= report.execution_success_rate
        <= 1
    )

    assert (
        0
        <= report.pass_rate
        <= 1
    )

    assert (
        0
        <= report.average_score
        <= 1
    )

    assert (
        0
        <= report.budget_compliance_rate
        <= 1
    )

    assert (
        0
        <= report.required_stop_coverage_rate
        <= 1
    )

    assert (
        0
        <= report.travel_constraint_compliance_rate
        <= 1
    )

    assert (
        0
        <= report.plan_structure_rate
        <= 1
    )

    assert (
        0
        <= report.validation_pass_rate
        <= 1
    )
