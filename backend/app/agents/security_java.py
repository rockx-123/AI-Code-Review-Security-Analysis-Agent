"""
Security Vulnerability Agent — Java detectors.

Same precision caveat as `security_python.py`: pattern-based on comment/string-masked source
text, not real data-flow analysis. Catches the common, textbook-shaped versions of each
vulnerability class; a determined or unusually-structured snippet can evade these rules.
"""
from __future__ import annotations

import re

from app.agents.java_source_utils import line_of, mask_comments_only
from app.agents.models import RawFinding


def _snippet(lines: list[str], line: int, context: int = 1) -> str:
    s = max(1, line - context)
    e = min(len(lines), line + context)
    return "\n".join(lines[s - 1:e])


# ---------------------------------------------------------------------------
# A03:2021 - Injection (SQL Injection)
# ---------------------------------------------------------------------------
# Flags `Statement`-based execute*() calls whose query argument contains a `+` concatenation
# with what looks like SQL text, and separately flags a `String` variable built the same way
# and later passed to execute*(). PreparedStatement usage with `?` placeholders is the
# recommended fix and is not flagged (no concatenation pattern to match in the first place).
_STATEMENT_EXEC = re.compile(r"\.(executeQuery|executeUpdate|execute)\s*\(\s*([^)]+)\)")
_LOOKS_LIKE_SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_STRING_CONCAT = re.compile(r"\+")
_STRING_VAR_ASSIGN = re.compile(r"\bString\s+(\w+)\s*=\s*(.+?);")


def _find_sql_injection(masked: str, code: str, lines: list[str]) -> list[RawFinding]:
    findings: list[RawFinding] = []
    tainted: dict[str, int] = {}

    for m in _STRING_VAR_ASSIGN.finditer(masked):
        var_name, rhs = m.group(1), m.group(2)
        if _LOOKS_LIKE_SQL.search(rhs) and _STRING_CONCAT.search(rhs):
            tainted[var_name] = line_of(code, m.start())

    for m in _STATEMENT_EXEC.finditer(masked):
        arg = m.group(2).strip()
        line = line_of(code, m.start())
        if _LOOKS_LIKE_SQL.search(arg) and _STRING_CONCAT.search(arg):
            findings.append(RawFinding(
                category="security", rule_id="sql-injection",
                title="Possible SQL injection",
                description=(
                    "This query is built by concatenating a variable directly into the SQL string "
                    "with `Statement`, instead of using `PreparedStatement` with `?` placeholders. An "
                    "attacker who controls that value can alter the query's meaning entirely. Use "
                    "`PreparedStatement` and bind values with `setString`/`setInt`/etc. rather than "
                    "building the query text yourself."
                ),
                severity="critical", start_line=line, end_line=line,
                snippet=_snippet(lines, line),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-89",
            ))
        elif arg in tainted:
            taint_line = tainted[arg]
            findings.append(RawFinding(
                category="security", rule_id="sql-injection",
                title="Possible SQL injection",
                description=(
                    f"'{arg}' is built on line {taint_line} by concatenating a value directly into a "
                    "SQL string, then passed to `Statement` unchanged. Use `PreparedStatement` with "
                    "`?` placeholders and bind values via setter methods instead of building the query "
                    "text yourself."
                ),
                severity="critical", start_line=line, end_line=line,
                snippet=_snippet(lines, taint_line) if taint_line != line else _snippet(lines, line),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-89",
            ))
    return findings


# ---------------------------------------------------------------------------
# A02/A05 - Hardcoded secrets
# ---------------------------------------------------------------------------
_SENSITIVE_NAME_WORDS = {
    "api", "key", "apikey", "secret", "secretkey", "password", "passwd", "pwd", "access",
    "accesskey", "auth", "authtoken", "token", "private", "privatekey", "credential", "credentials",
}
_FIELD_ASSIGN = re.compile(
    r"\b(?:private|public|protected|static|final)?\s*(?:private|public|protected|static|final)?\s*"
    r"String\s+(\w+)\s*=\s*\"([^\"]+)\""
)
_PLACEHOLDER_VALUES = {
    "", "changeme", "change_me", "your-key-here", "your_key_here", "xxx", "xxxx", "todo",
    "placeholder", "example", "test", "fixme", "insert_key_here", "<your-key>", "none",
}
_KNOWN_SECRET_PREFIXES = re.compile(r"\b(sk_live_|sk_test_|AKIA[0-9A-Z]{12,}|ghp_|gho_|xox[baprs]-)")


def _is_sensitive_name(identifier: str) -> bool:
    words = re.findall(r"[A-Za-z]+", identifier)
    normalized = {w.lower() for w in words}
    joined_pairs = {(words[i] + words[i + 1]).lower() for i in range(len(words) - 1)}
    return bool(normalized & _SENSITIVE_NAME_WORDS or joined_pairs & _SENSITIVE_NAME_WORDS)


def _find_hardcoded_secrets(masked: str, code: str, lines: list[str]) -> list[RawFinding]:
    findings = []
    flagged_lines: set[int] = set()

    for m in _KNOWN_SECRET_PREFIXES.finditer(masked):
        line = line_of(code, m.start())
        findings.append(RawFinding(
            category="security", rule_id="hardcoded-secret",
            title="Hardcoded secret (recognized key format)",
            description=(
                "This line contains a string matching a known API key/token format "
                f"(prefix '{m.group(1)}'). Treat this key as compromised and rotate it even if you "
                "remove this line — git history can retain it."
            ),
            severity="critical", start_line=line, end_line=line,
            snippet=_snippet(lines, line),
            owasp_category="A02:2021 - Cryptographic Failures", cwe_id="CWE-798",
        ))
        flagged_lines.add(line)

    for m in _FIELD_ASSIGN.finditer(masked):
        var_name, value = m.group(1), m.group(2)
        line = line_of(code, m.start())
        if line in flagged_lines:
            continue  # already flagged this line via the more specific prefix check above
        if _is_sensitive_name(var_name) and value.strip().lower() not in _PLACEHOLDER_VALUES and len(value) >= 4:
            findings.append(RawFinding(
                category="security", rule_id="hardcoded-secret",
                title="Hardcoded secret",
                description=(
                    f"'{var_name}' is assigned a literal string value directly in source code. "
                    "Secrets committed to source control are exposed to anyone with repository "
                    "access (and persist in git history even if later removed). Move this to an "
                    "environment variable or a secrets manager."
                ),
                severity="high", start_line=line, end_line=line,
                snippet=_snippet(lines, line),
                owasp_category="A02:2021 - Cryptographic Failures", cwe_id="CWE-798",
            ))
    return findings


# ---------------------------------------------------------------------------
# A07:2021 - Insecure authentication (weak hashing)
# ---------------------------------------------------------------------------
_WEAK_HASH = re.compile(r'MessageDigest\.getInstance\s*\(\s*"(MD5|SHA-?1)"\s*\)', re.IGNORECASE)


def _find_weak_hashing(masked: str, code: str, lines: list[str]) -> list[RawFinding]:
    findings = []
    for m in _WEAK_HASH.finditer(masked):
        algo = m.group(1).upper()
        line = line_of(code, m.start())
        findings.append(RawFinding(
            category="security", rule_id="weak-password-hash",
            title=f"Weak hash algorithm ({algo})",
            description=(
                f"{algo} is a fast, non-memory-hard hash — unsuitable for password storage since "
                "modern hardware can brute-force it at high speed. If used for passwords or other "
                "secrets, switch to a memory-hard algorithm (Argon2id or bcrypt, e.g. via Spring "
                f"Security's `BCryptPasswordEncoder`). {algo} may be acceptable for non-security "
                "checksums — check the context before treating this as a must-fix."
            ),
            severity="high", start_line=line, end_line=line,
            snippet=_snippet(lines, line),
            owasp_category="A07:2021 - Identification and Authentication Failures", cwe_id="CWE-916",
        ))
    return findings


# ---------------------------------------------------------------------------
# A03:2021 - Injection (Reflected XSS via servlet response)
# ---------------------------------------------------------------------------
# Tracks a variable assigned from `request.getParameter(...)` as tainted, then flags it if
# written to the response writer with no visible encoding call in between — the same
# cross-line tainted-variable approach used for SQL injection above, rather than only matching
# when both the source and the sink appear on the same line.
_PARAM_ASSIGN = re.compile(r"\bString\s+(\w+)\s*=\s*request\.getParameter\s*\([^)]*\)")
_RESPONSE_WRITE = re.compile(r"getWriter\(\)\.(?:print|println|write)\s*\(([^)]*)\)")
_REQUEST_PARAM_INLINE = re.compile(r"request\.getParameter\s*\(")
_ENCODING_HINT = re.compile(r"HtmlUtils\.htmlEscape|encodeForHTML|StringEscapeUtils|escapeHtml")


def _find_xss(masked: str, code: str, lines: list[str]) -> list[RawFinding]:
    findings = []
    tainted: dict[str, int] = {}

    for m in _PARAM_ASSIGN.finditer(masked):
        tainted[m.group(1)] = line_of(code, m.start())

    for m in _RESPONSE_WRITE.finditer(masked):
        arg = m.group(1).strip()
        line = line_of(code, m.start())
        if _ENCODING_HINT.search(arg):
            continue

        if _REQUEST_PARAM_INLINE.search(arg):
            findings.append(RawFinding(
                category="security", rule_id="reflected-xss",
                title="Possible Cross-Site Scripting (XSS)",
                description=(
                    "A request parameter is written directly to the response with no visible "
                    "encoding call. If this value is attacker-controlled, the browser will execute "
                    "it as markup. Encode it for the HTML context before writing it out (e.g. "
                    "Spring's `HtmlUtils.htmlEscape(...)` or Apache Commons "
                    "`StringEscapeUtils.escapeHtml4(...)`)."
                ),
                severity="high", start_line=line, end_line=line,
                snippet=_snippet(lines, line),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-79",
            ))
        elif arg in tainted:
            taint_line = tainted[arg]
            findings.append(RawFinding(
                category="security", rule_id="reflected-xss",
                title="Possible Cross-Site Scripting (XSS)",
                description=(
                    f"'{arg}' is assigned from `request.getParameter(...)` on line {taint_line}, "
                    "then written directly to the response with no visible encoding call. If this "
                    "value is attacker-controlled, the browser will execute it as markup. Encode it "
                    "for the HTML context before writing it out (e.g. Spring's "
                    "`HtmlUtils.htmlEscape(...)` or Apache Commons `StringEscapeUtils.escapeHtml4(...)`)."
                ),
                severity="high", start_line=line, end_line=line,
                snippet=_snippet(lines, taint_line) if taint_line != line else _snippet(lines, line),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-79",
            ))
    return findings


# ---------------------------------------------------------------------------
# A01:2021 - Broken Access Control (CSRF — explicit disable, Spring Security)
# ---------------------------------------------------------------------------
# Unlike the other Java rules, this one is high-confidence rather than heuristic: explicitly
# calling `.csrf().disable()` is an unambiguous, deliberate opt-out that's always worth
# surfacing for review, regardless of surrounding context.
_CSRF_DISABLED = re.compile(r"\.csrf\s*\(\s*\)\s*\.disable\s*\(\s*\)")


def _find_csrf_disabled(masked: str, code: str, lines: list[str]) -> list[RawFinding]:
    findings = []
    for m in _CSRF_DISABLED.finditer(masked):
        line = line_of(code, m.start())
        findings.append(RawFinding(
            category="security", rule_id="csrf-protection-disabled",
            title="CSRF protection explicitly disabled",
            description=(
                "Spring Security's CSRF protection is explicitly turned off (`.csrf().disable()`). "
                "This is sometimes intentional for stateless token-based APIs (which aren't "
                "CSRF-vulnerable the same way session-cookie-based apps are), but confirm that's "
                "actually the case here — if this application uses cookie-based sessions for "
                "authentication, disabling CSRF protection leaves state-changing endpoints exposed."
            ),
            severity="high", start_line=line, end_line=line,
            snippet=_snippet(lines, line),
            owasp_category="A01:2021 - Broken Access Control", cwe_id="CWE-352",
        ))
    return findings


def analyze_java_security(code: str) -> list[RawFinding]:
    masked = mask_comments_only(code)
    lines = code.splitlines()
    findings: list[RawFinding] = []
    findings += _find_sql_injection(masked, code, lines)
    findings += _find_hardcoded_secrets(masked, code, lines)
    findings += _find_weak_hashing(masked, code, lines)
    findings += _find_xss(masked, code, lines)
    findings += _find_csrf_disabled(masked, code, lines)
    return findings
