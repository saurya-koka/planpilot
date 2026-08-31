from __future__ import annotations

from backend.app.graph_orchestrator import (
    run_planpilot_graph,
)
from backend.app.models import (
    PlanRequest,
    Venue,
)
from backend.app.observability import (
    TRACE_STORE,
)


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="17:00",
        budget_total=250,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[],
        max_leg_minutes=45,
    )


def make_venue() -> Venue:
    return Venue(
        name="Observable Restaurant",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=40,
        duration_minutes=60,
        vibe=[
            "chill",
        ],
        food_tags=[],
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours=(
            "Mo-Su 16:00-23:00"
        ),
        source="sample",
    )


def test_graph_execution_creates_trace() -> None:
    TRACE_STORE.clear()

    result = (
        run_planpilot_graph(
            user_message=(
                "Plan a chill dinner."
            ),
            request=make_request(),
            venues=[
                make_venue(),
            ],
            start_coordinates=None,
            max_iterations=4,
        )
    )

    trace_id = (
        result.get(
            "trace_id"
        )
    )

    assert trace_id

    trace = (
        TRACE_STORE.get_trace(
            trace_id
        )
    )

    assert trace is not None

    assert (
        trace.status
        == "success"
    )

    assert (
        trace.total_duration_ms
        >= 0
    )

    assert (
        trace.metadata[
            "has_usable_plan"
        ]
        is True
    )


def test_graph_trace_contains_core_nodes() -> None:
    TRACE_STORE.clear()

    result = (
        run_planpilot_graph(
            user_message=(
                "Plan a chill dinner."
            ),
            request=make_request(),
            venues=[
                make_venue(),
            ],
            start_coordinates=None,
            max_iterations=4,
        )
    )

    trace = (
        TRACE_STORE.get_trace(
            result[
                "trace_id"
            ]
        )
    )

    assert trace is not None

    event_names = [
        event.name
        for event
        in trace.events
    ]

    assert (
        "initialize"
        in event_names
    )

    assert (
        "weather"
        in event_names
    )

    assert (
        "weather_constraints"
        in event_names
    )

    assert (
        "retrieve"
        in event_names
    )

    assert (
        "build_plans"
        in event_names
    )

    assert (
        "validate"
        in event_names
    )

    assert (
        "finish"
        in event_names
    )


def test_graph_trace_records_summary_metadata() -> None:
    TRACE_STORE.clear()

    result = (
        run_planpilot_graph(
            user_message=(
                "Plan a chill dinner."
            ),
            request=make_request(),
            venues=[
                make_venue(),
            ],
            start_coordinates=None,
            max_iterations=4,
        )
    )

    trace = (
        TRACE_STORE.get_trace(
            result[
                "trace_id"
            ]
        )
    )

    assert trace is not None

    assert (
        trace.metadata[
            "city"
        ]
        == "Boston"
    )

    assert (
        trace.metadata[
            "start_area"
        ]
        == "Back Bay"
    )

    assert (
        trace.metadata[
            "final_plan_count"
        ]
        >= 1
    )

    assert (
        trace.metadata[
            "search_count"
        ]
        == 0
    )

    assert (
        "rag_used"
        in trace.metadata
    )

    assert (
        isinstance(
            trace.metadata[
                "rag_used"
            ],
            bool,
        )
    )

    assert (
        "rag_result_count"
        in trace.metadata
    )

    assert (
        trace.metadata[
            "rag_result_count"
        ]
        >= 0
    )

    assert (
        "weather_checked"
        in trace.metadata
    )

    assert (
        isinstance(
            trace.metadata[
                "weather_checked"
            ],
            bool,
        )
    )

    assert (
        "weather_adjusted"
        in trace.metadata
    )

    assert (
        isinstance(
            trace.metadata[
                "weather_adjusted"
            ],
            bool,
        )
    )
