"""
Internal finding representation used inside the agents package.

Agents don't know a submission's id (they just receive language + code), so they can't build a
full `app.models.schemas.Finding` directly — that needs `submission_id`. `RawFinding` is the
same shape minus that field; the orchestrator converts these to real `Finding`s once it has the
submission context. Keeping this as a plain dataclass (not a Pydantic model) means the detection
logic in this package has zero dependency on FastAPI/Pydantic and can be unit-tested in total
isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class RawFinding:
    category: Literal["code-quality", "security"]
    title: str
    description: str
    severity: Literal["critical", "high", "medium", "low", "info"]
    start_line: int
    end_line: int
    snippet: str
    rule_id: str
    owasp_category: str | None = None
    cwe_id: str | None = None
    knowledge_base_refs: list[str] = field(default_factory=list)
