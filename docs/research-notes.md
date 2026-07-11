# Research Notes — Milestone 1, Task 1

Summary of the standards and patterns this project is built against. These notes drive both the
Security Vulnerability Agent's rule set (Milestone 2) and the contents of the RAG knowledge base
(Milestone 1, Task 4).

## 1. OWASP standards used as the vulnerability taxonomy

- **OWASP Top 10 (Web Application Security Risks)** — the primary classification system for
  findings. Categories relevant to source-level static review: Injection (A03), Broken Access
  Control (A01), Cryptographic Failures (A02), Insecure Design (A04), Security Misconfiguration
  (A05), Identification & Authentication Failures (A07), Software & Data Integrity Failures (A08).
- **OWASP ASVS (Application Security Verification Standard)** — used for verification-level
  detail (e.g., "passwords must be hashed with a memory-hard algorithm") that's more actionable
  than the Top 10 category alone. Referenced by the Remediation Agent for fix specificity.
- **OWASP Secure Coding Practices Quick Reference Guide** — checklist-style guidance
  (input validation, output encoding, auth, session management, access control, error handling
  and logging, data protection) used as the backbone of the knowledge base chunks.
- **CWE (Common Weakness Enumeration)** — used as a secondary ID alongside OWASP categories so
  findings can carry both a human-readable category (e.g. "SQL Injection") and a stable identifier
  (e.g. CWE-89), matching how most security tooling and dashboards report.

Vulnerability classes explicitly in scope for Milestone 2:

| Class | OWASP category | Typical CWE |
|---|---|---|
| SQL Injection | A03: Injection | CWE-89 |
| Cross-Site Scripting (XSS) | A03: Injection | CWE-79 |
| CSRF | A01: Broken Access Control | CWE-352 |
| Hardcoded secrets/credentials | A02/A05 | CWE-798 |
| Insecure authentication | A07 | CWE-287 |
| Broken access control | A01 | CWE-284/CWE-862 |

## 2. Secure coding guidelines

- Input validation at trust boundaries; never trust client-supplied data.
- Parameterized queries / prepared statements instead of string-built SQL.
- Output encoding appropriate to context (HTML, attribute, JS, URL) to prevent XSS.
- Secrets in environment variables or a secrets manager, never in source or version control.
- Principle of least privilege for access control checks, enforced server-side.
- Fail securely: errors should not leak stack traces, internal paths, or credentials.
- Use vetted crypto libraries; never hand-roll hashing/encryption.

## 3. Code smell & design anti-pattern categories

Used by the Code Analysis Agent (Milestone 2) independent of security concerns:

- **Structural smells:** long method, large class/god object, long parameter list, deep nesting.
- **Duplication:** copy-pasted logic across functions/files.
- **Complexity:** high cyclomatic complexity, excessive branching.
- **Coupling/cohesion:** feature envy, inappropriate intimacy between classes, low cohesion.
- **Naming & readability:** non-descriptive identifiers, magic numbers/strings.
- **Error handling smells:** bare `except:`/swallowed exceptions, empty catch blocks in Java.

## 4. RAG architecture used for the knowledge base

- **Chunking:** guideline documents are split into semantically coherent chunks (heading-aware,
  ~200–400 tokens with overlap) rather than fixed-length windows, so a chunk retrieved for
  "SQL injection remediation" doesn't cut off mid-explanation.
- **Embedding:** local sentence-embedding model (via Chroma's default embedding function,
  `all-MiniLM-L6-v2` class model) so the pipeline works fully offline with no external API key.
  The embedding provider is swappable (see `backend/app/config.py`) if a hosted embedding model
  is preferred later.
- **Vector store:** Chroma (embedded, file-backed at `backend/data/vector_store/`) for
  Milestone 1–3. Chosen for zero external infra and a straightforward upgrade path to a hosted
  vector DB if the project needs to scale past local development.
- **Retrieval pattern:** top-k similarity search with metadata filtering (by `category`, e.g.
  `owasp`, `code-smell`, `remediation`) so the future Conversational Assistant (Milestone 4) and
  Remediation Agent (Milestone 3) can scope retrieval to the relevant knowledge slice instead of
  searching the whole corpus indiscriminately.
