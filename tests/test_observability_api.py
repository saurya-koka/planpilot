from __future__ import annotations

from fastapi.testclient import (
    TestClient,
)

from backend.app.main import (
    app,
)
from backend.app.observability import (
    TRACE_STORE,
    TraceEvent,
)


client = TestClient(
    app
)


def test_list_traces_empty() -> None:
    TRACE_STORE.clear()

    response = client.get(
        "/traces"
    )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload[
            "count"
        ]
        == 0
    )

    assert (
        payload[
            "traces"
        ]
        == []
    )


def test_list_traces_returns_recent_trace() -> None:
    TRACE_STORE.clear()

    trace = (
        TRACE_STORE.start_trace(
            metadata={
                "city": (
                    "Boston"
                )
            }
        )
    )

    TRACE_STORE.finish_trace(
        trace_id=(
            trace.trace_id
        ),
        status="success",
        total_duration_ms=25.5,
    )

    response = client.get(
        "/traces"
    )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload[
            "count"
        ]
        == 1
    )

    saved = (
        payload[
            "traces"
        ][
            0
        ]
    )

    assert (
        saved[
            "trace_id"
        ]
        == trace.trace_id
    )

    assert (
        saved[
            "status"
        ]
        == "success"
    )

    assert (
        saved[
            "metadata"
        ][
            "city"
        ]
        == "Boston"
    )


def test_get_trace_by_id() -> None:
    TRACE_STORE.clear()

    trace = (
        TRACE_STORE.start_trace()
    )

    TRACE_STORE.add_event(
        trace_id=(
            trace.trace_id
        ),
        event=TraceEvent(
            name="build_plans",
            status="success",
            started_at=(
                trace.started_at
            ),
            duration_ms=12.5,
            metadata={
                "has_usable_plan": (
                    True
                )
            },
        ),
    )

    TRACE_STORE.finish_trace(
        trace_id=(
            trace.trace_id
        ),
        status="success",
        total_duration_ms=20.0,
    )

    response = client.get(
        (
            "/traces/"
            f"{trace.trace_id}"
        )
    )

    assert (
        response.status_code
        == 200
    )

    payload = (
        response.json()
    )

    assert (
        payload[
            "trace_id"
        ]
        == trace.trace_id
    )

    assert (
        len(
            payload[
                "events"
            ]
        )
        == 1
    )

    assert (
        payload[
            "events"
        ][
            0
        ][
            "name"
        ]
        == "build_plans"
    )


def test_get_unknown_trace_returns_404() -> None:
    TRACE_STORE.clear()

    response = client.get(
        "/traces/not-a-real-trace"
    )

    assert (
        response.status_code
        == 404
    )

    assert (
        response.json()[
            "detail"
        ]
        == "Trace not found."
    )


def test_clear_traces() -> None:
    TRACE_STORE.clear()

    TRACE_STORE.start_trace()

    assert (
        len(
            TRACE_STORE.latest()
        )
        == 1
    )

    response = client.delete(
        "/traces"
    )

    assert (
        response.status_code
        == 200
    )

    assert (
        response.json()
        == {
            "status": (
                "cleared"
            )
        }
    )

    assert (
        TRACE_STORE.latest()
        == []
    )


def test_trace_limit_validation() -> None:
    TRACE_STORE.clear()

    response = client.get(
        "/traces?limit=0"
    )

    assert (
        response.status_code
        == 422
    )

    response = client.get(
        "/traces?limit=101"
    )

    assert (
        response.status_code
        == 422
    )
