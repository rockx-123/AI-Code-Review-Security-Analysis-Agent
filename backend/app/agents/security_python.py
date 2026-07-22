"""
Security Vulnerability Agent — Python detectors.

Pattern-based (regex + light AST checks), not a full data-flow/taint analysis. That's a real
limitation worth being upfront about: these rules catch the common, textbook-shaped versions of
each vulnerability class (see docs/research-notes.md §1 for the OWASP mapping) — a determined or
unusually-structured piece of code can evade them, and some patterns can false-positive on code
that only *looks* like the vulnerable shape. Each detector's docstring below states its precision
trade-off explicitly rather than implying more rigor than a regex pass actually provides.
"""
from __future__ import annotations

import ast
import re

from app.agents.models import RawFinding


def _snippet(lines: list[str], line: int, context: int = 1) -> str:
    s = max(1, line - context)
    e = min(len(lines), line + context)
    return "\n".join(lines[s - 1:e])


# ---------------------------------------------------------------------------
# A03:2021 - Injection (SQL Injection)
# ---------------------------------------------------------------------------
# Two passes: (1) find variable assignments where the RHS is built via string concatenation,
# %-formatting, .format(), or an f-string containing an interpolated value — these variables are
# "tainted". (2) find execute()/executemany() calls whose argument is either a tainted variable
# or itself built the same way inline. This catches both the "query built on the line above,
# executed below" pattern (the most common real-world shape) and the same-line case. Still not
# real taint analysis — a tainted variable reassigned to something safe before use, or taint
# threaded through a helper function, won't be tracked correctly.
_SQL_EXEC_CALL = re.compile(r"\.(execute|executemany)\s*\(\s*(.+?)\)\s*$")
_ASSIGN_VAR = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+)$")
_FSTRING_START = re.compile(r"^f['\"]")
_CONCAT_WITH_STRING = re.compile(r"['\"].*['\"]\s*\+|\+\s*\w*['\"]|\+\s*[A-Za-z_]\w*\s*(\+|$)")
_PERCENT_FORMAT = re.compile(r"['\"].*%s.*['\"]\s*%")
_DOT_FORMAT_CALL = re.compile(r"\.format\s*\(")
_LOOKS_LIKE_SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


def _is_dynamically_built(expr: str) -> bool:
    return bool(
        _FSTRING_START.match(expr.strip())
        or _CONCAT_WITH_STRING.search(expr)
        or _PERCENT_FORMAT.search(expr)
        or _DOT_FORMAT_CALL.search(expr)
    )


def _find_sql_injection(lines: list[str]) -> list[RawFinding]:
    findings: list[RawFinding] = []
    tainted_vars: dict[str, int] = {}  # variable name -> line it was tainted on

    for i, line in enumerate(lines, start=1):
        assign_m = _ASSIGN_VAR.match(line)
        if assign_m:
            var_name, rhs = assign_m.group(1), assign_m.group(2)
            if _is_dynamically_built(rhs) and _LOOKS_LIKE_SQL.search(rhs):
                tainted_vars[var_name] = i
            elif var_name in tainted_vars:
                del tainted_vars[var_name]  # reassigned to something else — stop tracking

        exec_m = _SQL_EXEC_CALL.search(line)
        if not exec_m:
            continue
        arg = exec_m.group(2).strip()

        if _is_dynamically_built(arg):
            findings.append(RawFinding(
                category="security", rule_id="sql-injection",
                title="Possible SQL injection",
                description=(
                    "This database call builds its query text by concatenating or formatting a "
                    "variable directly into the SQL string, instead of passing values as separate "
                    "query parameters. An attacker who controls that variable can alter the query's "
                    "meaning entirely. Use parameterized queries — pass values as a tuple/dict "
                    "argument to execute() and use placeholders (%s, ?, or :name) in the SQL text "
                    "itself — rather than building the string yourself."
                ),
                severity="critical", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-89",
            ))
        elif arg in tainted_vars:
            taint_line = tainted_vars[arg]
            findings.append(RawFinding(
                category="security", rule_id="sql-injection",
                title="Possible SQL injection",
                description=(
                    f"'{arg}' is built on line {taint_line} by concatenating or formatting a value "
                    "directly into a SQL string, then passed to this database call unchanged. An "
                    "attacker who controls that value can alter the query's meaning entirely. Use "
                    "parameterized queries — pass values as a separate tuple/dict argument to "
                    "execute() with placeholders in the SQL text — rather than building the string "
                    "yourself."
                ),
                severity="critical", start_line=i, end_line=i,
                snippet=_snippet(lines, taint_line) if taint_line != i else _snippet(lines, i),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-89",
            ))
    return findings


# ---------------------------------------------------------------------------
# A02/A05 - Hardcoded secrets
# ---------------------------------------------------------------------------
# Two independent signals: (1) a literal string assigned to a variable whose name suggests a
# secret, or (2) a literal matching a known secret-prefix pattern regardless of variable name.
# Placeholder-looking values (empty, "changeme", "xxx", "your-key-here", etc.) are excluded to
# cut down on noise from example/template code.
_SENSITIVE_NAME_WORDS = {
    "api", "key", "apikey", "secret", "secretkey", "password", "passwd", "pwd", "access",
    "accesskey", "auth", "authtoken", "token", "private", "privatekey", "credential", "credentials",
}


def _is_sensitive_name(identifier: str) -> bool:
    """
    Tokenizes an identifier (splitting on underscores and camelCase boundaries) and checks
    whether any resulting word is a known sensitive term. A plain `\\bpassword\\b` regex on the
    whole identifier does NOT catch `db_password` — underscore counts as a word character in
    regex, so there's no boundary between `db_` and `password` — this tokenizing approach avoids
    that class of false negative.
    """
    words = re.findall(r"[A-Za-z]+", identifier)
    normalized = {w.lower() for w in words}
    # Also check adjacent-word-pairs joined (catches "api_key" -> "apikey")
    joined_pairs = {(words[i] + words[i + 1]).lower() for i in range(len(words) - 1)}
    return bool(normalized & _SENSITIVE_NAME_WORDS or joined_pairs & _SENSITIVE_NAME_WORDS)
_ASSIGNMENT_TO_LITERAL = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]([^'\"]+)['\"]")
_PLACEHOLDER_VALUES = {
    "", "changeme", "change_me", "your-key-here", "your_key_here", "xxx", "xxxx", "todo",
    "placeholder", "example", "test", "fixme", "insert_key_here", "<your-key>", "none",
}
_KNOWN_SECRET_PREFIXES = re.compile(r"\b(sk_live_|sk_test_|AKIA[0-9A-Z]{12,}|ghp_|gho_|xox[baprs]-)")


def _find_hardcoded_secrets(lines: list[str]) -> list[RawFinding]:
    findings = []
    flagged_lines: set[int] = set()

    # Check the more specific, higher-confidence signal first (a recognized key format is about
    # as close to certain as static analysis gets); only fall back to the generic
    # sensitive-variable-name heuristic for a line if nothing more specific already matched it.
    for i, line in enumerate(lines, start=1):
        prefix_match = _KNOWN_SECRET_PREFIXES.search(line)
        if prefix_match:
            findings.append(RawFinding(
                category="security", rule_id="hardcoded-secret",
                title="Hardcoded secret (recognized key format)",
                description=(
                    "This line contains a string matching a known API key/token format "
                    f"(prefix '{prefix_match.group(1)}'). Treat this key as compromised and rotate "
                    "it even if you remove this line — git history can retain it."
                ),
                severity="critical", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A02:2021 - Cryptographic Failures", cwe_id="CWE-798",
            ))
            flagged_lines.add(i)

    for i, line in enumerate(lines, start=1):
        if i in flagged_lines:
            continue
        m = _ASSIGNMENT_TO_LITERAL.match(line)
        if not m:
            continue
        var_name, value = m.group(1), m.group(2)
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
                severity="high", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A02:2021 - Cryptographic Failures", cwe_id="CWE-798",
            ))
    return findings


# ---------------------------------------------------------------------------
# A07:2021 - Insecure authentication (weak password hashing)
# ---------------------------------------------------------------------------
_WEAK_HASH = re.compile(r"hashlib\.(md5|sha1)\s*\(")


def _find_weak_hashing(lines: list[str]) -> list[RawFinding]:
    findings = []
    for i, line in enumerate(lines, start=1):
        m = _WEAK_HASH.search(line)
        if m:
            algo = m.group(1).upper()
            findings.append(RawFinding(
                category="security", rule_id="weak-password-hash",
                title=f"Weak hash algorithm ({algo})",
                description=(
                    f"{algo} is a fast, non-memory-hard hash — it's unsuitable for password storage "
                    "because modern hardware can brute-force it at high speed. If this hash is used for "
                    "passwords or other secrets, switch to a memory-hard algorithm (Argon2id or bcrypt). "
                    f"{algo} may be fine for non-security checksums (e.g. cache keys) — check the context "
                    "before treating this as a must-fix."
                ),
                severity="high", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A07:2021 - Identification and Authentication Failures", cwe_id="CWE-916",
            ))
    return findings


# ---------------------------------------------------------------------------
# A03:2021 - Injection (Cross-Site Scripting)
# ---------------------------------------------------------------------------
# Same tainted-variable-tracking approach as SQL injection above: a variable built from an
# f-string/concatenation containing what looks like an HTML tag is "tainted"; passing that
# variable (or building the string inline) into a sink function that doesn't auto-escape is
# flagged. Still heuristic and narrow by design — real XSS detection needs to know the
# rendering context, which a regex pass cannot fully determine — but tracking the variable
# across lines catches the common "build the HTML, then render it below" shape that a
# same-line-only check would miss entirely.
_XSS_SINK_CALL = re.compile(r"\b(?:render_template_string|mark_safe|HttpResponse)\s*\(\s*(.+?)\)\s*$")
_HTML_TAG_PATTERN = re.compile(r"<[a-zA-Z]+[^>]*>")


def _find_xss(lines: list[str]) -> list[RawFinding]:
    findings = []
    tainted_vars: dict[str, int] = {}

    for i, line in enumerate(lines, start=1):
        assign_m = _ASSIGN_VAR.match(line)
        if assign_m:
            var_name, rhs = assign_m.group(1), assign_m.group(2)
            if _is_dynamically_built(rhs) and _HTML_TAG_PATTERN.search(rhs):
                tainted_vars[var_name] = i
            elif var_name in tainted_vars:
                del tainted_vars[var_name]

        sink_m = _XSS_SINK_CALL.search(line)
        if not sink_m:
            continue
        arg = sink_m.group(1).strip()

        if _is_dynamically_built(arg) and _HTML_TAG_PATTERN.search(arg):
            findings.append(RawFinding(
                category="security", rule_id="reflected-xss",
                title="Possible Cross-Site Scripting (XSS)",
                description=(
                    "This builds an HTML string with an f-string/concatenation and passes it to a "
                    "rendering function that does not auto-escape (unlike a proper template file). "
                    "If any interpolated value comes from user input, the browser will execute it as "
                    "markup. Use a templating engine with auto-escaping enabled (render_template with "
                    "a .html file, not render_template_string with an f-string), or explicitly escape "
                    "user-controlled values before interpolating them."
                ),
                severity="high", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-79",
            ))
        elif arg in tainted_vars:
            taint_line = tainted_vars[arg]
            findings.append(RawFinding(
                category="security", rule_id="reflected-xss",
                title="Possible Cross-Site Scripting (XSS)",
                description=(
                    f"'{arg}' is built on line {taint_line} as an HTML string via f-string/"
                    "concatenation, then passed to a rendering function that does not auto-escape. "
                    "If any interpolated value comes from user input, the browser will execute it as "
                    "markup. Use a templating engine with auto-escaping enabled, or explicitly escape "
                    "user-controlled values before interpolating them."
                ),
                severity="high", start_line=i, end_line=i,
                snippet=_snippet(lines, taint_line) if taint_line != i else _snippet(lines, i),
                owasp_category="A03:2021 - Injection", cwe_id="CWE-79",
            ))
    return findings


# ---------------------------------------------------------------------------
# A01:2021 - Broken Access Control (best-effort, file-level heuristic)
# ---------------------------------------------------------------------------
# Looks for a route handler that fetches an object by an ID taken from the URL/request, with no
# reference to an authorization/ownership check (current_user, request.user, session, @login_required,
# permission, etc.) anywhere in the same function. This is the least reliable detector here —
# many false negatives (a check done via decorator or middleware elsewhere won't be seen) and
# some false positives (a genuinely public, unauthenticated endpoint gets flagged too). Included
# because missing object-level authorization is common and high-impact when it does happen, but
# every finding from this rule should be read as "worth a human look," not "confirmed vulnerable."
_ROUTE_DECORATOR = re.compile(r"@\w+\.route\s*\(.*<[\w:]+>")
_OBJECT_FETCH = re.compile(r"\.(get|filter|query)\w*\s*\([^)]*\bid\b[^)]*\)|\.(get|filter|query)\w*\s*\([^)]*_id\b[^)]*\)", re.IGNORECASE)
_AUTH_HINTS = re.compile(r"current_user|request\.user|login_required|permission|session\[|@login_required|authorize", re.IGNORECASE)


def _find_broken_access_control(code: str, lines: list[str]) -> list[RawFinding]:
    findings = []
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        decorators_text = " ".join(ast.dump(d) for d in node.decorator_list)
        if "route" not in decorators_text.lower():
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        func_source = "\n".join(lines[start - 1:end])
        has_path_param = bool(re.search(r"<[\w:]+>", "\n".join(lines[max(0, start - 2):start])))
        fetches_by_id = bool(_OBJECT_FETCH.search(func_source))
        has_auth_hint = bool(_AUTH_HINTS.search(func_source)) or bool(_AUTH_HINTS.search(decorators_text))
        if has_path_param and fetches_by_id and not has_auth_hint:
            findings.append(RawFinding(
                category="security", rule_id="missing-object-authorization",
                title="Possible missing authorization check",
                description=(
                    f"'{node.name}' fetches an object using an ID from the route, but no "
                    "authorization/ownership check (current_user, login_required, permission check, "
                    "etc.) is visible in this function. If this endpoint should be restricted, verify "
                    "the requester is allowed to access this specific object — heuristic finding, "
                    "please confirm manually rather than treating as certain."
                ),
                severity="medium", start_line=start, end_line=start,
                snippet=_snippet(lines, start),
                owasp_category="A01:2021 - Broken Access Control", cwe_id="CWE-862",
            ))
    return findings


# ---------------------------------------------------------------------------
# A01:2021 - Broken Access Control (CSRF — explicit exemption, Django)
# ---------------------------------------------------------------------------
# Unlike the broken-access-control heuristic below, this one is high-confidence: `@csrf_exempt`
# is an unambiguous, deliberate opt-out of Django's CSRF protection, always worth surfacing.
_CSRF_EXEMPT = re.compile(r"@csrf_exempt\b")


def _find_csrf_exempt(lines: list[str]) -> list[RawFinding]:
    findings = []
    for i, line in enumerate(lines, start=1):
        if _CSRF_EXEMPT.search(line):
            findings.append(RawFinding(
                category="security", rule_id="csrf-protection-disabled",
                title="CSRF protection explicitly exempted",
                description=(
                    "This view is decorated with `@csrf_exempt`, turning off Django's CSRF "
                    "protection for it. Sometimes intentional (e.g. a webhook endpoint verified by "
                    "signature instead), but confirm that's actually the case — if this view accepts "
                    "state-changing requests from an authenticated, cookie-based session, exempting "
                    "it from CSRF protection leaves it exposed."
                ),
                severity="high", start_line=i, end_line=i,
                snippet=_snippet(lines, i),
                owasp_category="A01:2021 - Broken Access Control", cwe_id="CWE-352",
            ))
    return findings


def analyze_python_security(code: str) -> list[RawFinding]:
    lines = code.splitlines()
    findings: list[RawFinding] = []
    findings += _find_sql_injection(lines)
    findings += _find_hardcoded_secrets(lines)
    findings += _find_weak_hashing(lines)
    findings += _find_xss(lines)
    findings += _find_broken_access_control(code, lines)
    findings += _find_csrf_exempt(lines)
    return findings
