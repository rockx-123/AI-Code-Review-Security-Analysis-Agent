"""
Thin wrapper around Chroma so the rest of the app depends on this interface, not on Chroma
directly. Per docs/architecture.md §4, swapping to a hosted vector DB later should only require
changes in this file.
"""
from __future__ import annotations

from dataclasses import dataclass

import chromadb
from chromadb.utils import embedding_functions

from app.config import get_settings


@dataclass
class QueryResult:
    chunk_id: str
    document: str
    metadata: dict
    score: float  # similarity in [0, 1], higher = more relevant


class VectorStore:
    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(path=str(settings.vector_store_path))
        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=settings.embedding_model
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.vector_store_collection,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        """Drop and recreate the collection — used by the ingestion script for clean rebuilds."""
        settings = get_settings()
        self._client.delete_collection(settings.vector_store_collection)
        self._collection = self._client.get_or_create_collection(
            name=settings.vector_store_collection,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, ids: list[str], documents: list[str], metadatas: list[dict]) -> None:
        if not ids:
            return
        self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    def query(self, text: str, top_k: int = 4, category: str | None = None) -> list[QueryResult]:
        where = {"category": category} if category else None
        result = self._collection.query(
            query_texts=[text],
            n_results=top_k,
            where=where,
        )
        results: list[QueryResult] = []
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, doc, meta, distance in zip(ids, docs, metas, distances):
            # Chroma returns cosine *distance*; convert to a 0..1 similarity score for the API.
            similarity = max(0.0, 1.0 - distance)
            results.append(QueryResult(chunk_id=chunk_id, document=doc, metadata=meta, score=round(similarity, 4)))
        return results

    def count(self) -> int:
        return self._collection.count()

    def get_all_metadata(self) -> list[dict]:
        result = self._collection.get(include=["metadatas"])
        return result.get("metadatas", []) or []


_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        _store = VectorStore()
    return _store
