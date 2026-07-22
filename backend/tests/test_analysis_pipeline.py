from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    Finding,
    FindingLocation,
    Language,
    Severity,
    Submission,
    SubmissionSource,
    SyntaxValidationResult,
)
from app.services.analysis_orchestrator import AnalysisOrchestrator

client = TestClient(app)

SAMPLES_DIR = Path(__file__).parent / "samples"


def _sample_code(filename: str) -> str:
    return (SAMPLES_DIR / filename).read_text(encoding="utf-8")


def test_submission_findings_for_python_sample():
    resp = client.post(
        "/api/submissions/paste",
        json={"language": "python", "code": _sample_code("vulnerable_python_sample.txt")},
    )
    assert resp.status_code == 201
    submission_id = resp.json()["id"]

    findings_resp = client.get(f"/api/submissions/{submission_id}/findings")
    assert findings_resp.status_code == 200
    findings_body = findings_resp.json()
    findings = findings_body["findings"]
    assert findings
    assert any(f["category"] == "code-quality" for f in findings)
    assert any(f["category"] == "security" for f in findings)
    assert any("SQL Injection" in f["title"] for f in findings)
    assert any("Hardcoded secret" in f["title"] for f in findings)


def test_submission_findings_for_java_sample():
    resp = client.post(
        "/api/submissions/paste",
        json={"language": "java", "code": _sample_code("vulnerable_java_sample.txt")},
    )
    assert resp.status_code == 201
    submission_id = resp.json()["id"]

    findings_resp = client.get(f"/api/submissions/{submission_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()["findings"]
    assert findings
    assert any("Overly permissive access control" == f["title"] for f in findings)
    assert any("CSRF protection disabled" == f["title"] for f in findings)
    assert any("Potential SQL Injection" == f["title"] for f in findings)


def test_submission_findings_unknown_submission_404():
    resp = client.get("/api/submissions/unknown-id/findings")
    assert resp.status_code == 404


def test_orchestrator_runs_agents_in_parallel():
    class SlowCodeAgent:
        def run(self, submission: Submission) -> list[Finding]:
            time.sleep(0.2)
            return [
                Finding(
                    submission_id=submission.id,
                    category="code-quality",
                    title="slow code finding",
                    description="x",
                    severity=Severity.LOW,
                    location=FindingLocation(start_line=1, end_line=1, snippet="x"),
                )
            ]

    class SlowSecurityAgent:
        def run(self, submission: Submission) -> list[Finding]:
            time.sleep(0.2)
            return [
                Finding(
                    submission_id=submission.id,
                    category="security",
                    title="slow security finding",
                    description="x",
                    severity=Severity.HIGH,
                    location=FindingLocation(start_line=1, end_line=1, snippet="x"),
                    owasp_category="A03:2021 - Injection",
                    cwe_id="CWE-89",
                )
            ]

    submission = Submission(
        language=Language.PYTHON,
        source=SubmissionSource.MANUAL,
        code="print('x')",
        size_bytes=10,
        validation=SyntaxValidationResult(is_valid=True, errors=[]),
    )
    orchestrator = AnalysisOrchestrator(
        code_analysis_agent=SlowCodeAgent(),
        security_agent=SlowSecurityAgent(),
    )

    start = time.perf_counter()
    summary = orchestrator.run(submission)
    elapsed = time.perf_counter() - start

    assert len(summary.findings) == 2
    assert elapsed < 0.35
