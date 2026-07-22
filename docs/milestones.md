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
| 1 | Build Code Analysis Agent — detect code smells, complexity issues, design anti-patterns, poor practices with severity scoring | ✅ |
| 2 | Build Security Vulnerability Agent — OWASP-standard checks with type/severity and location-specific flags | ✅ |
| 3 | Implement multi-agent orchestration — run Code Analysis + Security agents in parallel and merge outputs | ✅ |
| 4 | Validate detection behavior on sample Python and Java code with known issues/vulnerabilities | ✅ |

**Artifacts:** `backend/app/services/code_analysis_agent.py`,
`backend/app/services/security_vulnerability_agent.py`,
`backend/app/services/analysis_orchestrator.py`,
`backend/app/api/routes/submission.py`,
`backend/tests/test_analysis_pipeline.py`,
`backend/tests/samples/vulnerable_python_sample.txt`,
`backend/tests/samples/vulnerable_java_sample.txt`.

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
