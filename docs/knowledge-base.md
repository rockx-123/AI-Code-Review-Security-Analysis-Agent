# Secure Coding Knowledge Base — Contents

This is the explicit, human-readable answer to "what's actually in the knowledge base?" The
underlying documents live in `backend/app/rag/knowledge_base/`; this file is the plain-English
summary of what they contain once indexed.

## Current contents (Milestone 1)

**3 source documents → 22 chunks indexed** in the vector store.

| # | Document | Category | Chunks | Covers |
|---|---|---|---|---|
| 1 | `owasp-top-10.md` | `owasp` | 7 | OWASP Top 10 (2021): Broken Access Control, Cryptographic Failures, Injection (SQL injection, XSS), Insecure Design, Security Misconfiguration, Authentication Failures, Software & Data Integrity Failures |
| 2 | `secure-coding-practices.md` | `secure-coding` | 8 | Input validation, output encoding, authentication & session management, access control, secrets management, error handling & logging, data protection, dependency hygiene |
| 3 | `code-smells-and-design.md` | `code-smell` | 7 | Structural smells (long methods, god objects), duplication, cyclomatic complexity, coupling/cohesion issues, naming/readability, error-handling smells |

These three documents were scoped specifically to cover the vulnerability classes and
code-quality patterns the Milestone 2 agents will need (see
[`docs/research-notes.md`](research-notes.md) for the research this was built from) — this is a
deliberately focused starter set, not an exhaustive security library yet.

## Why this file exists instead of just the code

Chunk counts change automatically whenever a knowledge base document is edited and
re-ingested, so hardcoding a number in the README would go stale. This file is the place to
update by hand whenever the knowledge base grows — treat it as the source of truth to quote when
someone asks "how many knowledge base entries do you have."

## How to verify this yourself, live

With the backend running:

```bash
curl http://localhost:8000/api/knowledge-base/status
```
Returns the current document count, chunk count, and categories directly from the vector store —
useful for confirming this file hasn't drifted from reality.

Or from the frontend: the sidebar's knowledge base status widget shows the same numbers, and the
knowledge base search panel lets you query it directly by category.

## Planned growth

Not committed to a milestone yet, but natural next additions if/when the knowledge base needs to
grow beyond the starter set:

- OWASP ASVS (verification-level detail, more specific than the Top 10 summary)
- CWE reference entries for direct ID-to-guidance lookups
- Python-specific and Java-specific secure coding addenda (framework-specific guidance, e.g. Django/Spring)
- Historical vulnerability examples / CVE writeups for grounding remediation examples with real precedent

## How to add a new document

1. Add a new `.md` file to `backend/app/rag/knowledge_base/` with YAML front matter (`title`, `category`).
2. Re-run the ingestion script: `python -m app.rag.ingest` (add `--reset` for a full rebuild instead of an incremental update).
3. Update the table at the top of this file with the new document, category, and chunk count (shown in the ingestion script's output).
