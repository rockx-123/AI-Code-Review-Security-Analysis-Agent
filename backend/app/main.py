"""
FastAPI entrypoint. Run with:

    uvicorn app.main:app --reload --port 8000

Interactive API docs at /docs once running.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.execution import router as execution_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.submission import router as submission_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Code Review & Security Analysis Agent",
    description=(
        "Milestone 2: Code Submission + Secure Coding Knowledge Base (RAG) + "
        "Code Analysis and Security Vulnerability agents with parallel orchestration. "
        "Remediation, PR Summary narrative generation, Conversational Assistant, and report "
        "export land in Milestones 3-4."
    ),
    version="0.2.0-m2",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(submission_router)
app.include_router(knowledge_base_router)
app.include_router(execution_router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "milestone": 2, "code_execution_enabled": settings.enable_code_execution}
