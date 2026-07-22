"""
Multi-Agent Analysis API — Milestone 2.

Wires the Code Submission Module (Milestone 1) to the Code Analysis + Security Vulnerability
agents and their orchestrator (Milestone 2), exactly as anticipated in docs/architecture.md's
orchestration flow: a submission is validated first (Milestone 1), then analyzed here on request.

Deliberately a separate, explicit action from submission — POST /api/submissions/paste never
triggers analysis as a side effect. The frontend calls this only after the user asks for it.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.agents.orchestrator import Orchestrator
from app.api.routes.submission import get_submission_by_id
from app.models.schemas import ReviewSummary

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_orchestrator = Orchestrator()


@router.post("/{submission_id}", response_model=ReviewSummary)
def run_analysis(submission_id: str) -> ReviewSummary:
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return _orchestrator.run(submission)
