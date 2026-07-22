"""
Multi-Agent Orchestration — Milestone 2, Task 3.

Runs the Code Analysis Agent and Security Vulnerability Agent in parallel against a submission,
merges their output into a unified findings list, and converts the internal `RawFinding` shape
(see models.py) into the public `Finding`/`ReviewSummary` API contract.

Per docs/agent-design.md's orchestration contract: each agent is isolated — a failure in one
must not prevent the other's results from coming back. A failed agent contributes zero findings
plus a note in `agent_errors` rather than crashing the whole request.

Deliberately NOT populated here (reserved for later milestones, per docs/milestones.md):
  - `remediation` on each Finding — Remediation Agent, Milestone 3
  - `narrative` on the ReviewSummary — PR Summary Agent, Milestone 3
`top_risks` and `counts_by_severity` ARE computed here since they're pure aggregation over the
findings this milestone already produces, not new analysis.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from app.agents.code_analysis_java import analyze_java
from app.agents.code_analysis_python import analyze_python
from app.agents.finding_utils import ground_with_knowledge_base
from app.agents.models import RawFinding
from app.agents.security_java import analyze_java_security
from app.agents.security_python import analyze_python_security
from app.models.schemas import (
    Finding,
    FindingLocation,
    ReviewSummary,
    Severity,
    SeverityCounts,
    Submission,
)

_SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
_TOP_RISKS_LIMIT = 5

_CODE_ANALYSIS_AGENTS: dict[str, Callable[[str], list[RawFinding]]] = {
    "python": analyze_python,
    "java": analyze_java,
}
_SECURITY_AGENTS: dict[str, Callable[[str], list[RawFinding]]] = {
    "python": analyze_python_security,
    "java": analyze_java_security,
}


def _to_finding(raw: RawFinding, submission_id: str) -> Finding:
    return Finding(
        submission_id=submission_id,
        category=raw.category,
        title=raw.title,
        description=raw.description,
        severity=Severity(raw.severity),
        location=FindingLocation(start_line=raw.start_line, end_line=raw.end_line, snippet=raw.snippet),
        owasp_category=raw.owasp_category,
        cwe_id=raw.cwe_id,
        knowledge_base_refs=raw.knowledge_base_refs,
    )


def _ground_security_finding(raw: RawFinding) -> RawFinding:
    """
    Attaches a supporting knowledge base reference to a security finding, per
    docs/agent-design.md's grounding contract. Best-effort — `ground_with_knowledge_base` never
    raises, so a missing/unavailable knowledge base just leaves `knowledge_base_refs` empty
    rather than failing the finding entirely.
    """
    if raw.category != "security":
        return raw
    query = f"{raw.title} {raw.owasp_category or ''}".strip()
    raw.knowledge_base_refs = ground_with_knowledge_base(query, top_k=1)
    return raw


def _run_agent_safely(fn: Callable[[str], list[RawFinding]], code: str, agent_name: str) -> tuple[list[RawFinding], str | None]:
    """Runs one detector function, converting any exception into an error note instead of
    propagating it — so a bug in one agent can't take down the other's results."""
    try:
        return fn(code), None
    except Exception as exc:  # noqa: BLE001 - deliberately broad: isolate ANY agent failure
        return [], f"{agent_name} failed: {exc.__class__.__name__}: {exc}"


class Orchestrator:
    def run(self, submission: Submission) -> ReviewSummary:
        language = submission.language.value
        code_analysis_fn = _CODE_ANALYSIS_AGENTS.get(language)
        security_fn = _SECURITY_AGENTS.get(language)

        agent_errors: list[str] = []
        raw_findings: list[RawFinding] = []

        # Run both agents in parallel (Milestone 2, Task 3) rather than sequentially — they're
        # independent (neither depends on the other's output), so there's no reason to serialize.
        with ThreadPoolExecutor(max_workers=2) as pool:
            code_future = pool.submit(_run_agent_safely, code_analysis_fn, submission.code, "Code Analysis Agent") \
                if code_analysis_fn else None
            security_future = pool.submit(_run_agent_safely, security_fn, submission.code, "Security Vulnerability Agent") \
                if security_fn else None

            if code_future:
                findings, error = code_future.result()
                raw_findings += findings
                if error:
                    agent_errors.append(error)
            if security_future:
                findings, error = security_future.result()
                raw_findings += findings
                if error:
                    agent_errors.append(error)

        if not code_analysis_fn and not security_fn:
            agent_errors.append(f"No agents available for language '{language}'.")

        raw_findings = [_ground_security_finding(raw) for raw in raw_findings]
        findings = [_to_finding(raw, submission.id) for raw in raw_findings]
        findings.sort(key=lambda f: _SEVERITY_RANK.get(f.severity.value, 99))

        counts = SeverityCounts()
        for f in findings:
            setattr(counts, f.severity.value, getattr(counts, f.severity.value) + 1)

        return ReviewSummary(
            submission_id=submission.id,
            counts_by_severity=counts,
            top_risks=findings[:_TOP_RISKS_LIMIT],
            narrative="",  # populated by the PR Summary Agent — Milestone 3
            findings=findings,
            agent_errors=agent_errors,
        )
