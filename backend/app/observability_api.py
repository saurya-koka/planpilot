from __future__ import annotations

from typing import Any

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from .observability import (
    TRACE_STORE,
)


router = APIRouter(
    prefix="/traces",
    tags=[
        "observability",
    ],
)


@router.get("")
def list_traces(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
) -> dict[
    str,
    Any,
]:
    """
    Return the most recent PlanPilot execution traces.
    """

    traces = (
        TRACE_STORE.latest(
            limit=limit
        )
    )

    return {
        "count": (
            len(
                traces
            )
        ),
        "traces": [
            trace.to_dict()
            for trace
            in traces
        ],
    }


@router.get(
    "/{trace_id}"
)
def get_trace(
    trace_id: str,
) -> dict[
    str,
    Any,
]:
    """
    Return one complete PlanPilot execution trace.
    """

    trace = (
        TRACE_STORE.get_trace(
            trace_id
        )
    )

    if trace is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Trace not found."
            ),
        )

    return (
        trace.to_dict()
    )


@router.delete("")
def clear_traces() -> dict[
    str,
    str,
]:
    """
    Clear the in-memory development trace store.
    """

    TRACE_STORE.clear()

    return {
        "status": (
            "cleared"
        )
    }
