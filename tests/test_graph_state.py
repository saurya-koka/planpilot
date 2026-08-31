from backend.app.graph_state import (
    PlanPilotGraphState,
)
from backend.app.models import (
    PlanRequest,
)


def test_graph_state_accepts_minimal_state() -> None:
    request = PlanRequest()

    state: PlanPilotGraphState = {
        "user_message": (
            "Plan a dinner."
        ),
        "request": request,
        "venues": [],
        "plans": [],
        "selected_plan_index": 0,
        "has_usable_plan": False,
        "iteration_count": 0,
        "max_iterations": 4,
        "last_action": (
            "Graph initialized."
        ),
        "final_message": "",
        "exhausted": False,
    }

    assert (
        state[
            "request"
        ]
        is request
    )

    assert (
        state[
            "iteration_count"
        ]
        == 0
    )

    assert (
        state[
            "has_usable_plan"
        ]
        is False
    )


def test_graph_state_can_hold_start_coordinates() -> None:
    request = PlanRequest()

    state: PlanPilotGraphState = {
        "user_message": (
            "Plan a dinner."
        ),
        "request": request,
        "venues": [],
        "plans": [],
        "start_coordinates": (
            42.3507,
            -71.0797,
        ),
        "selected_plan_index": 0,
        "has_usable_plan": False,
        "iteration_count": 0,
        "max_iterations": 4,
        "last_action": "",
        "final_message": "",
        "exhausted": False,
    }

    assert (
        state[
            "start_coordinates"
        ]
        == (
            42.3507,
            -71.0797,
        )
    )
