# Data Models

Canonical shapes shared across backend, frontend, and every agent. Milestone 1 implements
`Submission` fully; `Finding` and `ReviewSummary` are defined now (and mirrored as Pydantic
models in `backend/app/models/schemas.py`) so later milestones don't change the contract shape,
only fill it in.

## Submission (Milestone 1 — implemented)

```
Submission
├── id: str (uuid)
├── language: "python" | "java"
├── source: "paste" | "upload"
├── filename: str | null              # present when source == "upload"
├── code: str                          # raw source text
├── size_bytes: int
├── created_at: datetime
└── validation: SyntaxValidationResult
    ├── is_valid: bool
    ├── errors: ValidationError[]
    │   ├── line: int | null
    │   ├── column: int | null
    │   └── message: str
    └── validated_at: datetime
```

## Finding (contract defined in M1, populated starting M2)

```
Finding
├── id: str (uuid)
├── submission_id: str
├── category: "code-quality" | "security"
├── title: str
├── description: str
├── severity: "critical" | "high" | "medium" | "low" | "info"
├── location: { start_line: int, end_line: int, snippet: str }
├── owasp_category: str | null         # e.g. "A03:2021 - Injection" (security findings only)
├── cwe_id: str | null                 # e.g. "CWE-89"                (security findings only)
├── knowledge_base_refs: string[]      # ids of RAG chunks that grounded this finding
└── remediation: Remediation | null    # populated by Remediation Agent (M3)
    ├── explanation: str
    ├── fixed_snippet: str
    └── references: string[]
```

## ReviewSummary (contract defined in M1, populated starting M3)

```
ReviewSummary
├── submission_id: str
├── generated_at: datetime
├── counts_by_severity: { critical: int, high: int, medium: int, low: int, info: int }
├── top_risks: Finding[]               # highest-severity subset, capped
├── narrative: str                     # PR-comment-style human-readable summary
└── findings: Finding[]                # full list
```

## Knowledge base document / chunk (Milestone 1 — implemented)

```
KnowledgeDocument
├── id: str
├── title: str
├── category: "owasp" | "secure-coding" | "code-smell"
├── source_path: str
└── chunks: KnowledgeChunk[]
    ├── id: str
    ├── text: str
    ├── heading: str | null
    ├── embedding: float[]        # stored in Chroma, not returned over the API
    └── metadata: { doc_id, category, chunk_index }
```

## Severity scale (fixed project-wide)

| Level | Meaning |
|---|---|
| `critical` | Immediately exploitable, high impact (e.g. unauthenticated RCE-class SQLi) |
| `high` | Serious risk, likely exploitable with some effort |
| `medium` | Real issue, limited exploitability or impact |
| `low` | Best-practice deviation, low real-world risk |
| `info` | Style/readability note, no security or correctness impact |
