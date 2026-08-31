from __future__ import annotations

import os
from pathlib import Path

from .embeddings import (
    get_embedding_provider,
)
from .graph_state import (
    PlanPilotGraphState,
)
from .models import (
    Venue,
)
from .rag_retriever import (
    PlanPilotRetriever,
    retrieve_context_for_request,
)


DEFAULT_GRAPH_RAG_PATH = (
    ".planpilot_chroma"
)

DEFAULT_GRAPH_RAG_COLLECTION = (
    "planpilot_graph_venues"
)


def build_graph_retriever(
    *,
    persist_directory: (
        str
        | Path
        | None
    ) = None,
    prefer_live_embeddings: bool = True,
) -> PlanPilotRetriever:
    """
    Build the retriever used by LangGraph.

    Tests run with OPENAI_API_KEY disabled through tests/conftest.py,
    so they automatically use deterministic local embeddings.

    Production can use OpenAI embeddings when configured.
    """

    resolved_directory = (
        persist_directory
        or os.getenv(
            "PLANPILOT_CHROMA_PATH",
            DEFAULT_GRAPH_RAG_PATH,
        )
    )

    provider = (
        get_embedding_provider(
            prefer_live=(
                prefer_live_embeddings
            )
        )
    )

    return PlanPilotRetriever(
        persist_directory=str(
            resolved_directory
        ),
        collection_name=(
            DEFAULT_GRAPH_RAG_COLLECTION
        ),
        embedding_provider=provider,
        prefer_live_embeddings=(
            prefer_live_embeddings
        ),
    )


def venue_match_key(
    venue: Venue,
) -> tuple[
    str,
    str,
]:
    """
    Build a stable in-memory lookup key for retrieved venue ranking.
    """

    return (
        venue.name
        .strip()
        .lower(),
        venue.category,
    )


def prioritize_venues(
    *,
    venues: list[
        Venue
    ],
    ranked_names: list[
        str
    ],
) -> list[
    Venue
]:
    """
    Move hybrid-ranked venues to the front while preserving all
    remaining venues.

    Retrieval therefore influences planning without deleting
    deterministic fallback candidates.
    """

    if (
        not venues
        or not ranked_names
    ):
        return list(
            venues
        )

    rank_lookup = {
        name.strip().lower(): index
        for index, name
        in enumerate(
            ranked_names
        )
    }

    indexed = list(
        enumerate(
            venues
        )
    )

    indexed.sort(
        key=lambda item: (
            rank_lookup.get(
                item[
                    1
                ].name
                .strip()
                .lower(),
                len(
                    rank_lookup
                )
                + item[
                    0
                ],
            )
        )
    )

    return [
        venue
        for _original_index, venue
        in indexed
    ]


def retrieve_rag_context_node(
    state: PlanPilotGraphState,
) -> PlanPilotGraphState:
    """
    Run V2.8 hybrid retrieval for the current LangGraph state.

    Workflow:
        venue pool
            ->
        Chroma semantic recall
            ->
        deterministic structured reranking
            ->
        prioritize graph venue pool

    Structured reranking uses:
    - semantic relevance
    - category
    - food preference
    - vibe
    - area
    - budget
    - geographic proximity
    """

    request = state[
        "request"
    ]

    venues = list(
        state.get(
            "venues",
            [],
        )
    )

    user_message = state.get(
        "user_message",
        "",
    )

    start_coordinates = (
        state.get(
            "start_coordinates"
        )
    )

    if not venues:
        return {
            "rag_query": "",
            "rag_context": (
                "No venue knowledge "
                "was available for "
                "retrieval."
            ),
            "rag_result_count": 0,
            "rag_document_ids": [],
            "rag_ranked_venue_names": [],
            "rag_used": False,
            "last_action": (
                "Hybrid retrieval skipped "
                "because the venue pool "
                "was empty."
            ),
        }

    try:
        retriever = (
            build_graph_retriever()
        )

        retriever.ingest_venues(
            venues
        )

        context = (
            retrieve_context_for_request(
                retriever=retriever,
                user_message=(
                    user_message
                ),
                request=request,
                limit=min(
                    8,
                    len(
                        venues
                    ),
                ),
                start_coordinates=(
                    start_coordinates
                ),
                use_hybrid_reranking=True,
            )
        )

    except Exception as exc:
        return {
            "rag_query": "",
            "rag_context": (
                "Hybrid RAG retrieval "
                "was unavailable."
            ),
            "rag_result_count": 0,
            "rag_document_ids": [],
            "rag_ranked_venue_names": [],
            "rag_used": False,
            "last_action": (
                "Hybrid RAG retrieval "
                "failed: "
                f"{exc}"
            ),
        }

    ranked_names: list[
        str
    ] = []

    document_ids: list[
        str
    ] = []

    for result in context.results:
        document_ids.append(
            result.document_id
        )

        name = (
            result.metadata.get(
                "name"
            )
        )

        if isinstance(
            name,
            str,
        ):
            ranked_names.append(
                name
            )

    prioritized = (
        prioritize_venues(
            venues=venues,
            ranked_names=(
                ranked_names
            ),
        )
    )

    return {
        "venues": prioritized,
        "rag_query": (
            context.query
        ),
        "rag_context": (
            context.context_text
        ),
        "rag_result_count": len(
            context.results
        ),
        "rag_document_ids": (
            document_ids
        ),
        "rag_ranked_venue_names": (
            ranked_names
        ),
        "rag_used": bool(
            context.results
        ),
        "last_action": (
            "Hybrid RAG retrieved and "
            f"reranked {len(context.results)} "
            "venue document(s)."
        ),
    }
