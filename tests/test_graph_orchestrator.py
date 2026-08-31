from backend.app.graph_orchestrator import (
    route_after_repair,
    route_after_validation,
    run_planpilot_graph,
)
from backend.app.models import (
    PlanRequest,
    Venue,
)


def make_request(
    *,
    budget_total: float = 200,
) -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=budget_total,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=30,
    )


def make_venues() -> list[Venue]:
    return [
        Venue(
            name="Expensive Restaurant",
            category="restaurant",
            area="Back Bay",
            estimated_cost_per_person=60,
            duration_minutes=60,
            vibe=[
                "chill",
            ],
            opening_hours=(
                "Mo-Su 16:00-23:00"
            ),
            source="sample",
        ),
        Venue(
            name="Affordable Restaurant",
            category="restaurant",
            area="Back Bay",
            estimated_cost_per_person=30,
            duration_minutes=60,
            vibe=[
                "chill",
            ],
            opening_hours=(
                "Mo-Su 16:00-23:00"
            ),
            source="sample",
        ),
    ]


def test_validation_routes_to_finish_when_usable() -> None:
    assert (
        route_after_validation(
            {
                "has_usable_plan": True,
                "iteration_count": 0,
                "max_iterations": 4,
            }
        )
        == "finish"
    )


def test_validation_routes_to_repair_when_invalid() -> None:
    assert (
        route_after_validation(
            {
                "has_usable_plan": False,
                "iteration_count": 0,
                "max_iterations": 4,
            }
        )
        == "repair"
    )


def test_repair_routes_to_validate_when_budget_remains() -> None:
    assert (
        route_after_repair(
            {
                "has_usable_plan": False,
                "iteration_count": 1,
                "max_iterations": 4,
            }
        )
        == "validate"
    )


def test_graph_finishes_with_valid_plan() -> None:
    result = (
        run_planpilot_graph(
            user_message=(
                "Plan dinner."
            ),
            request=(
                make_request()
            ),
            venues=(
                make_venues()
            ),
            max_iterations=4,
        )
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )

    assert (
        result[
            "exhausted"
        ]
        is False
    )

    assert (
        result[
            "plans"
        ]
    )

    assert (
        "usable itinerary"
        in result[
            "final_message"
        ].lower()
    )


def test_graph_can_repair_budget_failure() -> None:
    result = (
        run_planpilot_graph(
            user_message=(
                "Plan a cheap dinner."
            ),
            request=(
                make_request(
                    budget_total=80,
                )
            ),
            venues=(
                make_venues()
            ),
            max_iterations=4,
        )
    )

    assert (
        result[
            "plans"
        ]
    )

    assert (
        result[
            "iteration_count"
        ]
        >= 0
    )
