from __future__ import annotations

from backend.app.observability import (
    TRACE_STORE,
    TraceEvent,
    TraceStore,
    generate_trace_id,
    traced_node,
)


def test_generate_trace_id_is_unique() -> None:
    first = (
        generate_trace_id()
    )

    second = (
        generate_trace_id()
    )

    assert first
    assert second
    assert first != second


def test_trace_store_records_trace() -> None:
    store = TraceStore(
        max_traces=5
    )

    trace = store.start_trace(
        metadata={
            "city": (
                "Boston"
            )
        }
    )

    store.add_event(
        trace_id=(
            trace.trace_id
        ),
        event=TraceEvent(
            name="test",
            status="success",
            started_at=(
                trace.started_at
            ),
            duration_ms=12.5,
        ),
    )

    store.finish_trace(
        trace_id=(
            trace.trace_id
        ),
        status="success",
        total_duration_ms=20.0,
    )

    saved = store.get_trace(
        trace.trace_id
    )

    assert saved is not None

    assert (
        saved.status
        == "success"
    )

    assert (
        saved.total_duration_ms
        == 20.0
    )

    assert (
        len(
            saved.events
        )
        == 1
    )

    assert (
        saved.events[
            0
        ].name
        == "test"
    )


def test_trace_store_trims_old_traces() -> None:
    store = TraceStore(
        max_traces=2
    )

    first = (
        store.start_trace()
    )

    second = (
        store.start_trace()
    )

    third = (
        store.start_trace()
    )

    assert (
        store.get_trace(
            first.trace_id
        )
        is None
    )

    assert (
        store.get_trace(
            second.trace_id
        )
        is not None
    )

    assert (
        store.get_trace(
            third.trace_id
        )
        is not None
    )


def test_traced_node_records_success() -> None:
    TRACE_STORE.clear()

    trace = (
        TRACE_STORE.start_trace()
    )

    def sample_node(
        state,
    ):
        return {
            "last_action": (
                "Sample completed."
            ),
            "has_usable_plan": (
                True
            ),
        }

    wrapped = traced_node(
        node_name="sample",
        node=sample_node,
    )

    result = wrapped(
        {
            "trace_id": (
                trace.trace_id
            )
        }
    )

    assert (
        result[
            "has_usable_plan"
        ]
        is True
    )

    saved = (
        TRACE_STORE.get_trace(
            trace.trace_id
        )
    )

    assert saved is not None

    assert (
        len(
            saved.events
        )
        == 1
    )

    event = (
        saved.events[
            0
        ]
    )

    assert (
        event.name
        == "sample"
    )

    assert (
        event.status
        == "success"
    )

    assert (
        event.metadata[
            "has_usable_plan"
        ]
        is True
    )


def test_traced_node_records_error() -> None:
    TRACE_STORE.clear()

    trace = (
        TRACE_STORE.start_trace()
    )

    def failing_node(
        state,
    ):
        raise RuntimeError(
            "boom"
        )

    wrapped = traced_node(
        node_name="failure",
        node=failing_node,
    )

    try:
        wrapped(
            {
                "trace_id": (
                    trace.trace_id
                )
            }
        )

    except RuntimeError:
        pass

    saved = (
        TRACE_STORE.get_trace(
            trace.trace_id
        )
    )

    assert saved is not None

    assert (
        len(
            saved.events
        )
        == 1
    )

    event = (
        saved.events[
            0
        ]
    )

    assert (
        event.name
        == "failure"
    )

    assert (
        event.status
        == "error"
    )

    assert (
        event.error
        == "boom"
    )
