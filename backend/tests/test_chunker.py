from app.rag.chunker import chunk_document, parse_front_matter

SAMPLE_DOC = """---
title: Sample Doc
category: owasp
---

# Section One

Some short content about section one.

# Section Two

Some short content about section two.
"""


def test_parse_front_matter():
    meta, body = parse_front_matter(SAMPLE_DOC)
    assert meta.title == "Sample Doc"
    assert meta.category == "owasp"
    assert "Section One" in body


def test_chunk_document_splits_by_heading():
    meta, chunks = chunk_document(SAMPLE_DOC, max_words=300, overlap_words=20)
    assert meta.category == "owasp"
    headings = [c.heading for c in chunks]
    assert "Section One" in headings
    assert "Section Two" in headings
    assert len(chunks) == 2


def test_chunk_document_sub_splits_long_section():
    long_paragraph = ("word " * 500).strip()
    doc = f"---\ntitle: Long Doc\ncategory: code-smell\n---\n\n# Only Section\n\n{long_paragraph}\n\n{long_paragraph}\n"
    meta, chunks = chunk_document(doc, max_words=100, overlap_words=10)
    assert len(chunks) > 1
    assert all(c.heading == "Only Section" for c in chunks)


def test_chunk_indices_are_sequential():
    _, chunks = chunk_document(SAMPLE_DOC, max_words=300, overlap_words=20)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
