from __future__ import annotations

from backend.app.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.graph_rag import (
    build_graph_retriever,
    prioritize_venues,
    retrieve_rag_context_node,
)
from backend.app.models import (
    PlanRequest,
    Venue,
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


def make_restaurant(
    *,
    name: str,
    food_tags: list[str],
) -> Venue:
    return Venue(
        name=name,
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=25,
        duration_minutes=75,
        vibe=[
            "chill",
        ],
        food_tags=food_tags,
        latitude=42.3500,
        longitude=-71.0800,
        opening_hours=(
            "Mo-Su 11:00-22:00"
        ),
        source="sample",
    )


def test_prioritize_venues_uses_retrieval_rank() -> None:
    first = make_restaurant(
        name="Generic Place",
        food_tags=[],
    )

    second = make_restaurant(
        name="Chicken Spot",
        food_tags=[
            "chicken",
        ],
    )

    result = prioritize_venues(
        venues=[
            first,
            second,
        ],
        ranked_names=[
            "Chicken Spot",
            "Generic Place",
        ],
    )

    assert (
        result[
            0
        ].name
        == "Chicken Spot"
    )


def test_prioritize_venues_preserves_all_venues() -> None:
    first = make_restaurant(
        name="One",
        food_tags=[],
    )

    second = make_restaurant(
        name="Two",
        food_tags=[],
    )

    result = prioritize_venues(
        venues=[
            first,
            second,
        ],
        ranked_names=[
            "Two",
        ],
    )

    assert (
        len(
            result
        )
        == 2
    )

    assert {
        venue.name
        for venue
        in result
    } == {
        "One",
        "Two",
    }


def test_rag_node_retrieves_and_prioritizes(
    monkeypatch,
    tmp_path,
) -> None:
    request = make_request()

    generic = make_restaurant(
        name="Generic Place",
        food_tags=[],
    )

    chicken = make_restaurant(
        name="Chicken Spot",
        food_tags=[
            "chicken",
        ],
    )

    def fake_build_graph_retriever():
        from backend.app.rag_retriever import (
            PlanPilotRetriever,
        )

        return PlanPilotRetriever(
            persist_directory=str(
                tmp_path
                / "graph_rag"
            ),
            collection_name=(
                "graph_rag_test"
            ),
            embedding_provider=(
                DeterministicEmbeddingProvider(
                    dimensions=64,
                )
            ),
            prefer_live_embeddings=False,
        )

    monkeypatch.setattr(
        (
            "backend.app.graph_rag."
            "build_graph_retriever"
        ),
        fake_build_graph_retriever,
    )

    result = (
        retrieve_rag_context_node(
            {
                "user_message": (
                    "Find a chill chicken "
                    "dinner."
                ),
                "request": request,
                "venues": [
                    generic,
                    chicken,
                ],
            }
        )
    )

    assert (
        result[
            "rag_used"
        ]
        is True
    )

    assert (
        result[
            "rag_result_count"
        ]
        == 2
    )

    assert (
        result[
            "rag_context"
        ]
    )

    assert (
        "Chicken Spot"
        in result[
            "rag_context"
        ]
    )

    assert (
        result[
            "rag_ranked_venue_names"
        ]
    )


def test_rag_node_skips_empty_venue_pool() -> None:
    result = (
        retrieve_rag_context_node(
            {
                "user_message": (
                    "Plan dinner."
                ),
                "request": (
                    make_request()
                ),
                "venues": [],
            }
        )
    )

    assert (
        result[
            "rag_used"
        ]
        is False
    )

    assert (
        result[
            "rag_result_count"
        ]
        == 0
    )


def test_graph_retriever_can_use_local_storage(
    tmp_path,
) -> None:
    retriever = (
        build_graph_retriever(
            persist_directory=(
                tmp_path
                / "local_rag"
            ),
            prefer_live_embeddings=False,
        )
    )

    assert (
        retriever.count()
        == 0
    )
def test_graph_rag_uses_start_coordinates_for_hybrid_ranking(
    tmp_path,
    monkeypatch,
) -> None:
    from backend.app.embeddings import (
        DeterministicEmbeddingProvider,
    )
    from backend.app.graph_rag import (
        retrieve_rag_context_node,
    )
    from backend.app.models import (
        PlanRequest,
        Venue,
    )
    from backend.app.rag_retriever import (
        PlanPilotRetriever,
    )

    retriever = PlanPilotRetriever(
        persist_directory=str(
            tmp_path
            / "graph_hybrid"
        ),
        collection_name=(
            "graph_hybrid_test"
        ),
        embedding_provider=(
            DeterministicEmbeddingProvider(
                dimensions=64,
            )
        ),
        prefer_live_embeddings=False,
    )

    monkeypatch.setattr(
        "backend.app.graph_rag."
        "build_graph_retriever",
        lambda: retriever,
    )

    request = PlanRequest(
        city="Boston",
        start_area="Back Bay",
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

    far_venue = Venue(
        name="Far Chicken",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=90,
        vibe=[
            "chill",
        ],
        food_tags=[
            "chicken",
        ],
        latitude=42.4100,
        longitude=-71.1500,
        source="sample",
    )

    near_venue = Venue(
        name="Near Chicken",
        category="restaurant",
        area="Back Bay",
        estimated_cost_per_person=30,
        duration_minutes=90,
        vibe=[
            "chill",
        ],
        food_tags=[
            "chicken",
        ],
        latitude=42.3500,
        longitude=-71.0800,
        source="sample",
    )

    state = {
        "user_message": (
            "Plan a chill chicken "
            "dinner in Back Bay."
        ),
        "request": request,
        "venues": [
            far_venue,
            near_venue,
        ],
        "start_coordinates": (
            42.3493,
            -71.0810,
        ),
    }

    result = (
        retrieve_rag_context_node(
            state
        )
    )

    assert (
        result[
            "rag_used"
        ]
        is True
    )

    assert (
        result[
            "rag_ranked_venue_names"
        ][0]
        == "Near Chicken"
    )

    assert (
        result[
            "venues"
        ][0].name
        == "Near Chicken"
    )

    assert (
        "proximity="
        in result[
            "rag_context"
        ]
    )
