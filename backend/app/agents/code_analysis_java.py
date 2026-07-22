"""
Code Analysis Agent — Java detectors.

No parser available (see java_source_utils.py docstring for why), so this works on
comment/string-masked source text with regex + brace-matching. Precision is inherently lower
than the Python AST-based detectors — flag this honestly rather than implying parser-grade
rigor. Method boundaries are found via a signature regex + brace matching, which handles the
common case well but can be thrown off by unusual formatting (e.g. a `{` on its own line far
from the signature in an unusual style, or lambda-heavy code).
"""
from __future__ import annotations

import re

from app.agents.java_source_utils import find_matching_brace, line_of, mask_strings_and_comments
from app.agents.models import RawFinding

_LONG_METHOD_LINES = 50
_MAX_PARAMS = 5
_MAX_NESTING = 4
_COMPLEXITY_MEDIUM = 10
_COMPLEXITY_HIGH = 15
_GOD_CLASS_METHODS = 15

_METHOD_SIG = re.compile(
    r"(?:public|private|protected)\s+(?:static\s+|final\s+|abstract\s+)*"
    r"[\w<>\[\],\s]+?\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{"
)
_CLASS_SIG = re.compile(r"(?:public|private|protected)?\s*(?:final\s+|abstract\s+)?class\s+(\w+)[^{]*\{")
_EMPTY_CATCH = re.compile(r"catch\s*\([^)]*\)\s*\{\s*\}")
_NESTING_KEYWORDS = re.compile(r"\b(if|for|while|switch)\s*\(")
_DECISION_KEYWORDS = re.compile(r"\b(if|for|while|case|catch)\b|&&|\|\|")


def _count_top_level_commas(param_text: str) -> int:
    """Counts commas at depth 0 — ignores commas inside generic type params like Map<K, V>."""
    depth = 0
    count = 0
    for ch in param_text:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth -= 1
        elif ch == "," and depth == 0:
            count += 1
    return count if param_text.strip() else -1  # -1 sentinel for "no params" -> 0 params


def _snippet(lines: list[str], start: int, end: int, max_lines: int = 5) -> str:
    end = min(end, start + max_lines - 1)
    s = max(1, start)
    e = min(len(lines), end)
    return "\n".join(lines[s - 1:e])


def _brace_nesting_depth(body: str) -> int:
    """Max nesting depth of if/for/while/switch blocks within a method body (already masked)."""
    depth = 0
    max_depth = 0
    stack = []  # brace-open positions we're tracking as "control" braces
    i = 0
    n = len(body)
    while i < n:
        m = _NESTING_KEYWORDS.match(body, i)
        if m:
            # find the opening brace for this control structure (skip to first `{` after the `)`)
            paren_depth = 0
            j = m.end() - 1  # at the '('
            while j < n:
                if body[j] == "(":
                    paren_depth += 1
                elif body[j] == ")":
                    paren_depth -= 1
                    if paren_depth == 0:
                        break
                j += 1
            k = body.find("{", j)
            if k != -1:
                stack.append(k)
                depth += 1
                max_depth = max(max_depth, depth)
                i = k + 1
                continue
        if body[i] == "}" and stack and stack[-1] < i:
            # a naive pop: any closing brace after the most recent tracked open reduces depth.
            # Not perfectly precise for sibling (non-nested) blocks, but errs toward the same
            # or lower depth reading, which is the safer direction for a "flag if too deep" rule.
            stack.pop()
            depth = max(0, depth - 1)
        i += 1
    return max_depth


def analyze_java(code: str) -> list[RawFinding]:
    masked = mask_strings_and_comments(code)
    lines = code.splitlines()
    findings: list[RawFinding] = []

    for m in _METHOD_SIG.finditer(masked):
        method_name = m.group(1)
        params_text = m.group(2)
        open_brace = m.end() - 1
        close_brace = find_matching_brace(masked, open_brace)
        body = masked[open_brace + 1:close_brace]

        start_line = line_of(code, m.start())
        end_line = line_of(code, close_brace)
        num_lines = end_line - start_line + 1

        if num_lines > _LONG_METHOD_LINES:
            findings.append(RawFinding(
                category="code-quality", rule_id="long-method",
                title="Long method",
                description=(
                    f"'{method_name}' is {num_lines} lines long (over the {_LONG_METHOD_LINES}-line "
                    "guideline). Consider extracting cohesive chunks into smaller, well-named helper methods."
                ),
                severity="medium", start_line=start_line, end_line=end_line,
                snippet=_snippet(lines, start_line, end_line),
            ))

        param_count = _count_top_level_commas(params_text) + 1 if params_text.strip() else 0
        if param_count > _MAX_PARAMS:
            findings.append(RawFinding(
                category="code-quality", rule_id="long-parameter-list",
                title="Long parameter list",
                description=(
                    f"'{method_name}' takes {param_count} parameters. More than {_MAX_PARAMS} usually "
                    "signals several belong together as an object, or the method does more than one job."
                ),
                severity="low", start_line=start_line, end_line=start_line,
                snippet=_snippet(lines, start_line, start_line),
            ))

        decision_count = len(_DECISION_KEYWORDS.findall(body))
        complexity = decision_count + 1
        if complexity > _COMPLEXITY_HIGH:
            findings.append(RawFinding(
                category="code-quality", rule_id="high-cyclomatic-complexity",
                title="High cyclomatic complexity",
                description=(
                    f"'{method_name}' has an estimated cyclomatic complexity of {complexity} "
                    f"(high: over {_COMPLEXITY_HIGH}). Consider decomposing into smaller methods."
                ),
                severity="high", start_line=start_line, end_line=end_line,
                snippet=_snippet(lines, start_line, end_line),
            ))
        elif complexity > _COMPLEXITY_MEDIUM:
            findings.append(RawFinding(
                category="code-quality", rule_id="high-cyclomatic-complexity",
                title="Elevated cyclomatic complexity",
                description=(
                    f"'{method_name}' has an estimated cyclomatic complexity of {complexity} "
                    f"(elevated: over {_COMPLEXITY_MEDIUM})."
                ),
                severity="medium", start_line=start_line, end_line=end_line,
                snippet=_snippet(lines, start_line, end_line),
            ))

        nesting = _brace_nesting_depth(body)
        if nesting > _MAX_NESTING:
            findings.append(RawFinding(
                category="code-quality", rule_id="deep-nesting",
                title="Deep nesting",
                description=(
                    f"'{method_name}' nests control structures {nesting} levels deep (over {_MAX_NESTING}). "
                    "Guard clauses (early returns for edge cases) usually flatten this significantly."
                ),
                severity="medium", start_line=start_line, end_line=end_line,
                snippet=_snippet(lines, start_line, end_line),
            ))

    for m in _EMPTY_CATCH.finditer(masked):
        line = line_of(code, m.start())
        findings.append(RawFinding(
            category="code-quality", rule_id="swallowed-exception",
            title="Empty catch block",
            description=(
                "This catch block silently discards the exception. At minimum, log what was caught "
                "so the failure isn't invisible; ideally handle it or rethrow with context."
            ),
            severity="medium", start_line=line, end_line=line,
            snippet=_snippet(lines, line, line),
        ))

    for m in _CLASS_SIG.finditer(masked):
        class_name = m.group(1)
        open_brace = m.end() - 1
        close_brace = find_matching_brace(masked, open_brace)
        class_body = masked[open_brace + 1:close_brace]
        method_count = len(_METHOD_SIG.findall(class_body))
        if method_count > _GOD_CLASS_METHODS:
            line = line_of(code, m.start())
            findings.append(RawFinding(
                category="code-quality", rule_id="god-class",
                title="Large class (god object)",
                description=(
                    f"'{class_name}' defines {method_count} methods (over {_GOD_CLASS_METHODS}). "
                    "Consider splitting by responsibility."
                ),
                severity="medium", start_line=line, end_line=line,
                snippet=_snippet(lines, line, line),
            ))

    return findings
