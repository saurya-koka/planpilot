from __future__ import annotations

import pytest

from backend.app.embeddings import (
    DeterministicEmbeddingProvider,
    get_embedding_provider,
)


def test_deterministic_embedding_is_repeatable() -> None:
    provider = (
        DeterministicEmbeddingProvider(
            dimensions=32,
        )
    )

    first = provider.embed_query(
        "romantic Italian restaurant"
    )

    second = provider.embed_query(
        "romantic Italian restaurant"
    )

    assert (
        first
        == second
    )


def test_deterministic_embedding_dimensions() -> None:
    provider = (
        DeterministicEmbeddingProvider(
            dimensions=48,
        )
    )

    embedding = (
        provider.embed_query(
            "Boston dinner"
        )
    )

    assert (
        len(
            embedding
        )
        == 48
    )


def test_document_embedding_count_matches_input() -> None:
    provider = (
        DeterministicEmbeddingProvider(
            dimensions=32,
        )
    )

    embeddings = (
        provider.embed_documents(
            [
                "Italian dinner",
                "indoor activity",
                "dessert cafe",
            ]
        )
    )

    assert (
        len(
            embeddings
        )
        == 3
    )

    assert all(
        len(vector)
        == 32
        for vector
        in embeddings
    )


def test_similar_text_has_same_token_signal() -> None:
    provider = (
        DeterministicEmbeddingProvider(
            dimensions=64,
        )
    )

    first = provider.embed_query(
        "chill chicken restaurant"
    )

    second = provider.embed_query(
        "chill restaurant"
    )

    assert any(
        (
            value_a != 0
            and value_b != 0
        )
        for value_a, value_b
        in zip(
            first,
            second,
        )
    )


def test_invalid_embedding_dimension_rejected() -> None:
    with pytest.raises(
        ValueError,
    ):
        (
            DeterministicEmbeddingProvider(
                dimensions=4,
            )
        )


def test_offline_provider_resolution(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "",
    )

    provider = (
        get_embedding_provider(
            prefer_live=True,
        )
    )

    assert isinstance(
        provider,
        DeterministicEmbeddingProvider,
    )
