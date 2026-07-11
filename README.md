<<<<<<< HEAD
# AI Code Review & Security Analysis Agent

An intelligent multi-agent platform that automatically analyzes Python and Java source code
for quality issues, OWASP-standard security vulnerabilities, and best-practice violations —
then explains *why* it matters and *how* to fix it, grounded in a retrieval-augmented (RAG)
secure-coding knowledge base.

> **Build status: Milestone 1 of 4 complete.** See [`docs/milestones.md`](docs/milestones.md)
> for the full roadmap and what's implemented so far.

---

## What's in this repo right now (Milestone 1)

Milestone 1 focused on the *foundation* the other three milestones build on:

| Deliverable | Status | Where |
|---|---|---|
| Research: OWASP standards, secure coding guidelines, code smells, RAG architecture | ✅ Done | [`docs/research-notes.md`](docs/research-notes.md) |
| System architecture, agent responsibilities, orchestration flow, data models | ✅ Done | [`docs/architecture.md`](docs/architecture.md), [`docs/agent-design.md`](docs/agent-design.md), [`docs/data-models.md`](docs/data-models.md) |
| Code Submission Module (paste + upload, Python/Java, syntax validation) | ✅ Done | `backend/app/api/routes/submission.py`, `backend/app/services/syntax_validator.py`, `frontend/` |
| Secure Coding Knowledge Base + RAG ingestion pipeline (chunk → embed → index) | ✅ Done | `backend/app/rag/` |

The Code Analysis, Security Vulnerability, Remediation, and PR Summary **agents**, the
conversational assistant, findings UI, and report export are **not built yet** — those are
Milestones 2–4. The pipeline stepper you see in the UI is a preview of what's coming; only the
submission + validation step is functional today.

---

## Project layout

```
ai-code-review-agent/
├── docs/                      # Architecture, agent design, data models, research, roadmap
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app entrypoint
│   │   ├── config.py          # Settings (env-driven)
│   │   ├── models/schemas.py  # Pydantic request/response + core data models
│   │   ├── api/routes/        # HTTP endpoints (submission, knowledge base)
│   │   ├── services/          # Syntax validation, file handling
│   │   ├── rag/               # Knowledge base docs + chunk/embed/index pipeline
│   │   └── utils/             # Logging, shared helpers
│   ├── tests/                 # Unit tests for Milestone 1 modules
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  # Glass-UI single-page app (submission + KB explorer)
├── .gitignore
└── README.md
```

## Getting started (local dev)

**Requirements:** Python 3.11+, `pip`, a modern browser. No external API key is required —
embeddings run locally via `sentence-transformers` / Chroma's built-in embedding function.

```bash
# 1. Backend
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# 2. Build the knowledge base index (one-time, or whenever docs change)
python -m app.rag.ingest

# 3. Frontend
cd ../frontend
python -m http.server 5173
# open http://localhost:5173
```

The frontend calls the backend at `http://localhost:8000` by default (see `frontend/assets/app.js`,
`API_BASE_URL`).

## Running tests

```bash
cd backend
pytest -q
```

## Roadmap

See [`docs/milestones.md`](docs/milestones.md). In short:

- **Milestone 1 (done):** Research, architecture, Code Submission Module, secure-coding RAG knowledge base.
- **Milestone 2:** Code Analysis Agent + Security Vulnerability Agent + multi-agent orchestration.
- **Milestone 3:** Remediation Agent + PR Summary Agent + Findings/Severity UI.
- **Milestone 4:** Conversational Code Assistant (RAG Q&A), report generation/export, polish & hardening.
=======
# AI-Code-Review-Security-Analysis-Agent
AI powered multi agent code review and security analysis platform with RAG-based secure coding assistant for Python and Java
>>>>>>> 4cfaf7c2d03a0d0986334b2fd58fd1b99b3fdedc
