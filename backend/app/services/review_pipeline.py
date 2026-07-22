from __future__ import annotations

import ast
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.schemas import (
    Finding,
    FindingLocation,
    ReviewSummary,
    Severity,
    Submission,
)

_REVIEWS: dict[str, ReviewSummary] = {}

_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


def _build_location(code: str, line_number: int) -> FindingLocation:
    lines = code.splitlines()
    line_index = max(0, min(len(lines) - 1, line_number - 1)) if lines else 0
    snippet = lines[line_index].strip() if lines else ""
    return FindingLocation(start_line=line_index + 1, end_line=line_index + 1, snippet=snippet[:200])


def _finding(
    *,
    submission: Submission,
    category: str,
    title: str,
    description: str,
    severity: Severity,
    line_number: int,
    owasp_category: str | None = None,
    cwe_id: str | None = None,
) -> Finding:
    return Finding(
        submission_id=submission.id,
        category=category,  # type: ignore[arg-type]
        title=title,
        description=description,
        severity=severity,
        location=_build_location(submission.code, line_number),
        owasp_category=owasp_category,
        cwe_id=cwe_id,
    )


class CodeAnalysisAgent:
    def run(self, submission: Submission) -> list[Finding]:
        return self._run_python(submission) if submission.language.value == "python" else self._run_java(submission)

    def _run_python(self, submission: Submission) -> list[Finding]:
        findings: list[Finding] = []
        try:
            tree = ast.parse(submission.code)
        except SyntaxError:
            return findings

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if len(node.args.args) > 5:
                    findings.append(
                        _finding(
                            submission=submission,
                            category="code-quality",
                            title="Function has too many parameters",
                            description="High-arity functions are hard to test and maintain. Prefer grouping related inputs.",
                            severity=Severity.LOW,
                            line_number=node.lineno,
                        )
                    )
                end_line = getattr(node, "end_lineno", node.lineno)
                if end_line - node.lineno + 1 > 25:
                    findings.append(
                        _finding(
                            submission=submission,
                            category="code-quality",
                            title="Long function detected",
                            description="Function length suggests high complexity and lower readability. Consider refactoring into smaller units.",
                            severity=Severity.MEDIUM,
                            line_number=node.lineno,
                        )
                    )

            if isinstance(node, ast.ExceptHandler) and (
                node.type is None or (isinstance(node.type, ast.Name) and node.type.id == "Exception")
            ):
                findings.append(
                    _finding(
                        submission=submission,
                        category="code-quality",
                        title="Overly broad exception handling",
                        description="Catching broad exceptions can hide defects and make failures harder to diagnose.",
                        severity=Severity.MEDIUM,
                        line_number=node.lineno,
                    )
                )

        for line_number, line in enumerate(submission.code.splitlines(), start=1):
            if "print(" in line and not line.strip().startswith("#"):
                findings.append(
                    _finding(
                        submission=submission,
                        category="code-quality",
                        title="Debug print statement found",
                        description="Console prints in production paths are a code-smell. Prefer structured logging.",
                        severity=Severity.INFO,
                        line_number=line_number,
                    )
                )
        return findings

    def _run_java(self, submission: Submission) -> list[Finding]:
        findings: list[Finding] = []
        lines = submission.code.splitlines()
        method_start: int | None = None
        brace_depth = 0
        max_if_depth = 0
        if_depth = 0

        method_regex = re.compile(
            r"(public|protected|private)?\s*(static\s+)?[\w<>\[\]]+\s+\w+\s*\(([^)]*)\)\s*\{"
        )

        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            method_match = method_regex.search(stripped)
            if method_match:
                params = [p for p in method_match.group(3).split(",") if p.strip()]
                if len(params) > 5:
                    findings.append(
                        _finding(
                            submission=submission,
                            category="code-quality",
                            title="Method has too many parameters",
                            description="High-arity methods are difficult to maintain. Consider parameter objects or decomposition.",
                            severity=Severity.LOW,
                            line_number=i,
                        )
                    )
                method_start = i

            if "if (" in stripped:
                if_depth += 1
                max_if_depth = max(max_if_depth, if_depth)

            opening = stripped.count("{")
            closing = stripped.count("}")
            brace_depth += opening - closing
            if closing > 0 and if_depth > 0:
                if_depth = max(0, if_depth - closing)

            if method_start is not None and brace_depth == 0:
                method_length = i - method_start + 1
                if method_length > 30:
                    findings.append(
                        _finding(
                            submission=submission,
                            category="code-quality",
                            title="Long method detected",
                            description="Long methods increase complexity and reduce readability.",
                            severity=Severity.MEDIUM,
                            line_number=method_start,
                        )
                    )
                method_start = None

            if "System.out.println(" in stripped:
                findings.append(
                    _finding(
                        submission=submission,
                        category="code-quality",
                        title="Debug console output found",
                        description="Prefer structured logging over console output in production code.",
                        severity=Severity.INFO,
                        line_number=i,
                    )
                )

        if max_if_depth >= 3:
            findings.append(
                _finding(
                    submission=submission,
                    category="code-quality",
                    title="Deeply nested conditionals",
                    description="Nested conditionals increase cyclomatic complexity and make behavior harder to reason about.",
                    severity=Severity.MEDIUM,
                    line_number=1,
                )
            )
        return findings


class SecurityVulnerabilityAgent:
    _SECRET_RE = re.compile(
        r"""(?ix)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*["'][^"'\n]{6,}["']"""
    )

    def run(self, submission: Submission) -> list[Finding]:
        findings: list[Finding] = []
        lines = submission.code.splitlines()

        for line_number, line in enumerate(lines, start=1):
            if self._SECRET_RE.search(line):
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Hardcoded secret",
                        description="Credentials or sensitive tokens are hardcoded in source code.",
                        severity=Severity.HIGH,
                        line_number=line_number,
                        owasp_category="A02:2021 - Cryptographic Failures",
                        cwe_id="CWE-798",
                    )
                )

            sql_line = line.lower()
            if (
                "execute(" in sql_line
                and any(keyword in sql_line for keyword in ("select", "insert", "update", "delete"))
                and ("+" in line or "f\"" in line or "f'" in line or ".format(" in line)
            ):
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Possible SQL injection",
                        description="Query appears to concatenate or interpolate untrusted input directly into SQL.",
                        severity=Severity.CRITICAL,
                        line_number=line_number,
                        owasp_category="A03:2021 - Injection",
                        cwe_id="CWE-89",
                    )
                )

            if "request.getparameter(" in sql_line and ("print(" in sql_line or "write(" in sql_line):
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Potential reflected XSS",
                        description="User-controlled request data is written to a response without sanitization.",
                        severity=Severity.HIGH,
                        line_number=line_number,
                        owasp_category="A03:2021 - Injection",
                        cwe_id="CWE-79",
                    )
                )

            if re.search(r"return\s+.*request\.(args|form)\.get\(", line):
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Potential reflected XSS",
                        description="User input appears to be returned directly without output encoding.",
                        severity=Severity.HIGH,
                        line_number=line_number,
                        owasp_category="A03:2021 - Injection",
                        cwe_id="CWE-79",
                    )
                )

            if "@csrf_exempt" in line or "csrf = false" in sql_line or "csrf().disable()" in sql_line:
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="CSRF protection appears disabled",
                        description="Cross-Site Request Forgery protections appear to be disabled for request handlers.",
                        severity=Severity.HIGH,
                        line_number=line_number,
                        owasp_category="A01:2021 - Broken Access Control",
                        cwe_id="CWE-352",
                    )
                )

            if re.search(r"\b(password|passwd)\b\s*==\s*['\"].+['\"]", line):
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Insecure authentication check",
                        description="Hardcoded password comparison suggests insecure authentication logic.",
                        severity=Severity.MEDIUM,
                        line_number=line_number,
                        owasp_category="A07:2021 - Identification and Authentication Failures",
                        cwe_id="CWE-287",
                    )
                )

            if ".equals(\"admin\")" in line or ".equals('admin')" in line:
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Insecure authentication check",
                        description="Hardcoded credential or role check can be bypass-prone and brittle.",
                        severity=Severity.MEDIUM,
                        line_number=line_number,
                        owasp_category="A07:2021 - Identification and Authentication Failures",
                        cwe_id="CWE-287",
                    )
                )

            if "permitall()" in sql_line and "admin" in sql_line:
                findings.append(
                    _finding(
                        submission=submission,
                        category="security",
                        title="Potential broken access control",
                        description="Admin route appears to allow unrestricted access.",
                        severity=Severity.CRITICAL,
                        line_number=line_number,
                        owasp_category="A01:2021 - Broken Access Control",
                        cwe_id="CWE-284",
                    )
                )

        return findings


def _agent_error_finding(submission: Submission, category: str, agent_name: str, error: Exception) -> Finding:
    return _finding(
        submission=submission,
        category=category,
        title=f"{agent_name} failed",
        description=f"{agent_name} encountered an error and returned partial results: {error}",
        severity=Severity.INFO,
        line_number=1,
    )


def run_review_pipeline(submission: Submission) -> ReviewSummary:
    agents = {
        "Code Analysis Agent": ("code-quality", CodeAnalysisAgent().run),
        "Security Vulnerability Agent": ("security", SecurityVulnerabilityAgent().run),
    }

    findings: list[Finding] = []
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_to_agent = {
            executor.submit(agent_runner, submission): (agent_name, category)
            for agent_name, (category, agent_runner) in agents.items()
        }

        for future in as_completed(future_to_agent):
            agent_name, category = future_to_agent[future]
            try:
                findings.extend(future.result())
            except Exception as exc:  # pragma: no cover - defensive fallback
                findings.append(_agent_error_finding(submission, category, agent_name, exc))

    findings.sort(
        key=lambda f: (_SEVERITY_ORDER.get(f.severity, 5), f.location.start_line, f.title.lower())
    )

    summary = ReviewSummary(submission_id=submission.id)
    summary.findings = findings

    for finding in findings:
        if finding.severity == Severity.CRITICAL:
            summary.counts_by_severity.critical += 1
        elif finding.severity == Severity.HIGH:
            summary.counts_by_severity.high += 1
        elif finding.severity == Severity.MEDIUM:
            summary.counts_by_severity.medium += 1
        elif finding.severity == Severity.LOW:
            summary.counts_by_severity.low += 1
        elif finding.severity == Severity.INFO:
            summary.counts_by_severity.info += 1

    summary.top_risks = [f for f in findings if f.severity in (Severity.CRITICAL, Severity.HIGH)][:5]
    summary.narrative = (
        f"Detected {len(findings)} findings "
        f"({summary.counts_by_severity.critical} critical, "
        f"{summary.counts_by_severity.high} high, {summary.counts_by_severity.medium} medium)."
    )
    return summary


def analyze_submission(submission: Submission) -> ReviewSummary:
    summary = run_review_pipeline(submission)
    _REVIEWS[submission.id] = summary
    return summary


def get_review(submission_id: str) -> ReviewSummary | None:
    return _REVIEWS.get(submission_id)
