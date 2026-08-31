from __future__ import annotations

from dataclasses import (
    asdict,
    dataclass,
    field,
)
from datetime import (
    datetime,
    timezone,
)
from threading import Lock
from time import perf_counter
from typing import (
    Any,
    Callable,
)
from uuid import uuid4


@dataclass
class TraceEvent:
    """
    One observable event within a PlanPilot trace.
    """

    name: str

    status: str

    started_at: str

    duration_ms: float

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    error: str | None = None

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return asdict(
            self
        )


@dataclass
class TraceRecord:
    """
    Complete execution trace for one PlanPilot request.
    """

    trace_id: str

    started_at: str

    completed_at: str | None = None

    total_duration_ms: float = 0.0

    status: str = "running"

    events: list[
        TraceEvent
    ] = field(
        default_factory=list
    )

    metadata: dict[
        str,
        Any,
    ] = field(
        default_factory=dict
    )

    def to_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "trace_id": (
                self.trace_id
            ),
            "started_at": (
                self.started_at
            ),
            "completed_at": (
                self.completed_at
            ),
            "total_duration_ms": (
                self.total_duration_ms
            ),
            "status": (
                self.status
            ),
            "events": [
                event.to_dict()
                for event
                in self.events
            ],
            "metadata": dict(
                self.metadata
            ),
        }


def utc_now_iso() -> str:
    """
    Return a timezone-aware UTC timestamp.
    """

    return (
        datetime.now(
            timezone.utc
        )
        .isoformat()
    )


def generate_trace_id() -> str:
    """
    Generate a stable request trace identifier.
    """

    return (
        uuid4()
        .hex
    )


class TraceStore:
    """
    Small in-memory trace store.

    This is intentionally dependency-free for V2.12.
    A persistent backend or external telemetry system can
    replace it later without changing graph instrumentation.
    """

    def __init__(
        self,
        *,
        max_traces: int = 200,
    ) -> None:
        if max_traces < 1:
            raise ValueError(
                "max_traces must be "
                "at least 1."
            )

        self.max_traces = (
            max_traces
        )

        self._traces: dict[
            str,
            TraceRecord,
        ] = {}

        self._order: list[
            str
        ] = []

        self._lock = (
            Lock()
        )

    def start_trace(
        self,
        *,
        trace_id: str | None = None,
        metadata: (
            dict[str, Any]
            | None
        ) = None,
    ) -> TraceRecord:
        selected_trace_id = (
            trace_id
            or generate_trace_id()
        )

        trace = TraceRecord(
            trace_id=(
                selected_trace_id
            ),
            started_at=(
                utc_now_iso()
            ),
            metadata=dict(
                metadata
                or {}
            ),
        )

        with self._lock:
            self._traces[
                selected_trace_id
            ] = trace

            self._order.append(
                selected_trace_id
            )

            self._trim_locked()

        return trace

    def add_event(
        self,
        *,
        trace_id: str,
        event: TraceEvent,
    ) -> None:
        with self._lock:
            trace = (
                self._traces.get(
                    trace_id
                )
            )

            if trace is None:
                return

            trace.events.append(
                event
            )

    def finish_trace(
        self,
        *,
        trace_id: str,
        status: str,
        total_duration_ms: float,
        metadata: (
            dict[str, Any]
            | None
        ) = None,
    ) -> None:
        with self._lock:
            trace = (
                self._traces.get(
                    trace_id
                )
            )

            if trace is None:
                return

            trace.completed_at = (
                utc_now_iso()
            )

            trace.total_duration_ms = (
                round(
                    total_duration_ms,
                    3,
                )
            )

            trace.status = (
                status
            )

            if metadata:
                trace.metadata.update(
                    metadata
                )

    def get_trace(
        self,
        trace_id: str,
    ) -> TraceRecord | None:
        with self._lock:
            return (
                self._traces.get(
                    trace_id
                )
            )

    def latest(
        self,
        *,
        limit: int = 20,
    ) -> list[
        TraceRecord
    ]:
        if limit < 1:
            return []

        with self._lock:
            selected_ids = (
                self._order[
                    -limit:
                ]
            )

            return [
                self._traces[
                    trace_id
                ]
                for trace_id
                in reversed(
                    selected_ids
                )
                if trace_id
                in self._traces
            ]

    def clear(
        self,
    ) -> None:
        with self._lock:
            self._traces.clear()
            self._order.clear()

    def _trim_locked(
        self,
    ) -> None:
        while (
            len(
                self._order
            )
            > self.max_traces
        ):
            oldest = (
                self._order.pop(
                    0
                )
            )

            self._traces.pop(
                oldest,
                None,
            )


TRACE_STORE = TraceStore()


def build_trace_event(
    *,
    name: str,
    status: str,
    started_at: str,
    duration_ms: float,
    metadata: (
        dict[str, Any]
        | None
    ) = None,
    error: str | None = None,
) -> TraceEvent:
    return TraceEvent(
        name=name,
        status=status,
        started_at=started_at,
        duration_ms=round(
            duration_ms,
            3,
        ),
        metadata=dict(
            metadata
            or {}
        ),
        error=error,
    )


def traced_node(
    *,
    node_name: str,
    node: Callable[
        [dict[str, Any]],
        dict[str, Any],
    ],
) -> Callable[
    [dict[str, Any]],
    dict[str, Any],
]:
    """
    Wrap a LangGraph node with structured timing instrumentation.

    The wrapper reads trace_id from graph state. When tracing is
    unavailable, the original node behavior is preserved.
    """

    def wrapped(
        state: dict[
            str,
            Any,
        ],
    ) -> dict[
        str,
        Any,
    ]:
        trace_id = (
            state.get(
                "trace_id"
            )
        )

        started_at = (
            utc_now_iso()
        )

        started = (
            perf_counter()
        )

        try:
            result = node(
                state
            )

        except Exception as exc:
            duration_ms = (
                (
                    perf_counter()
                    - started
                )
                * 1000
            )

            if trace_id:
                TRACE_STORE.add_event(
                    trace_id=trace_id,
                    event=(
                        build_trace_event(
                            name=node_name,
                            status="error",
                            started_at=(
                                started_at
                            ),
                            duration_ms=(
                                duration_ms
                            ),
                            error=str(
                                exc
                            ),
                        )
                    ),
                )

            raise

        duration_ms = (
            (
                perf_counter()
                - started
            )
            * 1000
        )

        metadata: dict[
            str,
            Any,
        ] = {}

        if isinstance(
            result,
            dict,
        ):
            if (
                "last_action"
                in result
            ):
                metadata[
                    "last_action"
                ] = result[
                    "last_action"
                ]

            if (
                "has_usable_plan"
                in result
            ):
                metadata[
                    "has_usable_plan"
                ] = result[
                    "has_usable_plan"
                ]

            if (
                "search_count"
                in result
            ):
                metadata[
                    "search_count"
                ] = result[
                    "search_count"
                ]

            if (
                "iteration_count"
                in result
            ):
                metadata[
                    "iteration_count"
                ] = result[
                    "iteration_count"
                ]

        if trace_id:
            TRACE_STORE.add_event(
                trace_id=trace_id,
                event=(
                    build_trace_event(
                        name=node_name,
                        status="success",
                        started_at=(
                            started_at
                        ),
                        duration_ms=(
                            duration_ms
                        ),
                        metadata=(
                            metadata
                        ),
                    )
                ),
            )

        return result

    return wrapped
