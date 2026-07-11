"""
Heading-aware markdown chunker for the secure coding knowledge base.

Splits each document on its `#`/`##` headings first (so a chunk never straddles two unrelated
topics), then, only if a section is still larger than `chunk_size_tokens`, sub-splits it on
paragraph boundaries with overlap. This is deliberately not a fixed-length sliding window —
cutting "SQL injection prevention" in half mid-sentence would hurt retrieval quality more than
having slightly uneven chunk sizes helps.

Token counting here is approximate (whitespace-split word count) rather than a real tokenizer,
which is precise enough for chunk-sizing purposes and keeps this module dependency-free.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)
_FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class DocumentMeta:
    title: str
    category: str


@dataclass
class Chunk:
    text: str
    heading: str | None
    chunk_index: int = field(default=0)


def parse_front_matter(raw_text: str) -> tuple[DocumentMeta, str]:
    """Extract simple `key: value` front matter and return (meta, body)."""
    match = _FRONT_MATTER_RE.match(raw_text)
    title, category = "Untitled", "secure-coding"
    body = raw_text
    if match:
        body = raw_text[match.end():]
        for line in match.group(1).splitlines():
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            key, value = key.strip().lower(), value.strip()
            if key == "title":
                title = value
            elif key == "category":
                category = value
    return DocumentMeta(title=title, category=category), body


def _split_by_heading(body: str) -> list[tuple[str | None, str]]:
    """Return [(heading_text_or_None, section_body), ...] preserving document order."""
    matches = list(_HEADING_RE.finditer(body))
    if not matches:
        return [(None, body.strip())] if body.strip() else []

    sections: list[tuple[str | None, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        section_body = body[start:end].strip()
        if section_body:
            sections.append((heading, section_body))
    return sections


def _word_count(text: str) -> int:
    return len(text.split())


def _sub_split(text: str, max_words: int, overlap_words: int) -> list[str]:
    """Split an oversized section on paragraph boundaries, with word-count overlap between parts."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else []

    parts: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = _word_count(para)
        if current and current_words + para_words > max_words:
            parts.append("\n\n".join(current))
            # carry the tail of the previous part forward for continuity
            overlap_text = " ".join(" ".join(current).split()[-overlap_words:])
            current = [overlap_text, para] if overlap_text else [para]
            current_words = _word_count(" ".join(current))
        else:
            current.append(para)
            current_words += para_words

    if current:
        parts.append("\n\n".join(current))
    return parts


def chunk_document(raw_text: str, max_words: int = 300, overlap_words: int = 50) -> tuple[DocumentMeta, list[Chunk]]:
    meta, body = parse_front_matter(raw_text)
    sections = _split_by_heading(body)

    chunks: list[Chunk] = []
    idx = 0
    for heading, section_text in sections:
        if _word_count(section_text) <= max_words:
            chunks.append(Chunk(text=section_text, heading=heading, chunk_index=idx))
            idx += 1
        else:
            for part in _sub_split(section_text, max_words, overlap_words):
                chunks.append(Chunk(text=part, heading=heading, chunk_index=idx))
                idx += 1
    return meta, chunks
