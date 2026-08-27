from __future__ import annotations

from time import perf_counter

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
from .graph_weather import (
    apply_weather_constraints_node,
    retrieve_weather_context_node,
)
from .models import (
    PlanRequest,
    Venue,
)
from .observability import (
    TRACE_STORE,
    traced_node,
)


def has_unsearched_categories(
    state: PlanPilotGraphState,
) -> bool:
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
    return "validate"


def build_planpilot_graph():
    """
    Compile the PlanPilot LangGraph workflow.

        initialize
            |
            v
         weather
            |
            v
    weather_constraints
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

    V2.12 wraps every execution node with native PlanPilot tracing.
    """

    graph = StateGraph(
        PlanPilotGraphState
    )

    graph.add_node(
        "initialize",
        traced_node(
            node_name="initialize",
            node=initialize_graph_state,
        ),
    )

    graph.add_node(
        "weather",
        traced_node(
            node_name="weather",
            node=(
                retrieve_weather_context_node
            ),
        ),
    )

    graph.add_node(
        "weather_constraints",
        traced_node(
            node_name=(
                "weather_constraints"
            ),
            node=(
                apply_weather_constraints_node
            ),
        ),
    )

    graph.add_node(
        "retrieve",
        traced_node(
            node_name="retrieve",
            node=(
                retrieve_rag_context_node
            ),
        ),
    )

    graph.add_node(
        "build_plans",
        traced_node(
            node_name="build_plans",
            node=build_plans_node,
        ),
    )

    graph.add_node(
        "validate",
        traced_node(
            node_name="validate",
            node=validate_plans_node,
        ),
    )

    graph.add_node(
        "repair",
        traced_node(
            node_name="repair",
            node=(
                repair_selected_plan_node
            ),
        ),
    )

    graph.add_node(
        "search",
        traced_node(
            node_name="search",
            node=search_venues_node,
        ),
    )

    graph.add_node(
        "finish",
        traced_node(
            node_name="finish",
            node=finish_graph_node,
        ),
    )

    graph.set_entry_point(
        "initialize"
    )

    graph.add_edge(
        "initialize",
        "weather",
    )

    graph.add_edge(
        "weather",
        "weather_constraints",
    )

    graph.add_edge(
        "weather_constraints",
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
            "validate": "validate",
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
    Execute the compiled PlanPilot LangGraph workflow.

    V2.12 creates one structured trace for the complete graph run.
    """

    if max_iterations < 1:
        raise ValueError(
            "max_iterations must be "
            "at least 1."
        )

    trace = (
        TRACE_STORE.start_trace(
            metadata={
                "city": (
                    request.city
                ),
                "start_area": (
                    request.start_area
                ),
                "max_iterations": (
                    max_iterations
                ),
                "initial_venue_count": (
                    len(
                        venues
                    )
                ),
            }
        )
    )

    trace_id = (
        trace.trace_id
    )

    initial_state: PlanPilotGraphState = {
        "trace_id": (
            trace_id
        ),

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

        "weather_checked": False,

        "weather_condition": "",

        "weather_temperature_c": 0.0,

        "weather_precipitation_probability": (
            0.0
        ),

        "weather_wind_speed_kph": 0.0,

        "weather_risk_level": "",

        "weather_outdoor_safe": True,

        "weather_reasons": [],

        "weather_source": "",

        "weather_adjusted": False,

        "weather_original_venue_count": (
            len(
                venues
            )
        ),

        "weather_filtered_venue_count": (
            len(
                venues
            )
        ),

        "weather_removed_venue_names": [],

        "last_action": "",

        "final_message": "",

        "exhausted": False,
    }

    started = (
        perf_counter()
    )

    try:
        result = (
            PLANPILOT_GRAPH.invoke(
                initial_state
            )
        )

    except Exception as exc:
        total_duration_ms = (
            (
                perf_counter()
                - started
            )
            * 1000
        )

        TRACE_STORE.finish_trace(
            trace_id=trace_id,
            status="error",
            total_duration_ms=(
                total_duration_ms
            ),
            metadata={
                "error": str(
                    exc
                ),
            },
        )

        raise

    total_duration_ms = (
        (
            perf_counter()
            - started
        )
        * 1000
    )

    has_usable = (
        result.get(
            "has_usable_plan",
            False,
        )
    )

    exhausted = (
        result.get(
            "exhausted",
            False,
        )
    )

    trace_status = (
        "success"
        if has_usable
        else "completed"
    )

    TRACE_STORE.finish_trace(
        trace_id=trace_id,
        status=trace_status,
        total_duration_ms=(
            total_duration_ms
        ),
        metadata={
            "has_usable_plan": (
                has_usable
            ),
            "exhausted": (
                exhausted
            ),
            "iteration_count": (
                result.get(
                    "iteration_count",
                    0,
                )
            ),
            "search_count": (
                result.get(
                    "search_count",
                    0,
                )
            ),
            "final_plan_count": (
                len(
                    result.get(
                        "plans",
                        [],
                    )
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
        },
    )

    return result
