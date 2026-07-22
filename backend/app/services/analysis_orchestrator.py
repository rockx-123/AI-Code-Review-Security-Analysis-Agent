from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.schemas import Finding, ReviewSummary, Severity, SeverityCounts, Submission
from app.services.code_analysis_agent import CodeAnalysisAgent
from app.services.security_vulnerability_agent import SecurityVulnerabilityAgent

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


class AnalysisOrchestrator:
    def __init__(
        self,
        *,
        code_analysis_agent: CodeAnalysisAgent | None = None,
        security_agent: SecurityVulnerabilityAgent | None = None,
    ) -> None:
        self._code_analysis_agent = code_analysis_agent or CodeAnalysisAgent()
        self._security_agent = security_agent or SecurityVulnerabilityAgent()

    def run(self, submission: Submission) -> ReviewSummary:
        findings: list[Finding] = []
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(self._code_analysis_agent.run, submission),
                pool.submit(self._security_agent.run, submission),
            ]
            for future in as_completed(futures):
                findings.extend(future.result())

        findings.sort(
            key=lambda f: (
                _SEVERITY_ORDER[f.severity],
                f.location.start_line,
                f.title.lower(),
            )
        )
        counts = _severity_counts(findings)
        return ReviewSummary(
            submission_id=submission.id,
            counts_by_severity=counts,
            top_risks=findings[:5],
            narrative="",
            findings=findings,
        )


def _severity_counts(findings: list[Finding]) -> SeverityCounts:
    counts = SeverityCounts()
    for finding in findings:
        if finding.severity == Severity.CRITICAL:
            counts.critical += 1
        elif finding.severity == Severity.HIGH:
            counts.high += 1
        elif finding.severity == Severity.MEDIUM:
            counts.medium += 1
        elif finding.severity == Severity.LOW:
            counts.low += 1
        else:
            counts.info += 1
    return counts
