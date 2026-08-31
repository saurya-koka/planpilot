from backend.app.graph_nodes import (
    build_plans_node,
    finish_graph_node,
    initialize_graph_state,
    repair_selected_plan_node,
    validate_plans_node,
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


def test_initialize_graph_state_sets_defaults() -> None:
    request = make_request()

    result = (
        initialize_graph_state(
            {
                "user_message": (
                    "Plan dinner."
                ),
                "request": request,
                "venues": (
                    make_venues()
                ),
            }
        )
    )

    assert (
        result[
            "iteration_count"
        ]
        == 0
    )

    assert (
        result[
            "max_iterations"
        ]
        == 4
    )

    assert (
        result[
            "exhausted"
        ]
        is False
    )


def test_build_and_validate_nodes_find_usable_plan() -> None:
    request = make_request()

    built = build_plans_node(
        {
            "request": request,
            "venues": (
                make_venues()
            ),
            "start_coordinates": None,
        }
    )

    assert built[
        "plans"
    ]

    validated = (
        validate_plans_node(
            {
                "plans": (
                    built[
                        "plans"
                    ]
                ),
            }
        )
    )

    assert (
        validated[
            "has_usable_plan"
        ]
        is True
    )


def test_repair_node_can_fix_budget_failure() -> None:
    request = make_request(
        budget_total=80,
    )

    venues = make_venues()

    from backend.app.planner import (
        build_itinerary,
    )

    broken_plan = (
        build_itinerary(
            request=request,
            chosen_venues=[
                venues[0],
            ],
            start_coordinates=None,
            prefer_live=False,
        )
    )

    result = (
        repair_selected_plan_node(
            {
                "request": request,
                "venues": venues,
                "plans": [
                    broken_plan,
                ],
                "selected_plan_index": 0,
                "iteration_count": 0,
                "start_coordinates": None,
            }
        )
    )

    assert (
        result[
            "iteration_count"
        ]
        == 1
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )


def test_finish_node_reports_success() -> None:
    request = make_request()

    built = build_plans_node(
        {
            "request": request,
            "venues": (
                make_venues()
            ),
        }
    )

    result = finish_graph_node(
        {
            "plans": (
                built[
                    "plans"
                ]
            ),
        }
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )

    assert (
        "usable itinerary"
        in result[
            "final_message"
        ].lower()
    )
