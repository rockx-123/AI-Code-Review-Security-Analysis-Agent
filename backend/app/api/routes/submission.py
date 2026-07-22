"""
Code Submission Module — Milestone 1, Task 3.

Entry points, one shared validation path:
  POST /api/submissions/paste   — direct code entry (typed or pasted)
  POST /api/submissions/upload  — file upload (.py / .java)
  GET  /api/submissions         — recent activity feed (lightweight summaries)
  GET  /api/submissions/{id}    — full submission detail

All return/derive from `Submission`, including its `SyntaxValidationResult`. Nothing here calls
into the (not-yet-built) agent pipeline — that wiring is Milestone 2, per docs/architecture.md.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import (
    EntryMethod,
    Language,
    Submission,
    SubmissionRequest,
    SubmissionSource,
    SubmissionSummary,
)
from app.services.file_handler import (
    UploadValidationError,
    decode_source,
    enforce_size_limit,
    infer_language_from_filename,
)
from app.services.syntax_validator import get_validator

router = APIRouter(prefix="/api/submissions", tags=["submission"])

# In-memory store for Milestone 1. Replaced by persistent storage once the orchestration layer
# (Milestone 2) needs to look submissions up by id across requests/processes.
_SUBMISSIONS: dict[str, Submission] = {}


def _build_submission(
    *,
    language: Language,
    source: SubmissionSource,
    code: str,
    filename: str | None,
    entry_method: EntryMethod | None = None,
) -> Submission:
    validator = get_validator(language.value)
    validation = validator.validate(code)
    submission = Submission(
        language=language,
        source=source,
        filename=filename,
        entry_method=entry_method,
        code=code,
        size_bytes=len(code.encode("utf-8")),
        validation=validation,
    )
    _SUBMISSIONS[submission.id] = submission
    return submission


@router.post("/paste", response_model=Submission, status_code=status.HTTP_201_CREATED)
def submit_pasted_code(payload: SubmissionRequest) -> Submission:
    """Accept directly entered (typed or pasted) source code and validate its syntax."""
    return _build_submission(
        language=payload.language,
        source=SubmissionSource.MANUAL,
        code=payload.code,
        filename=None,
        entry_method=payload.entry_method,
    )


@router.post("/upload", response_model=Submission, status_code=status.HTTP_201_CREATED)
async def submit_uploaded_file(file: UploadFile = File(...)) -> Submission:
    """Accept a Python or Java source file, enforcing size/extension rules, then validate it."""
    try:
        language = infer_language_from_filename(file.filename or "")
        raw = await file.read()
        enforce_size_limit(len(raw))
        code = decode_source(raw)
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return _build_submission(
        language=language,
        source=SubmissionSource.UPLOAD,
        code=code,
        filename=file.filename,
    )


@router.get("", response_model=list[SubmissionSummary])
def list_recent_submissions(limit: int = 10) -> list[SubmissionSummary]:
    """Recent-activity feed, newest first — powers the frontend's activity panel."""
    limit = max(1, min(limit, 50))
    items = sorted(_SUBMISSIONS.values(), key=lambda s: s.created_at, reverse=True)[:limit]
    summaries: list[SubmissionSummary] = []
    for s in items:
        first_line = next((line for line in s.code.splitlines() if line.strip()), "")
        summaries.append(
            SubmissionSummary(
                id=s.id,
                language=s.language,
                source=s.source,
                entry_method=s.entry_method,
                filename=s.filename,
                is_valid=s.validation.is_valid,
                size_bytes=s.size_bytes,
                created_at=s.created_at,
                snippet=first_line[:80],
            )
        )
    return summaries


@router.get("/{submission_id}", response_model=Submission)
def get_submission(submission_id: str) -> Submission:
    submission = _get_submission_or_404(submission_id)
    return submission


def _get_submission_or_404(submission_id: str) -> Submission:
    submission = _SUBMISSIONS.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission


def get_submission_by_id(submission_id: str) -> Submission | None:
    """Used by the analysis route (Milestone 2) to look up a submission without importing
    the private `_SUBMISSIONS` dict directly."""
    return _SUBMISSIONS.get(submission_id)
