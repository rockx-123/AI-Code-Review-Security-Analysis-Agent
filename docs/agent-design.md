# Agent Design

Each agent is specified here as a contract (inputs → outputs → responsibilities) so that
Milestones 2–4 can implement them independently against a fixed interface. Only the responsibility
and interface are frozen in Milestone 1 — internal implementation (rules, prompts, models) is a
later-milestone decision.

## 1. Code Analysis Agent — *Milestone 2*

- **Input:** `Submission` (code, language)
- **Output:** `Finding[]` where `category = "code-quality"`
- **Responsibilities:** structural review — code smells, design anti-patterns, complexity,
  readability/naming issues, error-handling smells (see `docs/research-notes.md §3`).
- **Not responsible for:** security vulnerabilities (owned by the Security Vulnerability Agent)
  or suggesting fixes (owned by the Remediation Agent) — it only detects and describes.

## 2. Security Vulnerability Agent — *Milestone 2*

- **Input:** `Submission`
- **Output:** `Finding[]` where `category = "security"`, each carrying `owasp_category` and `cwe_id`
- **Responsibilities:** detect OWASP-standard vulnerability patterns (SQL injection, XSS, CSRF,
  hardcoded secrets, insecure authentication, broken access control — see research notes table),
  assign a severity score per `docs/data-models.md`.
- **Grounding:** cross-references the RAG knowledge base to confirm a pattern match against the
  documented guideline rather than relying purely on heuristics, and to attach the source
  guideline reference to each finding.

## 3. Remediation Agent — *Milestone 3*

- **Input:** `Finding[]` (from both agents above) + `Submission`
- **Output:** the same `Finding[]`, each enriched with `remediation: { explanation, fixed_snippet, references[] }`
- **Responsibilities:** produce a specific, actionable fix per finding — not generic advice.
  Retrieves relevant secure-coding guidance from the RAG knowledge base to ground its explanation
  and cites the source document(s) it used.

## 4. PR Summary Agent — *Milestone 3*

- **Input:** enriched `Finding[]`
- **Output:** `ReviewSummary` (see data models) — counts by severity, top risks, a short
  human-readable narrative suitable for pasting into a pull request comment.
- **Responsibilities:** compression and prioritization, not new analysis. Must not introduce
  findings that didn't come from the upstream agents.

## 5. Conversational Code Assistant — *Milestone 4*

- **Input:** a user question + conversation history + the active `Submission`/`ReviewSummary` as context
- **Output:** a grounded answer, plus the knowledge base source(s) it drew from
- **Responsibilities:** RAG-powered Q&A restricted to secure coding / the current findings —
  "why is this flagged," "show me another example of this fix," "what does OWASP say about X."
- **Grounding contract:** every answer must be able to cite which knowledge base chunk(s)
  informed it (`app/rag/vector_store.py::query()` already returns source metadata for this reason).

## Orchestration contract (implemented in Milestone 2)

```python
class Orchestrator:
    def run(self, submission: Submission) -> ReviewSummary:
        # 1. fan out
        quality_findings = CodeAnalysisAgent().run(submission)
        security_findings = SecurityVulnerabilityAgent().run(submission)
        findings = quality_findings + security_findings

        # 2. enrich
        findings = RemediationAgent().run(findings, submission)

        # 3. summarize
        return PRSummaryAgent().run(findings)
```

Each agent is isolated: a failure in one agent should not prevent the others from completing
(handled by per-agent try/except + partial-result reporting at the orchestration layer — planned
for Milestone 2, noted here so the interface anticipates it).
