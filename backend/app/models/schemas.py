"""
Typed contracts shared across the API, the RAG pipeline, and (starting Milestone 2) the agents.

Mirrors docs/data-models.md exactly — that file is the human-readable spec, this is the
enforced one. `Finding` and `ReviewSummary` are included now, unused by any endpoint yet, so the
shape is frozen before Milestone 2 starts writing agents against it.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


class Language(str, Enum):
    PYTHON = "python"
    JAVA = "java"


class SubmissionSource(str, Enum):
    MANUAL = "manual"
    UPLOAD = "upload"


class EntryMethod(str, Enum):
    TYPED = "typed"
    PASTED = "pasted"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


# ---------------------------------------------------------------------------
# Submission (Milestone 1)
# ---------------------------------------------------------------------------

class ValidationError(BaseModel):
    line: int | None = None
    column: int | None = None
    message: str


class SyntaxValidationResult(BaseModel):
    is_valid: bool
    errors: list[ValidationError] = Field(default_factory=list)
    validated_at: datetime = Field(default_factory=_now)


class SubmissionRequest(BaseModel):
    """Body for POST /api/submissions when pasting code."""
    language: Language
    code: str = Field(..., min_length=1, description="Raw source code")
    entry_method: EntryMethod | None = None

    model_config = {
        "json_schema_extra": {
            "example": {"language": "python", "code": "def add(a, b):\n    return a + b\n"}
        }
    }


class Submission(BaseModel):
    id: str = Field(default_factory=_uuid)
    language: Language
    source: SubmissionSource
    filename: str | None = None
    entry_method: EntryMethod | None = None
    code: str
    size_bytes: int
    created_at: datetime = Field(default_factory=_now)
    validation: SyntaxValidationResult


# ---------------------------------------------------------------------------
# Finding / ReviewSummary — contract frozen in M1, populated starting M2/M3
# ---------------------------------------------------------------------------

class FindingLocation(BaseModel):
    start_line: int
    end_line: int
    snippet: str


class Remediation(BaseModel):
    explanation: str
    fixed_snippet: str
    references: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str = Field(default_factory=_uuid)
    submission_id: str
    category: Literal["code-quality", "security"]
    title: str
    description: str
    severity: Severity
    location: FindingLocation
    owasp_category: str | None = None
    cwe_id: str | None = None
    knowledge_base_refs: list[str] = Field(default_factory=list)
    remediation: Remediation | None = None


class SeverityCounts(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class ReviewSummary(BaseModel):
    submission_id: str
    generated_at: datetime = Field(default_factory=_now)
    counts_by_severity: SeverityCounts = Field(default_factory=SeverityCounts)
    top_risks: list[Finding] = Field(default_factory=list)
    narrative: str = ""
    findings: list[Finding] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Knowledge base (Milestone 1)
# ---------------------------------------------------------------------------

class KnowledgeChunkResult(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    category: str
    heading: str | None = None
    text: str
    score: float


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)
    category: str | None = None


class KnowledgeQueryResponse(BaseModel):
    query: str
    results: list[KnowledgeChunkResult]


class KnowledgeBaseStatus(BaseModel):
    collection: str
    document_count: int
    chunk_count: int
    categories: list[str]
