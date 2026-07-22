"""
Code Analysis Agent — Python detectors.

Uses the standard library `ast` module for exact structural analysis (no regex heuristics
here — Python's own parser gives precise line numbers and real syntax tree structure). Assumes
the code already passed syntax validation; a `SyntaxError` here just yields no findings rather
than raising, since that failure mode is already owned by the Code Submission Module.

Detectors implemented (see docs/research-notes.md §3 for the taxonomy this maps to):
  - Long method            - Long parameter list      - Deep nesting
  - High cyclomatic complexity                         - God class (too many methods)
  - Bare / overly broad exception handling              - Mutable default argument
  - Duplicate function bodies (same file)
"""
from __future__ import annotations

import ast
import hashlib

from app.agents.models import RawFinding

_LONG_METHOD_LINES = 50
_MAX_PARAMS = 5
_MAX_NESTING = 4
_COMPLEXITY_MEDIUM = 10
_COMPLEXITY_HIGH = 15
_GOD_CLASS_METHODS = 15


def _line_span(node: ast.AST) -> tuple[int, int]:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)
    return start, end


def _snippet(lines: list[str], start: int, end: int, max_lines: int = 5) -> str:
    end = min(end, start + max_lines - 1)
    s = max(1, start)
    e = min(len(lines), end)
    return "\n".join(lines[s - 1:e])


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Standard McCabe-style approximation: 1 + one per decision point."""
    complexity = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(n, ast.BoolOp):
            complexity += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            complexity += 1 + len(n.ifs)
    return complexity


def _max_nesting_depth(node: ast.AST) -> int:
    _NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.With, ast.AsyncWith)

    def depth(n: ast.AST, current: int) -> int:
        best = current
        for child in ast.iter_child_nodes(n):
            child_depth = depth(child, current + 1) if isinstance(child, _NESTING_NODES) else depth(child, current)
            best = max(best, child_depth)
        return best

    return depth(node, 0)


def _param_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = fn.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    return [n for n in names if n not in ("self", "cls")]


def _is_noop_body(body: list[ast.stmt]) -> bool:
    """True if a body does nothing meaningful (`pass`, `...`, or just a comment/docstring)."""
    for stmt in body:
        if isinstance(stmt, ast.Pass):
            continue
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, (ast.Constant,)):
            continue
        return False
    return True


def analyze_python(code: str) -> list[RawFinding]:
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []

    lines = code.splitlines()
    findings: list[RawFinding] = []
    seen_bodies: dict[str, tuple[str, int]] = {}  # normalized body hash -> (function name, line)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start, end = _line_span(node)
            num_lines = end - start + 1

            if num_lines > _LONG_METHOD_LINES:
                findings.append(RawFinding(
                    category="code-quality", rule_id="long-method",
                    title="Long method",
                    description=(
                        f"'{node.name}' is {num_lines} lines long (over the {_LONG_METHOD_LINES}-line "
                        "guideline). Long functions are hard to hold in your head at once and often mix "
                        "multiple responsibilities — consider extracting cohesive chunks into smaller, "
                        "well-named helper functions."
                    ),
                    severity="medium", start_line=start, end_line=end,
                    snippet=_snippet(lines, start, end),
                ))

            params = _param_names(node)
            if len(params) > _MAX_PARAMS:
                findings.append(RawFinding(
                    category="code-quality", rule_id="long-parameter-list",
                    title="Long parameter list",
                    description=(
                        f"'{node.name}' takes {len(params)} parameters ({', '.join(params)}). More than "
                        f"{_MAX_PARAMS} usually signals that several of them belong together as an object, "
                        "or that the function is doing more than one job."
                    ),
                    severity="low", start_line=start, end_line=start,
                    snippet=_snippet(lines, start, start),
                ))

            complexity = _cyclomatic_complexity(node)
            if complexity > _COMPLEXITY_HIGH:
                findings.append(RawFinding(
                    category="code-quality", rule_id="high-cyclomatic-complexity",
                    title="High cyclomatic complexity",
                    description=(
                        f"'{node.name}' has an estimated cyclomatic complexity of {complexity} "
                        f"(high: over {_COMPLEXITY_HIGH}). That many independent paths through one function "
                        "makes full test coverage impractical and the logic hard to follow — consider "
                        "decomposing into smaller functions or replacing complex conditionals with a "
                        "lookup table or polymorphism."
                    ),
                    severity="high", start_line=start, end_line=end,
                    snippet=_snippet(lines, start, end),
                ))
            elif complexity > _COMPLEXITY_MEDIUM:
                findings.append(RawFinding(
                    category="code-quality", rule_id="high-cyclomatic-complexity",
                    title="Elevated cyclomatic complexity",
                    description=(
                        f"'{node.name}' has an estimated cyclomatic complexity of {complexity} "
                        f"(elevated: over {_COMPLEXITY_MEDIUM}). Worth keeping an eye on as the function grows."
                    ),
                    severity="medium", start_line=start, end_line=end,
                    snippet=_snippet(lines, start, end),
                ))

            nesting = _max_nesting_depth(node)
            if nesting > _MAX_NESTING:
                findings.append(RawFinding(
                    category="code-quality", rule_id="deep-nesting",
                    title="Deep nesting",
                    description=(
                        f"'{node.name}' nests control structures {nesting} levels deep "
                        f"(over {_MAX_NESTING}). Deeply nested code is hard to trace; guard clauses "
                        "(early returns for edge cases) usually flatten this significantly."
                    ),
                    severity="medium", start_line=start, end_line=end,
                    snippet=_snippet(lines, start, end),
                ))

            # Mutable default argument — a well-known, precisely-detectable real bug source:
            # the default is evaluated once at function definition time and shared across calls.
            for default in (*node.args.defaults, *node.args.kw_defaults):
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(RawFinding(
                        category="code-quality", rule_id="mutable-default-argument",
                        title="Mutable default argument",
                        description=(
                            f"'{node.name}' uses a mutable default argument (a list/dict/set literal). "
                            "Default values are evaluated once at definition time and shared across every "
                            "call that doesn't override them — mutating it in one call leaks into the next. "
                            "Use `None` as the default and create the mutable object inside the function body."
                        ),
                        severity="high", start_line=start, end_line=start,
                        snippet=_snippet(lines, start, start),
                    ))
                    break

            # Duplicate function body detection (exact match, same file).
            if node.body and not _is_noop_body(node.body):
                try:
                    body_dump = "\n".join(ast.dump(stmt, annotate_fields=False) for stmt in node.body)
                except Exception:
                    body_dump = ""
                if body_dump and len(node.body) > 1:
                    body_hash = hashlib.sha256(body_dump.encode()).hexdigest()
                    if body_hash in seen_bodies:
                        other_name, other_line = seen_bodies[body_hash]
                        findings.append(RawFinding(
                            category="code-quality", rule_id="duplicate-logic",
                            title="Duplicate logic",
                            description=(
                                f"'{node.name}' (line {start}) has an identical body to '{other_name}' "
                                f"(line {other_line}). Duplicated logic means a fix applied to one copy but "
                                "not the other silently reintroduces the bug — consider extracting the "
                                "shared logic into one function both call."
                            ),
                            severity="low", start_line=start, end_line=end,
                            snippet=_snippet(lines, start, end),
                        ))
                    else:
                        seen_bodies[body_hash] = (node.name, start)

        elif isinstance(node, ast.ClassDef):
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if len(methods) > _GOD_CLASS_METHODS:
                start, end = _line_span(node)
                findings.append(RawFinding(
                    category="code-quality", rule_id="god-class",
                    title="Large class (god object)",
                    description=(
                        f"'{node.name}' defines {len(methods)} methods (over {_GOD_CLASS_METHODS}). "
                        "A class with this many responsibilities is usually a sign it should be split — "
                        "look for groups of methods that operate on different pieces of state."
                    ),
                    severity="medium", start_line=start, end_line=start,
                    snippet=_snippet(lines, start, start),
                ))

        elif isinstance(node, ast.ExceptHandler):
            line = node.lineno
            if node.type is None:
                findings.append(RawFinding(
                    category="code-quality", rule_id="bare-except",
                    title="Bare except clause",
                    description=(
                        "A bare `except:` catches everything, including `KeyboardInterrupt` and "
                        "`SystemExit`, and often hides real failures. Catch specific exception types instead."
                    ),
                    severity="medium", start_line=line, end_line=line,
                    snippet=_snippet(lines, line, line),
                ))
            elif _is_noop_body(node.body):
                exc_name = ast.dump(node.type, annotate_fields=False) if node.type else "Exception"
                findings.append(RawFinding(
                    category="code-quality", rule_id="swallowed-exception",
                    title="Swallowed exception",
                    description=(
                        "This exception is caught and silently discarded (empty handler body). "
                        "At minimum, log what was caught so the failure isn't invisible."
                    ),
                    severity="medium", start_line=line, end_line=line,
                    snippet=_snippet(lines, line, line),
                ))

    return findings
