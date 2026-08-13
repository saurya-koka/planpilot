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

    # Structured planner request.
    request: PlanRequest

    # Current working venue pool.
    venues: list[
        Venue
    ]

    # Current itinerary candidates.
    plans: list[
        Itinerary
    ]

    # Optional geocoded start point.
    start_coordinates: (
        tuple[float, float]
        | None
    )

    # Candidate currently selected for repair.
    selected_plan_index: int

    # True when at least one candidate has no hard validation errors.
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

    # RAG semantic retrieval query.
    rag_query: str

    # Final model-readable retrieved context.
    rag_context: str

    # Number of semantic retrieval hits.
    rag_result_count: int

    # IDs of retrieved vector documents.
    rag_document_ids: list[
        str
    ]

    # Venue names ranked by semantic retrieval.
    rag_ranked_venue_names: list[
        str
    ]

    # Whether RAG retrieval executed successfully.
    rag_used: bool

    # Human-readable description of the most recent graph action.
    last_action: str

    # Final graph result message.
    final_message: str

    # True when graph stopped because its bounded repair budget
    # was exhausted.
    exhausted: bool
