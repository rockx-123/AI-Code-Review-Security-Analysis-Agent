# Detection Rules — Code Analysis & Security Vulnerability Agents

This is the explicit answer to "what does Milestone 2 actually detect, and how reliable is it?"
Both agents are **pattern-based static analysis** — Python's `ast` module gives exact structural
detection for Python; Java has no parser available in this environment, so its detectors work on
comment/string-masked source text with regex and brace-matching (same approach already used by
`syntax_validator.py`'s Java fallback). Neither is a full data-flow/taint analysis or a
production-grade SAST engine. Every rule below states its precision trade-off plainly.

## Code Analysis Agent (`category: "code-quality"`)

| Rule | Python | Java | Severity | Notes |
|---|---|---|---|---|
| Long method | ✅ AST | ✅ heuristic | medium | >50 lines (identical threshold, both languages) |
| Long parameter list | ✅ AST | ✅ heuristic | low | >5 parameters (`self`/`cls` excluded) |
| Deep nesting | ✅ AST | ✅ heuristic | medium | >4 levels of if/for/while/try |
| High cyclomatic complexity | ✅ AST (exact) | ✅ regex approximation | medium–high | McCabe-style: 1 + decision points; medium >10, high >15 |
| God class (too many methods) | ✅ AST | ✅ heuristic | medium | >15 methods (identical threshold, both languages) |
| Mutable default argument | ✅ AST (exact) | — | high | Python-specific footgun; not applicable to Java |
| Bare / swallowed exception | ✅ AST (exact) | ✅ regex (empty `catch`) | medium | Empty handler body or bare `except:` |
| Duplicate function bodies | ✅ AST (exact, alpha-renamed) | — | low | Same file only; Java version not yet built |

**Python detectors are exact** (real parse tree, real line numbers) — the only imprecision is in
choosing *thresholds* (is 45 lines "long"?), not in whether the structure is correctly identified.

**Java detectors are heuristic** — method boundaries come from a signature regex + brace-counting,
which handles typical formatting well but can be thrown off by unusual styles (e.g. lambda-heavy
code, a method signature split unusually across lines). String/comment content is masked before
scanning specifically so a `{` or keyword sitting inside a string or comment can't be
misinterpreted as real code structure.

## Security Vulnerability Agent (`category: "security"`)

| Rule | OWASP | CWE | Python | Java | Confidence |
|---|---|---|---|---|---|
| SQL Injection | A03:2021 | CWE-89 | ✅ | ✅ | High — tracks tainted variables across lines, not just same-line matches |
| Hardcoded secrets | A02:2021 | CWE-798 | ✅ | ✅ | High for recognized key formats (critical); medium-confidence for name-based heuristic (high) |
| Weak password hashing | A07:2021 | CWE-916 | ✅ (`hashlib.md5`/`sha1`) | ✅ (`MessageDigest` MD5/SHA-1) | High — unambiguous API call |
| Reflected XSS | A03:2021 | CWE-79 | ✅ | ✅ | Medium — tracks tainted variables across lines; narrow sink list |
| CSRF protection disabled | A01:2021 | CWE-352 | ✅ (`@csrf_exempt`) | ✅ (`.csrf().disable()`) | High — unambiguous, deliberate opt-out |
| Missing object-level authorization | A01:2021 | CWE-862 | ✅ (Flask route heuristic) | — | **Low** — most false-negative-prone rule here |

### What "tracks tainted variables across lines" means

The SQL injection and XSS detectors don't just match a single line — they track when a variable
is assigned a dynamically-built (concatenated/f-string/`.format()`) value that looks like SQL or
HTML, and then flag it if that *same variable* later flows into a dangerous call (`execute()`,
`render_template_string()`, etc.), even several lines later. This catches the most common
real-world shape ("build the query, then execute it below") that a same-line-only check would
miss. It's still not full taint analysis — reassigning the variable to something safe in between,
or threading the tainted value through a helper function, won't be tracked correctly.

### Every rule's honest limitation

- **SQL Injection**: parameterized queries (placeholders + a separate values argument) are
  correctly *not* flagged — the detector requires a string-building pattern, not just any
  `execute()` call. Misses taint that flows through a function call boundary.
- **Hardcoded secrets**: placeholder-looking values (`"changeme"`, `"xxx"`, `"your-key-here"`,
  etc.) are excluded to reduce noise on example/template code. A secret assigned to an
  innocuously-named variable (no "key"/"secret"/"password"/etc. in the name, and not matching a
  known key-format prefix) won't be caught.
- **Weak hashing**: flags `MD5`/`SHA-1` regardless of purpose — these algorithms are fine for
  non-security checksums (e.g. cache keys), so a finding here needs a human to check the context,
  not just switch algorithms reflexively. The description text says this explicitly.
- **XSS**: only two Python sinks (`render_template_string`, `mark_safe`, `HttpResponse`) and one
  Java sink pattern (`response.getWriter()`) are recognized. A properly-escaping templating engine
  in normal use (`render_template` with an actual `.html` file) is correctly not flagged, since
  there's no string-building pattern to match — auto-escaping templates are the recommended fix,
  not something this rule is trying to catch.
- **CSRF**: only catches an *explicit, deliberate* opt-out (`@csrf_exempt`, `.csrf().disable()`).
  An endpoint that's vulnerable because CSRF protection was never configured in the first place
  (rather than explicitly turned off) won't be flagged — that would require framework-level
  configuration analysis this milestone doesn't attempt.
- **Missing object-level authorization**: the least reliable rule in this project, by design
  choice (included because the vulnerability class is common and high-impact when it happens, not
  because the detector is precise). It only recognizes Flask-style `@app.route("/x/<id>")`
  handlers, checks for a small fixed list of auth-hint keywords anywhere in the function body, and
  has no visibility into decorators/middleware defined elsewhere that might actually enforce
  authorization out of view. Every finding from this rule is worded as "worth a human look," not
  "confirmed vulnerable," and should be read that way.

## Grounding

Every security finding carries a best-effort `knowledge_base_refs` — the id of the most relevant
chunk retrieved from the Milestone 1 secure coding knowledge base (see
[`docs/knowledge-base.md`](knowledge-base.md)), queried by the finding's title + OWASP category.
This never blocks or fails a finding — if the knowledge base isn't available for any reason,
`knowledge_base_refs` is just empty.

## Validated against

Every rule above was checked against hand-written fixtures with deliberately known issues
(`backend/tests/test_code_analysis_agent.py`, `backend/tests/test_security_agent.py`,
`backend/tests/test_orchestrator.py`) — both a "should fire" case and, where relevant, a "should
NOT fire" case (parameterized queries, auto-escaping templates, an authorization check present,
clean code with no issues at all) to catch false positives as well as false negatives. This is
the Milestone 2, Task 4 deliverable ("validate agent detection accuracy across sample Python and
Java codebases containing known quality issues and vulnerabilities").

## What's explicitly out of scope for Milestone 2

- **Remediation** (fix suggestions, corrected code) — Remediation Agent, Milestone 3
- **PR-style narrative summary** — PR Summary Agent, Milestone 3
- **Findings UI with filtering/severity dashboard** — Milestone 3
- Both are already present as empty/default values in the API response (`ReviewSummary.narrative`,
  `Finding.remediation`) so the contract doesn't change shape when they're filled in later.
