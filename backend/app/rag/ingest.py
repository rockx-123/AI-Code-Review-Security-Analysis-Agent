"""
Builds the secure coding knowledge base index: reads every markdown doc in
`app/rag/knowledge_base/`, chunks it (heading-aware, see chunker.py), embeds each chunk, and
upserts it into the vector store.

Run whenever knowledge base documents change:

    python -m app.rag.ingest

Idempotent: chunk IDs are deterministic (`{doc_slug}::{chunk_index}`), so re-running after
editing a doc updates existing chunks rather than duplicating them. Use --reset to drop and
fully rebuild the collection (e.g. after changing the embedding model or chunk size).
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from app.config import get_settings
from app.rag.chunker import chunk_document
from app.rag.vector_store import get_vector_store

KNOWLEDGE_BASE_DIR = Path(__file__).parent / "knowledge_base"


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def ingest(reset: bool = False) -> dict:
    settings = get_settings()
    store = get_vector_store()
    if reset:
        store.reset()

    doc_paths = sorted(KNOWLEDGE_BASE_DIR.glob("*.md"))
    if not doc_paths:
        raise RuntimeError(f"No knowledge base documents found in {KNOWLEDGE_BASE_DIR}")

    total_chunks = 0
    categories: set[str] = set()

    for path in doc_paths:
        raw_text = path.read_text(encoding="utf-8")
        meta, chunks = chunk_document(
            raw_text,
            max_words=settings.chunk_size_tokens,
            overlap_words=settings.chunk_overlap_tokens,
        )
        doc_slug = _slugify(path.stem)
        categories.add(meta.category)

        ids = [f"{doc_slug}::{c.chunk_index}" for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [
            {
                "doc_id": doc_slug,
                "title": meta.title,
                "category": meta.category,
                "heading": c.heading or "",
                "chunk_index": c.chunk_index,
                "source_path": str(path.relative_to(KNOWLEDGE_BASE_DIR.parent.parent.parent)),
            }
            for c in chunks
        ]
        store.upsert(ids=ids, documents=documents, metadatas=metadatas)
        total_chunks += len(chunks)
        print(f"  indexed {len(chunks):>3} chunks  <-  {path.name}  ({meta.category})")

    return {
        "documents": len(doc_paths),
        "chunks": total_chunks,
        "categories": sorted(categories),
        "collection_size": store.count(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build/update the secure coding knowledge base index")
    parser.add_argument("--reset", action="store_true", help="Drop and rebuild the collection from scratch")
    args = parser.parse_args()

    print("Building secure coding knowledge base index...")
    summary = ingest(reset=args.reset)
    print(
        f"\nDone. {summary['documents']} documents -> {summary['chunks']} chunks "
        f"indexed (collection now holds {summary['collection_size']} chunks). "
        f"Categories: {', '.join(summary['categories'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
