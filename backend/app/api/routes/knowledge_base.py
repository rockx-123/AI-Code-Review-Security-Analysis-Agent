"""
Read-only API over the secure coding knowledge base (Milestone 1, Task 4).

Query endpoint exists in Milestone 1 mainly so the RAG pipeline is demonstrably working end to
end (index -> embed -> retrieve). It becomes load-bearing in Milestone 4, when the Conversational
Assistant and Remediation Agent call the same underlying `VectorStore.query()`.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import (
    KnowledgeBaseStatus,
    KnowledgeChunkResult,
    KnowledgeQueryRequest,
    KnowledgeQueryResponse,
)
from app.rag.vector_store import get_vector_store

router = APIRouter(prefix="/api/knowledge-base", tags=["knowledge-base"])


@router.get("/status", response_model=KnowledgeBaseStatus)
def knowledge_base_status() -> KnowledgeBaseStatus:
    store = get_vector_store()
    metadatas = store.get_all_metadata()
    doc_ids = {m.get("doc_id") for m in metadatas if m.get("doc_id")}
    categories = sorted({m.get("category") for m in metadatas if m.get("category")})

    from app.config import get_settings

    return KnowledgeBaseStatus(
        collection=get_settings().vector_store_collection,
        document_count=len(doc_ids),
        chunk_count=len(metadatas),
        categories=categories,
    )


@router.post("/query", response_model=KnowledgeQueryResponse)
def query_knowledge_base(payload: KnowledgeQueryRequest) -> KnowledgeQueryResponse:
    store = get_vector_store()
    if store.count() == 0:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base index is empty — run `python -m app.rag.ingest` first.",
        )

    raw_results = store.query(payload.query, top_k=payload.top_k, category=payload.category)
    results = [
        KnowledgeChunkResult(
            chunk_id=r.chunk_id,
            doc_id=r.metadata.get("doc_id", ""),
            title=r.metadata.get("title", ""),
            category=r.metadata.get("category", ""),
            heading=r.metadata.get("heading") or None,
            text=r.document,
            score=r.score,
        )
        for r in raw_results
    ]
    return KnowledgeQueryResponse(query=payload.query, results=results)
