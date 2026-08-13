from __future__ import annotations

from langgraph.graph import (
    END,
    StateGraph,
)

from .graph_nodes import (
    build_plans_node,
    finish_graph_node,
    initialize_graph_state,
    repair_selected_plan_node,
    required_search_categories,
    search_venues_node,
    validate_plans_node,
)
from .graph_rag import (
    retrieve_rag_context_node,
)
from .graph_state import (
    PlanPilotGraphState,
)
from .models import (
    PlanRequest,
    Venue,
)


def has_unsearched_categories(
    state: PlanPilotGraphState,
) -> bool:
    """
    Return True when the request requires a venue category that has
    not yet been searched during this graph run.
    """

    request = state.get(
        "request"
    )

    if request is None:
        return False

    required = (
        required_search_categories(
            request
        )
    )

    searched = set(
        state.get(
            "searched_categories",
            [],
        )
    )

    return any(
        category
        not in searched
        for category
        in required
    )


def route_after_validation(
    state: PlanPilotGraphState,
) -> str:
    """
    Choose the next graph strategy.

    1. Finish when a usable plan exists.
    2. Try deterministic repair.
    3. After repair, expand the venue pool with search when a required
       category has not yet been searched.
    4. Continue bounded repair after search.
    5. Finish when the iteration budget is exhausted.
    """

    if state.get(
        "has_usable_plan",
        False,
    ):
        return "finish"

    iteration_count = state.get(
        "iteration_count",
        0,
    )

    max_iterations = state.get(
        "max_iterations",
        4,
    )

    if (
        iteration_count
        >= max_iterations
    ):
        return "finish"

    if (
        iteration_count > 0
        and has_unsearched_categories(
            state
        )
    ):
        return "search"

    return "repair"


def route_after_repair(
    state: PlanPilotGraphState,
) -> str:
    """
    Validate every repaired candidate before choosing another action.
    """

    if state.get(
        "has_usable_plan",
        False,
    ):
        return "validate"

    iteration_count = state.get(
        "iteration_count",
        0,
    )

    max_iterations = state.get(
        "max_iterations",
        4,
    )

    if (
        iteration_count
        >= max_iterations
    ):
        return "finish"

    return "validate"


def route_after_search(
    state: PlanPilotGraphState,
) -> str:
    """
    Search may rebuild candidate plans.

    Validate the resulting candidate state before taking another
    action.
    """

    return "validate"


def build_planpilot_graph():
    """
    Compile the PlanPilot LangGraph workflow.

        initialize
            |
            v
         retrieve
            |
            v
        build_plans
            |
            v
         validate
        /   |    \\
       /    |     \\
    finish repair search
             |      |
             v      v
          validate validate
    """

    graph = StateGraph(
        PlanPilotGraphState
    )

    graph.add_node(
        "initialize",
        initialize_graph_state,
    )

    graph.add_node(
        "retrieve",
        retrieve_rag_context_node,
    )

    graph.add_node(
        "build_plans",
        build_plans_node,
    )

    graph.add_node(
        "validate",
        validate_plans_node,
    )

    graph.add_node(
        "repair",
        repair_selected_plan_node,
    )

    graph.add_node(
        "search",
        search_venues_node,
    )

    graph.add_node(
        "finish",
        finish_graph_node,
    )

    graph.set_entry_point(
        "initialize"
    )

    graph.add_edge(
        "initialize",
        "retrieve",
    )

    graph.add_edge(
        "retrieve",
        "build_plans",
    )

    graph.add_edge(
        "build_plans",
        "validate",
    )

    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "finish": "finish",
            "repair": "repair",
            "search": "search",
        },
    )

    graph.add_conditional_edges(
        "repair",
        route_after_repair,
        {
            "validate": "validate",
            "finish": "finish",
        },
    )

    graph.add_conditional_edges(
        "search",
        route_after_search,
        {
            "validate": (
                "validate"
            ),
        },
    )

    graph.add_edge(
        "finish",
        END,
    )

    return graph.compile()


PLANPILOT_GRAPH = (
    build_planpilot_graph()
)


def run_planpilot_graph(
    *,
    user_message: str,
    request: PlanRequest,
    venues: list[
        Venue
    ],
    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None,
    max_iterations: int = 4,
) -> PlanPilotGraphState:
    """
    Execute the compiled LangGraph workflow.
    """

    if max_iterations < 1:
        raise ValueError(
            "max_iterations must be "
            "at least 1."
        )

    initial_state: PlanPilotGraphState = {
        "user_message": (
            user_message
        ),
        "request": request,
        "venues": list(
            venues
        ),
        "plans": [],
        "start_coordinates": (
            start_coordinates
        ),
        "selected_plan_index": 0,
        "has_usable_plan": False,
        "iteration_count": 0,
        "max_iterations": (
            max_iterations
        ),
        "searched_categories": [],
        "search_count": 0,
        "rag_query": "",
        "rag_context": "",
        "rag_result_count": 0,
        "rag_document_ids": [],
        "rag_ranked_venue_names": [],
        "rag_used": False,
        "last_action": "",
        "final_message": "",
        "exhausted": False,
    }

    result = (
        PLANPILOT_GRAPH.invoke(
            initial_state
        )
    )

    return result
