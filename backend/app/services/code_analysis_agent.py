from __future__ import annotations

import ast
import re

from app.models.schemas import Finding, FindingLocation, Severity, Submission


def _snippet(lines: list[str], start_line: int, end_line: int) -> str:
    start = max(1, start_line)
    end = max(start, end_line)
    return "\n".join(lines[start - 1:end]).strip()


class _FunctionComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.max_depth = 0
        self._depth = 0

    def _enter(self) -> None:
        self._depth += 1
        self.max_depth = max(self.max_depth, self._depth)

    def _leave(self) -> None:
        self._depth -= 1

    def visit_If(self, node: ast.If) -> None:  # noqa: N802 - AST naming
        self._enter()
        self.generic_visit(node)
        self._leave()

    def visit_For(self, node: ast.For) -> None:  # noqa: N802 - AST naming
        self._enter()
        self.generic_visit(node)
        self._leave()

    def visit_While(self, node: ast.While) -> None:  # noqa: N802 - AST naming
        self._enter()
        self.generic_visit(node)
        self._leave()

    def visit_Try(self, node: ast.Try) -> None:  # noqa: N802 - AST naming
        self._enter()
        self.generic_visit(node)
        self._leave()


class CodeAnalysisAgent:
    def run(self, submission: Submission) -> list[Finding]:
        if submission.language.value == "python":
            return self._analyze_python(submission)
        if submission.language.value == "java":
            return self._analyze_java(submission)
        return []

    def _analyze_python(self, submission: Submission) -> list[Finding]:
        findings: list[Finding] = []
        lines = submission.code.splitlines()
        try:
            tree = ast.parse(submission.code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start_line = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", start_line)
                if len(node.args.args) > 5:
                    findings.append(
                        Finding(
                            submission_id=submission.id,
                            category="code-quality",
                            title="Too many function parameters",
                            description="Function has more than five parameters, reducing readability and maintainability.",
                            severity=Severity.MEDIUM,
                            location=FindingLocation(
                                start_line=start_line,
                                end_line=end_line,
                                snippet=_snippet(lines, start_line, end_line),
                            ),
                        )
                    )
                if (end_line - start_line + 1) > 30:
                    findings.append(
                        Finding(
                            submission_id=submission.id,
                            category="code-quality",
                            title="Long function",
                            description="Function exceeds 30 lines and may be doing too much.",
                            severity=Severity.MEDIUM,
                            location=FindingLocation(
                                start_line=start_line,
                                end_line=end_line,
                                snippet=_snippet(lines, start_line, end_line),
                            ),
                        )
                    )

                complexity_visitor = _FunctionComplexityVisitor()
                complexity_visitor.visit(node)
                if complexity_visitor.max_depth > 3:
                    findings.append(
                        Finding(
                            submission_id=submission.id,
                            category="code-quality",
                            title="High nesting complexity",
                            description="Deeply nested control flow increases cognitive complexity.",
                            severity=Severity.HIGH,
                            location=FindingLocation(
                                start_line=start_line,
                                end_line=end_line,
                                snippet=_snippet(lines, start_line, end_line),
                            ),
                        )
                    )

            if isinstance(node, ast.ExceptHandler) and node.type is None:
                start_line = getattr(node, "lineno", 1)
                end_line = getattr(node, "end_lineno", start_line)
                findings.append(
                    Finding(
                        submission_id=submission.id,
                        category="code-quality",
                        title="Bare exception handler",
                        description="A bare except catches all exceptions and can hide real errors.",
                        severity=Severity.LOW,
                        location=FindingLocation(
                            start_line=start_line,
                            end_line=end_line,
                            snippet=_snippet(lines, start_line, end_line),
                        ),
                    )
                )
        return findings

    def _analyze_java(self, submission: Submission) -> list[Finding]:
        findings: list[Finding] = []
        lines = submission.code.splitlines()
        method_signature = re.compile(
            r"(public|protected|private)\s+(?:static\s+)?[\w<>\[\]]+\s+(\w+)\s*\(([^)]*)\)\s*\{"
        )

        method_starts: list[tuple[int, str, str]] = []
        for idx, line in enumerate(lines, start=1):
            match = method_signature.search(line)
            if match:
                params = [p for p in match.group(3).split(",") if p.strip()]
                if len(params) > 5:
                    findings.append(
                        Finding(
                            submission_id=submission.id,
                            category="code-quality",
                            title="Too many method parameters",
                            description="Method has more than five parameters, which suggests high coupling.",
                            severity=Severity.MEDIUM,
                            location=FindingLocation(
                                start_line=idx,
                                end_line=idx,
                                snippet=_snippet(lines, idx, idx),
                            ),
                        )
                    )
                method_starts.append((idx, match.group(2), line))

        for start_line, _name, _sig in method_starts:
            depth = 0
            end_line = start_line
            for idx in range(start_line - 1, len(lines)):
                depth += lines[idx].count("{")
                depth -= lines[idx].count("}")
                end_line = idx + 1
                if depth == 0:
                    break
            if (end_line - start_line + 1) > 35:
                findings.append(
                    Finding(
                        submission_id=submission.id,
                        category="code-quality",
                        title="Long method",
                        description="Method exceeds 35 lines and may contain multiple responsibilities.",
                        severity=Severity.MEDIUM,
                        location=FindingLocation(
                            start_line=start_line,
                            end_line=end_line,
                            snippet=_snippet(lines, start_line, min(end_line, start_line + 6)),
                        ),
                    )
                )

        method_count = len(method_starts)
        if method_count > 20:
            findings.append(
                Finding(
                    submission_id=submission.id,
                    category="code-quality",
                    title="Potential God Class",
                    description="Class has a large number of methods, indicating a design anti-pattern.",
                    severity=Severity.HIGH,
                    location=FindingLocation(
                        start_line=1,
                        end_line=min(len(lines), 12),
                        snippet=_snippet(lines, 1, min(len(lines), 12)),
                    ),
                )
            )

        return findings
