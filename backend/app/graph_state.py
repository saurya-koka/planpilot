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

    # ------------------------------------------------------------------
    # V2.12 observability state
    # ------------------------------------------------------------------

    trace_id: str

    # ------------------------------------------------------------------
    # Core request state
    # ------------------------------------------------------------------

    user_message: str

    request: PlanRequest

    venues: list[
        Venue
    ]

    plans: list[
        Itinerary
    ]

    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    )

    selected_plan_index: int

    has_usable_plan: bool

    iteration_count: int

    max_iterations: int

    searched_categories: list[
        str
    ]

    search_count: int

    # ------------------------------------------------------------------
    # V2.8 hybrid RAG state
    # ------------------------------------------------------------------

    rag_query: str

    rag_context: str

    rag_result_count: int

    rag_document_ids: list[
        str
    ]

    rag_ranked_venue_names: list[
        str
    ]

    rag_used: bool

    # ------------------------------------------------------------------
    # V2.9 weather state
    # ------------------------------------------------------------------

    weather_checked: bool

    weather_condition: str

    weather_temperature_c: float

    weather_precipitation_probability: float

    weather_wind_speed_kph: float

    weather_risk_level: str

    weather_outdoor_safe: bool

    weather_reasons: list[
        str
    ]

    weather_source: str

    # Whether weather caused the working venue pool to change.
    weather_adjusted: bool

    # Number of candidates before weather adaptation.
    weather_original_venue_count: int

    # Number of candidates after weather adaptation.
    weather_filtered_venue_count: int

    # Outdoor candidates removed because weather was unsafe.
    weather_removed_venue_names: list[
        str
    ]

    # ------------------------------------------------------------------
    # Graph execution summary
    # ------------------------------------------------------------------

    last_action: str

    final_message: str

    exhausted: bool
