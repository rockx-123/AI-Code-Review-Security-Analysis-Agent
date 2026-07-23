"""
Report export endpoint — generates a PDF from a fresh analysis run and returns it as a
download. Deliberately re-runs the orchestrator (same as /api/analysis/{id}) rather than caching
a prior result, so the report always reflects the current rule set rather than a stale run.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response, status

from app.agents.orchestrator import Orchestrator
from app.api.routes.submission import get_submission_by_id
from app.services.report_generator import generate_pdf_report

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{submission_id}/pdf")
def download_pdf_report(submission_id: str) -> Response:
    submission = get_submission_by_id(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")

    summary = Orchestrator().run(submission)
    pdf_bytes = generate_pdf_report(submission, summary)

    filename = f"code-review-report-{submission_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
