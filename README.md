# AI Code Review & Security Analysis Agent

![Milestone](https://img.shields.io/badge/milestone-2%20of%204-4cc9f0)
![Status](https://img.shields.io/badge/status-in%20development-a78bfa)
![Python](https://img.shields.io/badge/python-3.11%2B-34d399)
![License](https://img.shields.io/badge/license-MIT-9aa3b8)

An intelligent multi-agent platform that automatically analyzes Python and Java source code
for quality issues, OWASP-standard security vulnerabilities, and best-practice violations —
then explains *why* it matters and *how* to fix it, grounded in a retrieval-augmented (RAG)
secure-coding knowledge base.

Instead of a slow, subjective manual code review, a developer pastes or uploads code and a
pipeline of specialized agents — Code Analysis, Security Vulnerability, Remediation, and PR
Summary — reviews it automatically, with a RAG-powered conversational assistant on hand for
follow-up questions.

---

## Table of contents

- [Project status](#project-status)
- [Architecture](#architecture)
- [What's implemented](#whats-implemented)
- [Project structure](#project-structure)
- [Getting started](#getting-started)
- [Running tests](#running-tests)
- [Roadmap](#roadmap)

## Project status

**Milestone 2 of 4 complete.** See [`docs/milestones.md`](docs/milestones.md) for the full
roadmap and exactly what's built vs. planned.

| Milestone | Focus | Status |
|---|---|---|
| 1 | Architecture, Code Submission Module, secure-coding RAG knowledge base | Complete |
| 2 | Code Analysis Agent, Security Vulnerability Agent, multi-agent orchestration | Complete |
| 3 | Remediation Agent, PR Summary Agent, Findings & Severity UI | Planned |
| 4 | Conversational Code Assistant, report generation & export, final polish | Planned |

## Architecture

```
Frontend (glass UI)
   │  paste / upload code
   ▼
Code Submission Module ──▶ Multi-Agent Orchestration (M2)
   │                             │  Code Analysis · Security Vulnerability
   │                             │  Remediation · PR Summary (M3)
   ▼                             ▼
                     RAG Pipeline (chunk → embed → Chroma index)
                     + Conversational Assistant (M4)
```

Full detail, agent contracts, and data models: [`docs/architecture.md`](docs/architecture.md),
[`docs/agent-design.md`](docs/agent-design.md), [`docs/data-models.md`](docs/data-models.md).

## What's implemented

**Milestone 1:**

| Deliverable | Where |
|---|---|
| Research: OWASP standards, secure coding guidelines, code smells, RAG architecture | [`docs/research-notes.md`](docs/research-notes.md) |
| System architecture, agent responsibilities, orchestration flow, data models | [`docs/architecture.md`](docs/architecture.md) |
| Code Submission Module — paste + upload, Python/Java syntax validation | `backend/app/api/routes/submission.py`, `backend/app/services/syntax_validator.py`, `frontend/` |
| Secure Coding Knowledge Base + RAG ingestion pipeline (chunk → embed → index) — **3 documents, 22 chunks**, see [`docs/knowledge-base.md`](docs/knowledge-base.md) | `backend/app/rag/` |

**Milestone 2:**

| Deliverable | Where |
|---|---|
| Code Analysis Agent — smells, complexity, design anti-patterns (Python `ast` + Java heuristics) | `backend/app/agents/code_analysis_python.py`, `code_analysis_java.py` |
| Security Vulnerability Agent — SQLi, XSS, secrets, weak hashing, CSRF, broken access control | `backend/app/agents/security_python.py`, `security_java.py` |
| Multi-agent orchestration — parallel execution, merged findings, per-agent failure isolation | `backend/app/agents/orchestrator.py` |
| Detection accuracy validation — real fixtures, both true-positive and false-positive checks | `backend/tests/test_code_analysis_agent.py`, `test_security_agent.py`, `test_orchestrator.py` |
| Full rule catalog with honest precision/limitation notes for every rule | [`docs/detection-rules.md`](docs/detection-rules.md) |

The Remediation Agent, PR Summary Agent, Conversational Assistant, polished findings/severity UI,
and report export are **not built yet** — those land in Milestones 3–4. The pipeline stepper in
the UI previews what's coming.

## Project structure

```
ai-code-review-agent/
├── docs/                      Architecture, agent design, data models, research, roadmap
├── backend/
│   ├── app/
│   │   ├── main.py            FastAPI entrypoint
│   │   ├── config.py          Env-driven settings
│   │   ├── models/schemas.py  Pydantic request/response + core data models
│   │   ├── api/routes/        HTTP endpoints (submission, knowledge base)
│   │   ├── services/          Syntax validation, file handling
│   │   ├── rag/                Knowledge base docs + chunk/embed/index pipeline
│   │   └── utils/
│   ├── tests/                 Unit tests for Milestone 1 modules
│   ├── requirements.txt
│   └── .env.example
├── frontend/                  Glass-UI single-page app (submission + KB explorer)
├── .gitignore
└── README.md
```

## Getting started

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

The frontend calls the backend at `http://localhost:8000` by default
(`frontend/assets/app.js` → `API_BASE_URL`).

## Running tests

```bash
cd backend
pytest -q
```

## Roadmap

See [`docs/milestones.md`](docs/milestones.md) for full detail.

- **Milestone 1 (done):** Research, architecture, Code Submission Module, secure-coding RAG knowledge base.
- **Milestone 2 (done):** Code Analysis Agent + Security Vulnerability Agent + multi-agent orchestration.
- **Milestone 3:** Remediation Agent + PR Summary Agent + Findings/Severity UI.
- **Milestone 4:** Conversational Code Assistant (RAG Q&A), report generation/export, polish & hardening.
