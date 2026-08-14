from __future__ import annotations

import argparse
import json
from pathlib import Path

from .eval_runner import (
    EvaluationReport,
    load_evaluation_cases,
    run_evaluation,
)


def percentage(
    value: float,
) -> str:
    return (
        f"{value * 100:.1f}%"
    )


def print_report(
    report: EvaluationReport,
) -> None:
    print()
    print(
        "PlanPilot Evaluation Report"
    )
    print(
        "==========================="
    )

    print(
        f"Mode:                      "
        f"{report.mode}"
    )

    print(
        f"Total cases:               "
        f"{report.total_cases}"
    )

    print(
        f"Executed successfully:     "
        f"{report.executed_cases}"
    )

    print(
        f"Execution failures:        "
        f"{report.execution_failures}"
    )

    print(
        f"Benchmark passes:          "
        f"{report.passed_cases}"
    )

    print(
        f"Benchmark failures:        "
        f"{report.failed_cases}"
    )

    print()

    print(
        f"Execution success rate:    "
        f"{percentage(report.execution_success_rate)}"
    )

    print(
        f"Benchmark pass rate:       "
        f"{percentage(report.pass_rate)}"
    )

    print(
        f"Average quality score:     "
        f"{percentage(report.average_score)}"
    )

    print()
    print(
        "Constraint Metrics"
    )
    print(
        "------------------"
    )

    print(
        f"Budget compliance:         "
        f"{percentage(report.budget_compliance_rate)}"
    )

    print(
        f"Required-stop coverage:    "
        f"{percentage(report.required_stop_coverage_rate)}"
    )

    print(
        f"Travel compliance:         "
        f"{percentage(report.travel_constraint_compliance_rate)}"
    )

    print(
        f"Plan structure:            "
        f"{percentage(report.plan_structure_rate)}"
    )

    print(
        f"Validation pass rate:      "
        f"{percentage(report.validation_pass_rate)}"
    )

    print()
    print(
        "Case Results"
    )
    print(
        "------------"
    )

    for result in report.cases:
        if not result.execution_success:
            status = "ERROR"

        elif result.passed:
            status = "PASS"

        else:
            status = "FAIL"

        print(
            f"{status:5} "
            f"{result.case_id:30} "
            f"{percentage(result.overall_score)}"
        )

        if (
            result.best_plan_title
        ):
            print(
                "      Best plan: "
                f"{result.best_plan_title}"
            )

        metadata = (
            result.engine_metadata
        )

        if (
            report.mode
            == "agentic"
            and metadata
        ):
            print(
                "      Graph: "
                f"{metadata.get('graph_iterations', 0)} "
                "iteration(s), "
                f"{metadata.get('graph_search_count', 0)} "
                "search(es), "
                "RAG="
                f"{metadata.get('rag_used', False)}"
            )

        if result.error:
            print(
                "      Error: "
                f"{result.error}"
            )


def save_json_report(
    *,
    report: EvaluationReport,
    output_path: str | Path,
) -> None:
    output_path = Path(
        output_path
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the PlanPilot "
            "evaluation benchmark."
        )
    )

    parser.add_argument(
        "--cases",
        default="evals/cases.json",
        help=(
            "Path to evaluation "
            "case JSON."
        ),
    )

    parser.add_argument(
        "--mode",
        choices=[
            "deterministic",
            "agentic",
        ],
        default="deterministic",
        help=(
            "PlanPilot execution engine "
            "to benchmark."
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Optional path for the "
            "JSON evaluation report."
        ),
    )

    args = (
        parser.parse_args()
    )

    output_path = (
        args.output
        or (
            "evals/results/"
            f"{args.mode}_latest.json"
        )
    )

    cases = (
        load_evaluation_cases(
            args.cases
        )
    )

    report = (
        run_evaluation(
            cases,
            mode=args.mode,
        )
    )

    print_report(
        report
    )

    save_json_report(
        report=report,
        output_path=output_path,
    )

    print()
    print(
        "JSON report written to:"
    )
    print(
        output_path
    )


if __name__ == "__main__":
    main()
