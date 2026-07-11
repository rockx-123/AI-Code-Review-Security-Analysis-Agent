# System Architecture

## 1. High-level view

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND (glass UI)                         │
│  Code Submission  │  Pipeline Status  │  Findings (M3)  │  Chat (M4)      │
└───────────────────────────────┬────────────────────────────────────────-┘
                                 │ REST (JSON) — fetch()
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                            BACKEND — FastAPI                             │
│                                                                          │
│   ┌────────────────────┐        ┌────────────────────────────────────┐  │
│   │ Submission Module   │        │ Multi-Agent Orchestration (M2)     │  │
│   │  - paste / upload   │──────▶│  Code Analysis │ Security Vuln      │  │
│   │  - syntax validate  │        │  Remediation   │ PR Summary   (M3)  │  │
│   └────────────────────┘        └────────────────┬───────────────────┘  │
│                                                     │ retrieval           │
│                                                     ▼                    │
│                                   ┌─────────────────────────────────┐    │
│                                   │  RAG Pipeline                    │    │
│                                   │  chunk → embed → Chroma index    │    │
│                                   │  + Conversational Assistant (M4) │    │
│                                   └─────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                 backend/data/vector_store  (persisted Chroma index)
```

## 2. Module boundaries

| Module | Owns | Depends on |
|---|---|---|
| **Code Submission Module** (M1) | Accepting pasted code / uploaded `.py` / `.java` files, syntax validation, creating a `Submission` record | Nothing else in-app |
| **Secure Coding Knowledge Base + RAG Pipeline** (M1) | Source documents, chunking, embedding, vector index, retrieval API | Nothing else in-app |
| **Multi-Agent Orchestration** (M2) | Running the 4 review agents against a `Submission`, aggregating `Finding[]` | Submission Module, RAG Pipeline |
| **Findings & Severity UI** (M3) | Rendering `Finding[]` with severity, filters | Orchestration output |
| **Conversational Assistant** (M4) | Chat over `Finding[]` + knowledge base | RAG Pipeline, Findings |
| **Report Generation/Export** (M4) | Turning `Finding[]` + summary into exportable Markdown/PDF | Orchestration output |

This boundary is deliberate: the Submission Module and RAG Pipeline built in Milestone 1 are
consumed by, but never depend on, the agents built later — so Milestones 2–4 are additive, not
refactors.

## 3. Orchestration flow (target end-state, implemented incrementally)

```
1. Developer pastes code or uploads a file
        ↓
2. Code Submission Module validates syntax → creates Submission{id, language, code, source}
        ↓  (Milestone 2 wires this trigger)
3. Orchestrator fans out to:
        Code Analysis Agent ─┐
        Security Vulnerability Agent ─┤→ each returns Finding[]
        ↓ (after both complete)
4. Remediation Agent consumes Finding[] → attaches fix + corrected snippet per finding
        ↓
5. PR Summary Agent consumes enriched Finding[] → ReviewSummary
        ↓
6. Findings UI renders ReviewSummary; Conversational Assistant can be asked about any Finding;
   Report module exports ReviewSummary
```

Steps 1–2 are implemented in Milestone 1. Steps 3–6 are stubbed as data contracts
(see `docs/data-models.md`) but not yet implemented, so the frontend can already show the
pipeline as a status stepper without lying about what's functional (submission/validation is
live; analysis/remediation/summary are marked "planned").

## 4. Why FastAPI + Chroma

- **FastAPI**: async-friendly, typed request/response via Pydantic (matches the typed
  `Finding`/`Submission` contracts the agents will share), auto-generates OpenAPI docs at `/docs`
  which doubles as a live contract for the frontend and future agents.
- **Chroma**: embedded vector store, no external service to stand up for local development,
  persists to disk (`backend/data/vector_store/`), and has a straightforward path to swap in a
  hosted vector DB later without changing the retrieval interface (`app/rag/vector_store.py` is
  the only file that would need to change).

## 5. Non-functional decisions carried from Milestone 1 forward

- **No required external API key.** Embeddings run locally by default so the project works
  offline; an LLM API key becomes relevant starting Milestone 2 (for agent reasoning) and should
  be read from `.env`, never hardcoded — enforced by `backend/app/config.py`.
- **Language support is Python and Java only**, per the project brief. The submission and
  validation layer is written so a third language could be added by implementing one interface
  (`SyntaxValidator`) rather than branching logic throughout the codebase.
- **Severity scale** fixed at `critical | high | medium | low | info` across the whole project
  (see `docs/data-models.md`) so UI, reports, and agents never disagree on vocabulary.
