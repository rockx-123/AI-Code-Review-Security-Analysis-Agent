"""Shared helper used by the Security Vulnerability Agent's grounding step (orchestrator.py)."""
from __future__ import annotations


def ground_with_knowledge_base(query: str, category: str | None = None, top_k: int = 1) -> list[str]:
    """
    Best-effort lookup into the secure coding knowledge base to attach a supporting reference to
    a finding (per docs/agent-design.md's grounding contract for the Security Vulnerability
    Agent). Never raises — if the vector store isn't available for any reason (not yet indexed,
    optional dependency not installed, etc.), findings are still returned, just without a
    `knowledge_base_refs` reference.
    """
    try:
        from app.rag.vector_store import get_vector_store

        results = get_vector_store().query(query, top_k=top_k, category=category)
        return [r.chunk_id for r in results]
    except Exception:
        return []
