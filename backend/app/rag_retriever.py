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
from .vector_store import (
    PlanPilotVectorStore,
    RetrievalResult,
)


@dataclass
class RetrievalContext:
    """
    Final RAG result consumed by PlanPilot orchestration.
    """

    query: str

    results: list[
        RetrievalResult
    ]

    context_text: str


class PlanPilotRetriever:
    """
    High-level retrieval layer for PlanPilot.

    Responsibilities:
    - ingest normalized Venue objects
    - perform semantic retrieval
    - optionally filter by venue category
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
    Convert one retrieval hit into compact model-readable context.
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


def build_rag_context(
    *,
    query: str,
    results: list[
        RetrievalResult
    ],
) -> str:
    """
    Build a bounded textual RAG context block.
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
) -> RetrievalContext:
    """
    Run the complete RAG retrieval workflow for one planning request.
    """

    query = build_request_query(
        user_message=(
            user_message
        ),
        request=request,
    )

    results = (
        retriever.retrieve(
            query=query,
            limit=limit,
            category=category,
        )
    )

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
    )
