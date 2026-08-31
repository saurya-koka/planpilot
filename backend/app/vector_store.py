from __future__ import annotations

from dataclasses import (
    dataclass,
)
from pathlib import Path
from typing import Any

import chromadb

from .embeddings import (
    EmbeddingProvider,
    get_embedding_provider,
)


DEFAULT_COLLECTION_NAME = (
    "planpilot_knowledge"
)

DEFAULT_CHROMA_PATH = (
    ".planpilot_chroma"
)


@dataclass
class VectorDocument:
    """
    One normalized document stored in PlanPilot's vector database.
    """

    document_id: str
    text: str
    metadata: dict[
        str,
        str | int | float | bool,
    ]


@dataclass
class RetrievalResult:
    """
    One semantic retrieval hit.
    """

    document_id: str
    text: str

    metadata: dict[
        str,
        Any,
    ]

    distance: float | None = None


class PlanPilotVectorStore:
    """
    Thin ChromaDB wrapper used by PlanPilot's RAG layer.

    The vector store owns:
    - collection creation
    - embedding generation
    - document upsert
    - semantic query
    - collection clearing

    Embeddings remain behind the EmbeddingProvider abstraction so
    tests never require OpenAI.
    """

    def __init__(
        self,
        *,
        persist_directory: (
            str
            | Path
        ) = DEFAULT_CHROMA_PATH,
        collection_name: str = (
            DEFAULT_COLLECTION_NAME
        ),
        embedding_provider: (
            EmbeddingProvider
            | None
        ) = None,
        prefer_live_embeddings: bool = True,
    ) -> None:
        self.persist_directory = Path(
            persist_directory
        )

        self.persist_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.embedding_provider = (
            embedding_provider
            or get_embedding_provider(
                prefer_live=(
                    prefer_live_embeddings
                )
            )
        )

        self.client = (
            chromadb.PersistentClient(
                path=str(
                    self.persist_directory
                )
            )
        )

        self.collection_name = (
            collection_name
        )

        self.collection = (
            self.client
            .get_or_create_collection(
                name=(
                    self.collection_name
                ),
            )
        )

    def count(
        self,
    ) -> int:
        """
        Return the number of documents currently stored.
        """

        return int(
            self.collection.count()
        )

    def upsert_documents(
        self,
        documents: list[
            VectorDocument
        ],
    ) -> int:
        """
        Add or replace documents by document_id.

        Returns the number of input documents processed.
        """

        if not documents:
            return 0

        ids = [
            document.document_id
            for document
            in documents
        ]

        texts = [
            document.text
            for document
            in documents
        ]

        metadatas = [
            document.metadata
            for document
            in documents
        ]

        embeddings = (
            self.embedding_provider
            .embed_documents(
                texts
            )
        )

        if (
            len(embeddings)
            != len(documents)
        ):
            raise ValueError(
                "Embedding provider returned "
                "an unexpected number of "
                "vectors."
            )

        self.collection.upsert(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
            embeddings=embeddings,
        )

        return len(
            documents
        )

    def query(
        self,
        *,
        query_text: str,
        limit: int = 5,
        where: (
            dict[
                str,
                Any,
            ]
            | None
        ) = None,
    ) -> list[
        RetrievalResult
    ]:
        """
        Perform semantic nearest-neighbor retrieval.
        """

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        if (
            not query_text
            .strip()
        ):
            raise ValueError(
                "query_text cannot be empty."
            )

        if self.count() == 0:
            return []

        query_embedding = (
            self.embedding_provider
            .embed_query(
                query_text
            )
        )

        query_kwargs: dict[
            str,
            Any,
        ] = {
            "query_embeddings": [
                query_embedding,
            ],
            "n_results": (
                min(
                    limit,
                    self.count(),
                )
            ),
            "include": [
                "documents",
                "metadatas",
                "distances",
            ],
        }

        if where is not None:
            query_kwargs[
                "where"
            ] = where

        raw = self.collection.query(
            **query_kwargs
        )

        raw_ids = (
            raw.get(
                "ids",
                [],
            )
        )

        raw_documents = (
            raw.get(
                "documents",
                [],
            )
            or []
        )

        raw_metadatas = (
            raw.get(
                "metadatas",
                [],
            )
            or []
        )

        raw_distances = (
            raw.get(
                "distances",
                [],
            )
            or []
        )

        if not raw_ids:
            return []

        ids = raw_ids[
            0
        ]

        documents = (
            raw_documents[0]
            if raw_documents
            else []
        )

        metadatas = (
            raw_metadatas[0]
            if raw_metadatas
            else []
        )

        distances = (
            raw_distances[0]
            if raw_distances
            else []
        )

        results: list[
            RetrievalResult
        ] = []

        for index, document_id in enumerate(
            ids
        ):
            text = (
                documents[
                    index
                ]
                if index
                < len(documents)
                else ""
            )

            metadata = (
                metadatas[
                    index
                ]
                if index
                < len(metadatas)
                else {}
            )

            distance = (
                distances[
                    index
                ]
                if index
                < len(distances)
                else None
            )

            results.append(
                RetrievalResult(
                    document_id=(
                        document_id
                    ),
                    text=text or "",
                    metadata=(
                        metadata
                        or {}
                    ),
                    distance=(
                        float(
                            distance
                        )
                        if distance
                        is not None
                        else None
                    ),
                )
            )

        return results

    def delete_all(
        self,
    ) -> None:
        """
        Delete all documents in this collection.

        Recreating the collection is more reliable than relying on
        provider-specific wildcard delete behavior.
        """

        self.client.delete_collection(
            name=(
                self.collection_name
            )
        )

        self.collection = (
            self.client
            .get_or_create_collection(
                name=(
                    self.collection_name
                ),
            )
        )
