# Milestone Roadmap

This file is the single source of truth for what's built vs. planned. Update the status column
as each milestone lands.

## Milestone 1 — Foundation (Week 1–2) — ✅ Complete

| # | Task | Status |
|---|---|---|
| 1 | Study OWASP vulnerability standards, secure coding guidelines, code smell patterns, RAG architecture | ✅ |
| 2 | Design system architecture, agent responsibilities, orchestration flow, data models | ✅ |
| 3 | Build Code Submission Module — paste + upload for Python/Java, syntax validation | ✅ |
| 4 | Build Secure Coding Knowledge Base — index OWASP guidelines & best practices via chunking, embedding, vector store | ✅ |

**Artifacts:** `docs/architecture.md`, `docs/agent-design.md`, `docs/data-models.md`,
`docs/research-notes.md`, `backend/app/api/routes/submission.py`,
`backend/app/services/syntax_validator.py`, `backend/app/rag/*`, `frontend/*`.

## Milestone 2 — Analysis & Detection (Week 3–4) — ✅ Complete

| # | Task | Status |
|---|---|---|
| 1 | Build Code Analysis Agent — code smells, complexity, design anti-patterns, poor practices, severity-scored | ✅ |
| 2 | Build Security Vulnerability Agent — OWASP-standard vulnerabilities, classified by type/severity, location-specific | ✅ |
| 3 | Implement multi-agent orchestration — Code Analysis + Security Vulnerability run in parallel, merged into unified findings list | ✅ |
| 4 | Validate agent detection accuracy across sample Python/Java codebases with known issues | ✅ |

**Artifacts:** `backend/app/agents/` (code analysis + security detectors for Python and Java,
orchestrator), `backend/app/api/routes/analysis.py`, `docs/detection-rules.md` (full rule catalog
+ honest precision/limitation notes for every rule), `backend/tests/test_code_analysis_agent.py`,
`backend/tests/test_security_agent.py`, `backend/tests/test_orchestrator.py`,
`backend/tests/test_analysis_api.py`.

**What's detected:** long methods, long parameter lists, deep nesting, high cyclomatic
complexity, god classes, mutable default arguments, swallowed/bare exceptions (code quality); SQL
injection, hardcoded secrets, weak password hashing, reflected XSS, CSRF protection disabled, and
a best-effort missing-authorization heuristic (security) — mapped to OWASP categories and CWE IDs,
each security finding grounded with a knowledge base reference. Both agents run concurrently via a
thread pool and are isolated from each other's failures (see `orchestrator.py`).

**Not yet built (Milestone 3):** remediation suggestions/corrected code, the PR-style narrative
summary, and the polished findings/severity UI. The API contract already has slots for all three
(`Finding.remediation`, `ReviewSummary.narrative`) so their shape won't change when filled in.

## Milestone 3 — Remediation & Reporting UI (planned)

- Implement **Remediation Agent**: fix suggestions + corrected code snippets per finding, grounded in the RAG knowledge base.
- Implement **PR Summary Agent**: rolls up all findings into a structured, human-readable review summary.
- Build the **Findings Display & Severity Scoring** UI (developer portal view): filterable, severity-coded results panel.

## Milestone 4 — Conversational Assistant & Export (planned)

- Implement the **Conversational Code Assistant**: RAG-grounded Q&A over flagged issues and secure coding guidance, with chat UI.
- Build **Code Review Report Generation & Export** (PDF/Markdown export of findings + remediation roadmap).
- End-to-end polish: performance, error states, accessibility pass, final UI/UX refinement.

---

### Definition of done (applies to every milestone)

- Code is organized under the module boundaries in `docs/architecture.md` — no milestone should require restructuring earlier work.
- New agents/services expose a typed request/response contract (see `docs/data-models.md`) so the orchestration layer and UI don't need to change shape later.
- Tests accompany new backend logic in `backend/tests/`.
- This file is updated to move the milestone from *planned* to *complete* with a list of artifacts, mirroring the Milestone 1 entry above.
