"""
FastAPI entrypoint. Run with:

    uvicorn app.main:app --reload --port 8000

Interactive API docs at /docs once running.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.execution import router as execution_router
from app.api.routes.jokes import router as jokes_router
from app.api.routes.knowledge_base import router as knowledge_base_router
from app.api.routes.submission import router as submission_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="AI Code Review & Security Analysis Agent",
    description=(
        "Milestone 1: Code Submission Module + Secure Coding Knowledge Base (RAG). "
        "Code Analysis, Security Vulnerability, Remediation, and PR Summary agents, the "
        "Conversational Assistant, and report export land in Milestones 2-4."
    ),
    version="0.1.0-m1",
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
app.include_router(jokes_router)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "milestone": 1, "code_execution_enabled": settings.enable_code_execution}
