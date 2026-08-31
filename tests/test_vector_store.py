from __future__ import annotations

from backend.app.embeddings import (
    DeterministicEmbeddingProvider,
)
from backend.app.vector_store import (
    PlanPilotVectorStore,
    VectorDocument,
)


def make_store(
    tmp_path,
) -> PlanPilotVectorStore:
    return PlanPilotVectorStore(
        persist_directory=(
            tmp_path
            / "chroma"
        ),
        collection_name=(
            "test_planpilot"
        ),
        embedding_provider=(
            DeterministicEmbeddingProvider(
                dimensions=64,
            )
        ),
        prefer_live_embeddings=False,
    )


def test_vector_store_starts_empty(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    assert (
        store.count()
        == 0
    )


def test_upsert_documents_adds_records(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    inserted = (
        store.upsert_documents(
            [
                VectorDocument(
                    document_id="1",
                    text=(
                        "Chill Italian "
                        "restaurant in "
                        "Back Bay"
                    ),
                    metadata={
                        "category": (
                            "restaurant"
                        ),
                    },
                ),
                VectorDocument(
                    document_id="2",
                    text=(
                        "Indoor activity "
                        "near downtown"
                    ),
                    metadata={
                        "category": (
                            "activity"
                        ),
                    },
                ),
            ]
        )
    )

    assert (
        inserted
        == 2
    )

    assert (
        store.count()
        == 2
    )


def test_query_returns_semantic_match(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    store.upsert_documents(
        [
            VectorDocument(
                document_id="restaurant",
                text=(
                    "chill chicken "
                    "restaurant dinner"
                ),
                metadata={
                    "category": (
                        "restaurant"
                    ),
                },
            ),
            VectorDocument(
                document_id="activity",
                text=(
                    "museum indoor "
                    "activity exhibits"
                ),
                metadata={
                    "category": (
                        "activity"
                    ),
                },
            ),
        ]
    )

    results = store.query(
        query_text=(
            "chill restaurant"
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
        ].document_id
        == "restaurant"
    )


def test_query_supports_metadata_filter(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    store.upsert_documents(
        [
            VectorDocument(
                document_id="restaurant",
                text=(
                    "chill restaurant"
                ),
                metadata={
                    "category": (
                        "restaurant"
                    ),
                },
            ),
            VectorDocument(
                document_id="dessert",
                text=(
                    "chill dessert cafe"
                ),
                metadata={
                    "category": (
                        "dessert"
                    ),
                },
            ),
        ]
    )

    results = store.query(
        query_text="chill",
        limit=5,
        where={
            "category": (
                "dessert"
            ),
        },
    )

    assert (
        len(results)
        == 1
    )

    assert (
        results[
            0
        ].document_id
        == "dessert"
    )


def test_upsert_replaces_existing_document(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    store.upsert_documents(
        [
            VectorDocument(
                document_id="venue-1",
                text=(
                    "old restaurant"
                ),
                metadata={
                    "category": (
                        "restaurant"
                    ),
                },
            )
        ]
    )

    store.upsert_documents(
        [
            VectorDocument(
                document_id="venue-1",
                text=(
                    "updated restaurant"
                ),
                metadata={
                    "category": (
                        "restaurant"
                    ),
                },
            )
        ]
    )

    assert (
        store.count()
        == 1
    )

    result = store.query(
        query_text=(
            "updated restaurant"
        ),
        limit=1,
    )

    assert (
        result[
            0
        ].document_id
        == "venue-1"
    )


def test_empty_query_database_returns_empty(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    results = store.query(
        query_text="restaurant",
        limit=5,
    )

    assert (
        results
        == []
    )


def test_delete_all_clears_collection(
    tmp_path,
) -> None:
    store = make_store(
        tmp_path
    )

    store.upsert_documents(
        [
            VectorDocument(
                document_id="1",
                text="restaurant",
                metadata={
                    "category": (
                        "restaurant"
                    ),
                },
            )
        ]
    )

    assert (
        store.count()
        == 1
    )

    store.delete_all()

    assert (
        store.count()
        == 0
    )
