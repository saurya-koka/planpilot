from __future__ import annotations

from backend.app.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.models import (
    PlanRequest,
    Venue,
)
from backend.app.rag_retriever import (
    PlanPilotRetriever,
    build_rag_context,
    build_request_query,
    retrieve_context_for_request,
)


def make_retriever(
    tmp_path,
) -> PlanPilotRetriever:
    return PlanPilotRetriever(
        persist_directory=str(
            tmp_path
            / "rag_chroma"
        ),
        collection_name=(
            "test_rag"
        ),
        embedding_provider=(
            DeterministicEmbeddingProvider(
                dimensions=64,
            )
        ),
        prefer_live_embeddings=False,
    )


def make_restaurant() -> Venue:
    return Venue(
        name="Chill Chicken Spot",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=75,
        vibe=[
            "chill",
            "casual",
        ],
        food_tags=[
            "chicken",
        ],
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours=(
            "Mo-Su 11:00-22:00"
        ),
        source="sample",
    )


def make_activity() -> Venue:
    return Venue(
        name="Indoor Museum",
        category="activity",
        area="Downtown",
        estimated_cost_per_person=20,
        duration_minutes=90,
        vibe=[
            "calm",
            "indoor",
        ],
        food_tags=[],
        latitude=42.3600,
        longitude=-71.0600,
        opening_hours=(
            "Mo-Su 10:00-18:00"
        ),
        source="sample",
    )


def make_request() -> PlanRequest:
    return PlanRequest(
        city="Boston",
        start_area="Back Bay",
        date="Friday",
        start_time="18:00",
        budget_total=120,
        party_size=2,
        transport="walking",
        vibe=[
            "chill",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=45,
    )


def test_retriever_ingests_venues(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    count = (
        retriever.ingest_venues(
            [
                make_restaurant(),
                make_activity(),
            ]
        )
    )

    assert (
        count
        == 2
    )

    assert (
        retriever.count()
        == 2
    )


def test_retriever_returns_relevant_restaurant(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_restaurant(),
            make_activity(),
        ]
    )

    results = retriever.retrieve(
        query=(
            "chill chicken "
            "restaurant"
        ),
        limit=1,
    )

    assert (
        len(results)
        == 1
    )

    assert (
        results[
            0
        ].metadata[
            "category"
        ]
        == "restaurant"
    )


def test_retriever_category_filter(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_restaurant(),
            make_activity(),
        ]
    )

    results = retriever.retrieve(
        query="chill",
        limit=5,
        category="activity",
    )

    assert (
        len(results)
        == 1
    )

    assert (
        results[
            0
        ].metadata[
            "category"
        ]
        == "activity"
    )


def test_request_query_contains_constraints() -> None:
    request = make_request()

    query = build_request_query(
        user_message=(
            "Find somewhere chill."
        ),
        request=request,
    )

    lowered = (
        query.lower()
    )

    assert (
        "back bay"
        in lowered
    )

    assert (
        "chicken"
        in lowered
    )

    assert (
        "120"
        in lowered
    )

    assert (
        "walking"
        in lowered
    )


def test_context_builder_contains_ranked_result(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_restaurant(),
        ]
    )

    results = (
        retriever.retrieve(
            query=(
                "chill chicken"
            ),
            limit=1,
        )
    )

    context = (
        build_rag_context(
            query=(
                "chill chicken"
            ),
            results=results,
        )
    )

    assert (
        "[1]"
        in context
    )

    assert (
        "Chill Chicken Spot"
        in context
    )

    assert (
        "restaurant"
        in context
    )


def test_complete_retrieval_context_workflow(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_restaurant(),
            make_activity(),
        ]
    )

    request = make_request()

    context = (
        retrieve_context_for_request(
            retriever=retriever,
            user_message=(
                "Plan a chill chicken "
                "dinner."
            ),
            request=request,
            limit=2,
        )
    )

    assert (
        context.query
    )

    assert (
        context.results
    )

    assert (
    	"PlanPilot hybrid-retrieved "
    	"venue context"
    	in context.context_text
	)

    assert (
        "Chill Chicken Spot"
        in context.context_text
    )


def test_clear_removes_retrieval_documents(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_restaurant(),
        ]
    )

    assert (
        retriever.count()
        == 1
    )

    retriever.clear()

    assert (
        retriever.count()
        == 0
    )
