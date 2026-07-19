"""
Code execution endpoint — EXPERIMENTAL, disabled by default.

Read docs/code-execution-safety.md before setting ENABLE_CODE_EXECUTION=true, especially
before any public deployment. See app/services/code_runner.py for exactly what protection
this does and doesn't provide.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.config import get_settings
from app.models.schemas import ExecutionRequest, ExecutionResult
from app.services.code_runner import run_code
from app.services.syntax_validator import get_validator

router = APIRouter(prefix="/api/execution", tags=["execution"])


@router.post("/run", response_model=ExecutionResult)
def run_submitted_code(payload: ExecutionRequest) -> ExecutionResult:
    settings = get_settings()
    if not settings.enable_code_execution:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Code execution is disabled on this server. Read "
                "docs/code-execution-safety.md, then set ENABLE_CODE_EXECUTION=true in .env "
                "to enable it — off by default intentionally, especially for public deployments."
            ),
        )

    # Re-validate server-side rather than trusting the client's "it passed validation" state —
    # never execute code we haven't independently confirmed parses.
    validator = get_validator(payload.language.value)
    validation = validator.validate(payload.code)
    if not validation.is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Code has syntax errors — fix validation issues before running.",
        )

    return run_code(payload.language.value, payload.code)
