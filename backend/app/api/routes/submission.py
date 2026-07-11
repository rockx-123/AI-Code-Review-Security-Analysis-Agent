"""
Code Submission Module — Milestone 1, Task 3.

Two entry points, one shared validation path:
  POST /api/submissions/paste   — direct code paste
  POST /api/submissions/upload  — file upload (.py / .java)

Both return a `Submission` including its `SyntaxValidationResult`. Nothing here calls into the
(not-yet-built) agent pipeline — that wiring is Milestone 2, per docs/architecture.md.
"""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.models.schemas import Language, Submission, SubmissionRequest, SubmissionSource
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


def _build_submission(*, language: Language, source: SubmissionSource, code: str, filename: str | None) -> Submission:
    validator = get_validator(language.value)
    validation = validator.validate(code)
    submission = Submission(
        language=language,
        source=source,
        filename=filename,
        code=code,
        size_bytes=len(code.encode("utf-8")),
        validation=validation,
    )
    _SUBMISSIONS[submission.id] = submission
    return submission


@router.post("/paste", response_model=Submission, status_code=status.HTTP_201_CREATED)
def submit_pasted_code(payload: SubmissionRequest) -> Submission:
    """Accept directly pasted source code and run syntax validation against it."""
    return _build_submission(
        language=payload.language,
        source=SubmissionSource.PASTE,
        code=payload.code,
        filename=None,
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


@router.get("/{submission_id}", response_model=Submission)
def get_submission(submission_id: str) -> Submission:
    submission = _SUBMISSIONS.get(submission_id)
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return submission
