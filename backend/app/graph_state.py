from __future__ import annotations

from typing import TypedDict

from .models import (
    Itinerary,
    PlanRequest,
    Venue,
)


class PlanPilotGraphState(
    TypedDict,
    total=False,
):
    """
    Shared LangGraph state for one PlanPilot orchestration run.

    Nodes read from this state and return only the fields they want
    to update.
    """

    # Original natural-language request.
    user_message: str

    # Structured request consumed by the planner.
    request: PlanRequest

    # Current working venue pool.
    venues: list[
        Venue
    ]

    # Current itinerary candidates.
    plans: list[
        Itinerary
    ]

    # Optional geocoded starting point.
    start_coordinates: (
        tuple[float, float]
        | None
    )

    # Candidate currently selected for repair.
    selected_plan_index: int

    # True when at least one itinerary has no hard validation errors.
    has_usable_plan: bool

    # Number of repair iterations completed.
    iteration_count: int

    # Maximum repair iterations allowed.
    max_iterations: int

    # Categories already searched during this graph execution.
    searched_categories: list[
        str
    ]

    # Number of live venue-search operations attempted.
    search_count: int

    # Human-readable description of the most recent graph action.
    last_action: str

    # Final graph result message.
    final_message: str

    # True when the graph stopped because its repair budget was used.
    exhausted: bool
