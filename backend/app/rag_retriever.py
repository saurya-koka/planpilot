from __future__ import annotations

from dataclasses import (
    dataclass,
)

from .embeddings import (
    EmbeddingProvider,
)
from .models import (
    PlanRequest,
    Venue,
)
from .rag_documents import (
    venues_to_vector_documents,
)
from .reranker import (
    RerankedResult,
    rerank_results,
)
from .vector_store import (
    PlanPilotVectorStore,
    RetrievalResult,
)


DEFAULT_RETRIEVAL_CANDIDATE_MULTIPLIER = 3
DEFAULT_MAX_RETRIEVAL_CANDIDATES = 20


@dataclass
class RetrievalContext:
    """
    Final RAG result consumed by PlanPilot orchestration.

    results:
        Final retrieval order consumed by the graph.

    reranked_results:
        Explainable hybrid-scored records used to produce that order.
    """

    query: str

    results: list[
        RetrievalResult
    ]

    context_text: str

    reranked_results: list[
        RerankedResult
    ]


class PlanPilotRetriever:
    """
    High-level retrieval layer for PlanPilot.

    Responsibilities:
    - ingest normalized Venue objects
    - perform semantic retrieval
    - optionally filter by venue category
    - perform hybrid semantic + structured reranking
    - build compact RAG context text
    """

    def __init__(
        self,
        *,
        persist_directory: str,
        collection_name: str = (
            "planpilot_venues"
        ),
        embedding_provider: (
            EmbeddingProvider
            | None
        ) = None,
        prefer_live_embeddings: bool = True,
    ) -> None:
        self.store = (
            PlanPilotVectorStore(
                persist_directory=(
                    persist_directory
                ),
                collection_name=(
                    collection_name
                ),
                embedding_provider=(
                    embedding_provider
                ),
                prefer_live_embeddings=(
                    prefer_live_embeddings
                ),
            )
        )

    def count(
        self,
    ) -> int:
        return self.store.count()

    def ingest_venues(
        self,
        venues: list[
            Venue
        ],
    ) -> int:
        """
        Convert venues into vector documents and upsert them.
        """

        documents = (
            venues_to_vector_documents(
                venues
            )
        )

        return (
            self.store
            .upsert_documents(
                documents
            )
        )

    def retrieve(
        self,
        *,
        query: str,
        limit: int = 5,
        category: (
            str
            | None
        ) = None,
    ) -> list[
        RetrievalResult
    ]:
        """
        Retrieve semantically relevant venue documents.

        This preserves the original V2.7 raw semantic-retrieval API.
        """

        where = None

        if category:
            where = {
                "category": (
                    category
                ),
            }

        return (
            self.store.query(
                query_text=query,
                limit=limit,
                where=where,
            )
        )

    def retrieve_hybrid(
        self,
        *,
        query: str,
        request: PlanRequest,
        limit: int = 5,
        category: (
            str
            | None
        ) = None,
        start_coordinates: (
            tuple[
                float,
                float,
            ]
            | None
        ) = None,
        candidate_limit: (
            int
            | None
        ) = None,
    ) -> list[
        RerankedResult
    ]:
        """
        Retrieve a broader semantic candidate set and rerank it using
        deterministic PlanPilot constraints.

        The semantic search remains the recall stage.

        The deterministic reranker becomes the precision stage.
        """

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        if candidate_limit is None:
            candidate_limit = min(
                DEFAULT_MAX_RETRIEVAL_CANDIDATES,
                max(
                    limit,
                    (
                        limit
                        * DEFAULT_RETRIEVAL_CANDIDATE_MULTIPLIER
                    ),
                ),
            )

        if candidate_limit < limit:
            candidate_limit = limit

        semantic_results = (
            self.retrieve(
                query=query,
                limit=candidate_limit,
                category=category,
            )
        )

        return rerank_results(
            results=semantic_results,
            request=request,
            desired_category=(
                category
            ),
            start_coordinates=(
                start_coordinates
            ),
            limit=limit,
        )

    def clear(
        self,
    ) -> None:
        self.store.delete_all()


def build_request_query(
    *,
    user_message: str,
    request: PlanRequest,
) -> str:
    """
    Build a semantic retrieval query from the original request and
    structured planning fields.
    """

    parts: list[
        str
    ] = []

    if user_message.strip():
        parts.append(
            user_message.strip()
        )

    parts.append(
        f"City: {request.city}."
    )

    parts.append(
        (
            "Starting area: "
            f"{request.start_area}."
        )
    )

    if request.vibe:
        parts.append(
            (
                "Vibe: "
                f"{', '.join(request.vibe)}."
            )
        )

    if request.food_preferences:
        parts.append(
            (
                "Food preferences: "
                f"{', '.join(request.food_preferences)}."
            )
        )

    if request.must_include:
        parts.append(
            (
                "Must include: "
                f"{', '.join(request.must_include)}."
            )
        )

    parts.append(
        (
            "Budget: "
            f"{request.budget_total:.0f} "
            "dollars total."
        )
    )

    parts.append(
        (
            "Party size: "
            f"{request.party_size}."
        )
    )

    parts.append(
        (
            "Transport: "
            f"{request.transport}."
        )
    )

    return " ".join(
        parts
    )


def format_retrieval_result(
    *,
    result: RetrievalResult,
    rank: int,
) -> str:
    """
    Convert one raw semantic retrieval hit into compact
    model-readable context.
    """

    metadata = (
        result.metadata
    )

    name = (
        metadata.get(
            "name",
            result.document_id,
        )
    )

    category = (
        metadata.get(
            "category",
            "unknown",
        )
    )

    area = (
        metadata.get(
            "area",
            "unknown",
        )
    )

    cost = (
        metadata.get(
            "estimated_cost_per_person"
        )
    )

    lines = [
        (
            f"[{rank}] "
            f"{name}"
        ),
        (
            "Category: "
            f"{category}"
        ),
        (
            "Area: "
            f"{area}"
        ),
    ]

    if cost is not None:
        lines.append(
            (
                "Estimated cost per "
                f"person: ${cost}"
            )
        )

    if result.distance is not None:
        lines.append(
            (
                "Vector distance: "
                f"{result.distance:.4f}"
            )
        )

    lines.append(
        (
            "Context: "
            f"{result.text}"
        )
    )

    return "\n".join(
        lines
    )


def format_reranked_result(
    *,
    reranked: RerankedResult,
    rank: int,
) -> str:
    """
    Convert one hybrid-ranked venue into explainable model context.
    """

    result = (
        reranked.result
    )

    metadata = (
        result.metadata
        or {}
    )

    name = (
        metadata.get(
            "name",
            result.document_id,
        )
    )

    category = (
        metadata.get(
            "category",
            "unknown",
        )
    )

    area = (
        metadata.get(
            "area",
            "unknown",
        )
    )

    cost = (
        metadata.get(
            "estimated_cost_per_person"
        )
    )

    breakdown = (
        reranked.breakdown
    )

    lines = [
        (
            f"[{rank}] "
            f"{name}"
        ),
        (
            "Category: "
            f"{category}"
        ),
        (
            "Area: "
            f"{area}"
        ),
        (
            "Hybrid score: "
            f"{reranked.final_score:.4f}"
        ),
        (
            "Score breakdown: "
            f"semantic={breakdown.semantic:.3f}, "
            f"category={breakdown.category:.3f}, "
            f"food={breakdown.food:.3f}, "
            f"vibe={breakdown.vibe:.3f}, "
            f"area={breakdown.area:.3f}, "
            f"budget={breakdown.budget:.3f}, "
            f"proximity={breakdown.proximity:.3f}"
        ),
    ]

    if cost is not None:
        lines.append(
            (
                "Estimated cost per "
                f"person: ${cost}"
            )
        )

    if result.distance is not None:
        lines.append(
            (
                "Vector distance: "
                f"{result.distance:.4f}"
            )
        )

    if reranked.reasons:
        lines.append(
            (
                "Ranking reasons: "
                f"{', '.join(reranked.reasons)}"
            )
        )

    lines.append(
        (
            "Context: "
            f"{result.text}"
        )
    )

    return "\n".join(
        lines
    )


def build_rag_context(
    *,
    query: str,
    results: list[
        RetrievalResult
    ],
) -> str:
    """
    Build the original V2.7 semantic-only context block.

    Kept for backwards compatibility and isolated semantic tests.
    """

    if not results:
        return (
            "No relevant PlanPilot "
            "knowledge was retrieved."
        )

    sections = [
        (
            "PlanPilot retrieved "
            "venue context"
        ),
        (
            "Query: "
            f"{query}"
        ),
    ]

    for rank, result in enumerate(
        results,
        start=1,
    ):
        sections.append(
            format_retrieval_result(
                result=result,
                rank=rank,
            )
        )

    return "\n\n".join(
        sections
    )


def build_hybrid_rag_context(
    *,
    query: str,
    reranked_results: list[
        RerankedResult
    ],
) -> str:
    """
    Build the V2.8 hybrid retrieval context.

    The final order is determined by semantic recall followed by
    structured deterministic reranking.
    """

    if not reranked_results:
        return (
            "No relevant PlanPilot "
            "knowledge was retrieved."
        )

    sections = [
        (
            "PlanPilot hybrid-retrieved "
            "venue context"
        ),
        (
            "Query: "
            f"{query}"
        ),
        (
            "Ranking method: semantic retrieval "
            "plus deterministic constraint reranking."
        ),
    ]

    for rank, reranked in enumerate(
        reranked_results,
        start=1,
    ):
        sections.append(
            format_reranked_result(
                reranked=reranked,
                rank=rank,
            )
        )

    return "\n\n".join(
        sections
    )


def retrieve_context_for_request(
    *,
    retriever: PlanPilotRetriever,
    user_message: str,
    request: PlanRequest,
    limit: int = 5,
    category: (
        str
        | None
    ) = None,
    start_coordinates: (
        tuple[
            float,
            float,
        ]
        | None
    ) = None,
    use_hybrid_reranking: bool = True,
) -> RetrievalContext:
    """
    Run the complete RAG retrieval workflow for one planning request.

    V2.8 defaults to hybrid retrieval:
        semantic recall
            ->
        deterministic structured reranking
            ->
        final RAG context

    The semantic-only path is preserved for backwards compatibility.
    """

    query = build_request_query(
        user_message=(
            user_message
        ),
        request=request,
    )

    if use_hybrid_reranking:
        reranked_results = (
            retriever.retrieve_hybrid(
                query=query,
                request=request,
                limit=limit,
                category=category,
                start_coordinates=(
                    start_coordinates
                ),
            )
        )

        results = [
            item.result
            for item
            in reranked_results
        ]

        context_text = (
            build_hybrid_rag_context(
                query=query,
                reranked_results=(
                    reranked_results
                ),
            )
        )

    else:
        results = (
            retriever.retrieve(
                query=query,
                limit=limit,
                category=category,
            )
        )

        reranked_results = []

        context_text = (
            build_rag_context(
                query=query,
                results=results,
            )
        )

    return RetrievalContext(
        query=query,
        results=results,
        context_text=(
            context_text
        ),
        reranked_results=(
            reranked_results
        ),
    )
