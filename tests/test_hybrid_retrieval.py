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
    build_hybrid_rag_context,
    retrieve_context_for_request,
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
            "foodie",
        ],
        must_include=[
            "dinner",
        ],
        food_preferences=[
            "chicken",
        ],
        max_leg_minutes=45,
    )


def make_venue(
    *,
    name: str,
    area: str,
    food_tags: list[str],
    vibe: list[str],
    cost: float,
    latitude: float,
    longitude: float,
) -> Venue:
    return Venue(
        name=name,
        category="restaurant",
        area=area,
        estimated_cost_per_person=(
            cost
        ),
        duration_minutes=90,
        vibe=vibe,
        food_tags=food_tags,
        latitude=latitude,
        longitude=longitude,
        opening_hours=(
            "Mo-Su 11:00-22:00"
        ),
        source="sample",
    )


def make_retriever(
    tmp_path,
) -> PlanPilotRetriever:
    return PlanPilotRetriever(
        persist_directory=str(
            tmp_path
            / "hybrid_chroma"
        ),
        collection_name=(
            "hybrid_test"
        ),
        embedding_provider=(
            DeterministicEmbeddingProvider(
                dimensions=64,
            )
        ),
        prefer_live_embeddings=False,
    )


def test_hybrid_retrieve_returns_reranked_results(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_venue(
                name="Downtown Generic",
                area="Downtown",
                food_tags=[
                    "vegetarian",
                ],
                vibe=[
                    "indoor",
                ],
                cost=55,
                latitude=42.3600,
                longitude=-71.0600,
            ),
            make_venue(
                name="Back Bay Chicken",
                area="Back Bay",
                food_tags=[
                    "chicken options",
                ],
                vibe=[
                    "chill",
                    "foodie",
                ],
                cost=30,
                latitude=42.3500,
                longitude=-71.0800,
            ),
        ]
    )

    ranked = (
        retriever.retrieve_hybrid(
            query=(
                "chill chicken dinner"
            ),
            request=(
                make_request()
            ),
            limit=2,
            category="restaurant",
            start_coordinates=(
                42.3493,
                -71.0810,
            ),
        )
    )

    assert (
        len(ranked)
        == 2
    )

    assert (
        ranked[
            0
        ].result.metadata[
            "name"
        ]
        == "Back Bay Chicken"
    )

    assert (
        ranked[
            0
        ].final_score
        >= ranked[
            1
        ].final_score
    )


def test_hybrid_retrieve_preserves_explainability(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_venue(
                name="Back Bay Chicken",
                area="Back Bay",
                food_tags=[
                    "chicken",
                ],
                vibe=[
                    "chill",
                    "foodie",
                ],
                cost=30,
                latitude=42.3500,
                longitude=-71.0800,
            )
        ]
    )

    ranked = (
        retriever.retrieve_hybrid(
            query="chicken dinner",
            request=(
                make_request()
            ),
            limit=1,
            category="restaurant",
            start_coordinates=(
                42.3493,
                -71.0810,
            ),
        )
    )

    first = ranked[
        0
    ]

    assert (
        first.breakdown.food
        == 1.0
    )

    assert (
        first.breakdown.area
        == 1.0
    )

    assert (
        first.breakdown.proximity
        >= 0.8
    )

    assert (
        first.reasons
    )


def test_hybrid_context_contains_scores(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_venue(
                name="Back Bay Chicken",
                area="Back Bay",
                food_tags=[
                    "chicken",
                ],
                vibe=[
                    "chill",
                ],
                cost=30,
                latitude=42.3500,
                longitude=-71.0800,
            )
        ]
    )

    ranked = (
        retriever.retrieve_hybrid(
            query="chill chicken",
            request=(
                make_request()
            ),
            limit=1,
            category="restaurant",
            start_coordinates=(
                42.3493,
                -71.0810,
            ),
        )
    )

    context = (
        build_hybrid_rag_context(
            query="chill chicken",
            reranked_results=ranked,
        )
    )

    assert (
        "Hybrid score:"
        in context
    )

    assert (
        "Score breakdown:"
        in context
    )

    assert (
        "Back Bay Chicken"
        in context
    )


def test_complete_request_context_uses_hybrid_by_default(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_venue(
                name="Back Bay Chicken",
                area="Back Bay",
                food_tags=[
                    "chicken",
                ],
                vibe=[
                    "chill",
                    "foodie",
                ],
                cost=30,
                latitude=42.3500,
                longitude=-71.0800,
            )
        ]
    )

    context = (
        retrieve_context_for_request(
            retriever=retriever,
            user_message=(
                "Plan a chill chicken "
                "dinner."
            ),
            request=(
                make_request()
            ),
            limit=1,
            category="restaurant",
            start_coordinates=(
                42.3493,
                -71.0810,
            ),
        )
    )

    assert (
        len(
            context.results
        )
        == 1
    )

    assert (
        len(
            context.reranked_results
        )
        == 1
    )

    assert (
        "hybrid-retrieved"
        in context.context_text
    )


def test_semantic_only_mode_remains_available(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    retriever.ingest_venues(
        [
            make_venue(
                name="Semantic Venue",
                area="Downtown",
                food_tags=[
                    "chicken",
                ],
                vibe=[
                    "chill",
                ],
                cost=30,
                latitude=42.3600,
                longitude=-71.0600,
            )
        ]
    )

    context = (
        retrieve_context_for_request(
            retriever=retriever,
            user_message=(
                "chicken dinner"
            ),
            request=(
                make_request()
            ),
            limit=1,
            use_hybrid_reranking=False,
        )
    )

    assert (
        len(
            context.results
        )
        == 1
    )

    assert (
        context.reranked_results
        == []
    )

    assert (
        "PlanPilot retrieved "
        "venue context"
        in context.context_text
    )


def test_hybrid_candidate_limit_can_exceed_final_limit(
    tmp_path,
) -> None:
    retriever = (
        make_retriever(
            tmp_path
        )
    )

    venues = [
        make_venue(
            name=(
                f"Venue {index}"
            ),
            area=(
                "Back Bay"
                if index == 4
                else "Downtown"
            ),
            food_tags=(
                [
                    "chicken",
                ]
                if index == 4
                else [
                    "vegetarian",
                ]
            ),
            vibe=(
                [
                    "chill",
                    "foodie",
                ]
                if index == 4
                else [
                    "indoor",
                ]
            ),
            cost=(
                25
                if index == 4
                else 50
            ),
            latitude=(
                42.3500
                if index == 4
                else 42.3600
            ),
            longitude=(
                -71.0800
                if index == 4
                else -71.0600
            ),
        )
        for index
        in range(5)
    ]

    retriever.ingest_venues(
        venues
    )

    ranked = (
        retriever.retrieve_hybrid(
            query="restaurant",
            request=(
                make_request()
            ),
            limit=2,
            candidate_limit=5,
            start_coordinates=(
                42.3493,
                -71.0810,
            ),
        )
    )

    assert (
        len(ranked)
        == 2
    )

    assert (
        ranked[
            0
        ].result.metadata[
            "name"
        ]
        == "Venue 4"
    )
