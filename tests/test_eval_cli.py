from __future__ import annotations

import json

from backend.app.eval_cli import (
    percentage,
    save_json_report,
)
from backend.app.eval_runner import (
    EvaluationCaseResult,
    EvaluationReport,
)


def make_report() -> EvaluationReport:
    return EvaluationReport(
        mode="deterministic",
        total_cases=1,
        executed_cases=1,
        execution_failures=0,
        passed_cases=1,
        failed_cases=0,
        execution_success_rate=1.0,
        pass_rate=1.0,
        average_score=0.875,
        budget_compliance_rate=1.0,
        required_stop_coverage_rate=1.0,
        travel_constraint_compliance_rate=1.0,
        plan_structure_rate=1.0,
        validation_pass_rate=1.0,
        cases=[
            EvaluationCaseResult(
                case_id="test-case",
                execution_success=True,
                passed=True,
                overall_score=0.875,
                best_plan_title=(
                    "Test Plan"
                ),
                metrics={},
                engine_metadata={
                    "engine": (
                        "deterministic_planner"
                    ),
                },
                error=None,
            )
        ],
    )


def test_percentage_formatting() -> None:
    assert (
        percentage(
            1.0
        )
        == "100.0%"
    )

    assert (
        percentage(
            0.875
        )
        == "87.5%"
    )


def test_save_json_report(
    tmp_path,
) -> None:
    path = (
        tmp_path
        / "report.json"
    )

    save_json_report(
        report=make_report(),
        output_path=path,
    )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    assert (
        data[
            "mode"
        ]
        == "deterministic"
    )

    assert (
        data[
            "pass_rate"
        ]
        == 1.0
    )
