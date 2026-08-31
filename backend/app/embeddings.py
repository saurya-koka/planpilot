from __future__ import annotations

import hashlib
import math
import os
from typing import Protocol

from dotenv import load_dotenv


load_dotenv()


DEFAULT_EMBEDDING_MODEL = (
    "text-embedding-3-small"
)

DEFAULT_FAKE_EMBEDDING_DIMENSIONS = 64


class EmbeddingProvider(
    Protocol
):
    """
    Interface used by PlanPilot's retrieval layer.

    Production can use OpenAI embeddings while tests can use the
    deterministic local provider below.
    """

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        ...

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        ...


def normalize_vector(
    values: list[float],
) -> list[float]:
    """
    Normalize one embedding vector to unit length.
    """

    magnitude = math.sqrt(
        sum(
            value * value
            for value
            in values
        )
    )

    if magnitude == 0:
        return values

    return [
        value / magnitude
        for value
        in values
    ]


class DeterministicEmbeddingProvider:
    """
    Deterministic local embedding implementation for tests and
    offline development.

    This is not intended to approximate a production semantic model.

    Each token is hashed into one vector bucket. Shared tokens
    therefore contribute to shared vector positions, making the
    implementation predictable enough for vector-store tests while
    requiring no network calls or API credits.
    """

    def __init__(
        self,
        dimensions: int = (
            DEFAULT_FAKE_EMBEDDING_DIMENSIONS
        ),
    ) -> None:
        if dimensions < 8:
            raise ValueError(
                "dimensions must be "
                "at least 8."
            )

        self.dimensions = (
            dimensions
        )

    def _tokenize(
        self,
        text: str,
    ) -> list[str]:
        """
        Produce a small deterministic token collection.
        """

        normalized = (
            text.lower()
            .replace(",", " ")
            .replace(".", " ")
            .replace("/", " ")
            .replace("-", " ")
            .replace("_", " ")
            .replace(":", " ")
            .replace(";", " ")
        )

        return [
            token
            for token
            in normalized.split()
            if token
        ]

    def _embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Convert text into a deterministic hashed bag-of-words vector.

        Positive counts are intentional. They prevent hash collisions
        from cancelling shared token signals during unit tests.
        """

        vector = [
            0.0
            for _ in range(
                self.dimensions
            )
        ]

        tokens = (
            self._tokenize(
                text
            )
        )

        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(
                token.encode(
                    "utf-8"
                )
            ).digest()

            index = int.from_bytes(
                digest[:4],
                byteorder="big",
            ) % self.dimensions

            vector[
                index
            ] += 1.0

        return normalize_vector(
            vector
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            self._embed(
                text
            )
            for text
            in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        return self._embed(
            text
        )


class OpenAIEmbeddingProvider:
    """
    Production embedding provider backed by the OpenAI Embeddings API.
    """

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        resolved_api_key = (
            api_key
            or os.getenv(
                "OPENAI_API_KEY"
            )
        )

        if not resolved_api_key:
            raise ValueError(
                "OPENAI_API_KEY is not "
                "configured."
            )

        from openai import (
            OpenAI,
        )

        self.client = OpenAI(
            api_key=(
                resolved_api_key
            )
        )

        self.model = (
            model
            or os.getenv(
                "OPENAI_EMBEDDING_MODEL",
                DEFAULT_EMBEDDING_MODEL,
            )
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            return []

        response = (
            self.client
            .embeddings
            .create(
                model=self.model,
                input=texts,
            )
        )

        ordered = sorted(
            response.data,
            key=lambda item: (
                item.index
            ),
        )

        return [
            list(
                item.embedding
            )
            for item
            in ordered
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        embeddings = (
            self.embed_documents(
                [
                    text,
                ]
            )
        )

        return embeddings[
            0
        ]


def embedding_provider_is_configured() -> bool:
    """
    Return whether live OpenAI embeddings can be used.
    """

    return bool(
        os.getenv(
            "OPENAI_API_KEY"
        )
    )


def get_embedding_provider(
    *,
    prefer_live: bool = True,
) -> EmbeddingProvider:
    """
    Resolve the embedding provider for one retrieval workflow.

    Live OpenAI embeddings are preferred when available. Otherwise
    PlanPilot falls back to the deterministic local implementation.
    """

    if (
        prefer_live
        and embedding_provider_is_configured()
    ):
        return (
            OpenAIEmbeddingProvider()
        )

    return (
        DeterministicEmbeddingProvider()
    )
