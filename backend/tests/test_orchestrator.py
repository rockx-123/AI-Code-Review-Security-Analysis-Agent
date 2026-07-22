"""
Tests for the orchestration layer (Milestone 2, Task 3): both agents run and their findings are
merged into one list, per-agent failures are isolated rather than crashing the whole request, and
the aggregation (severity counts, top risks, sorting) is correct.
"""
from datetime import datetime, timezone

import pytest

from app.agents.orchestrator import Orchestrator
from app.models.schemas import Language, Submission, SubmissionSource, SyntaxValidationResult


def _submission(language: Language, code: str) -> Submission:
    return Submission(
        language=language,
        source=SubmissionSource.MANUAL,
        code=code,
        size_bytes=len(code.encode("utf-8")),
        created_at=datetime.now(timezone.utc),
        validation=SyntaxValidationResult(is_valid=True, errors=[]),
    )


def _fake_secret_code() -> str:
    """
    A Python snippet containing a fake Stripe-key-shaped secret, for testing the
    hardcoded-secret detector. Deliberately built by concatenating two fragments rather than
    one contiguous literal — GitHub's push protection (correctly) flags any single unbroken
    "sk_live_" + 24+ alphanumeric characters string as a real credential shape, regardless of
    how obviously fake the wording is, so the fragments are kept apart in the source itself.
    """
    fake_key = "sk_live_" + "NOTAREALKEYUSEDONLYFORUNITTESTS"
    return f'api_key = "{fake_key}"\n'


def test_orchestrator_merges_quality_and_security_findings():
    code = (
        "def get_user(user_id):\n"
        "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
        "    cursor.execute(query)\n\n"
        "def handle(a, b, c, d, e, f, g):\n"
        "    return a\n"
    )
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    categories = {f.category for f in result.findings}
    assert "security" in categories
    assert "code-quality" in categories
    assert result.submission_id == submission.id
    assert result.agent_errors == []


def test_orchestrator_severity_counts_match_findings():
    code = _fake_secret_code()
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    total_from_counts = (
        result.counts_by_severity.critical
        + result.counts_by_severity.high
        + result.counts_by_severity.medium
        + result.counts_by_severity.low
        + result.counts_by_severity.info
    )
    assert total_from_counts == len(result.findings)
    assert result.counts_by_severity.critical >= 1  # the recognized-prefix secret is critical


def test_orchestrator_findings_sorted_by_severity():
    code = (
        "def handle(a, b, c, d, e, f, g):\n"  # low: long-parameter-list
        "    pass\n\n"
        "def get_user(user_id):\n"  # critical: sql-injection
        "    cursor.execute(\"SELECT * FROM users WHERE id = \" + user_id)\n"
    )
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    severities = [f.severity.value for f in result.findings]
    rank = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    assert severities == sorted(severities, key=lambda s: rank[s])


def test_orchestrator_top_risks_is_capped_and_most_severe_first():
    # Six distinct findings guaranteed: one per line below is a separate hardcoded secret.
    lines = [f'secret_{i} = "sk_live_{i}23456789012345"' for i in range(6)]
    code = "\n".join(lines) + "\n"
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    assert len(result.top_risks) <= 5
    assert len(result.top_risks) <= len(result.findings)
    if result.top_risks:
        assert result.top_risks[0].severity == result.findings[0].severity


def test_orchestrator_clean_code_produces_no_findings():
    code = (
        "def calculate_total(cart):\n"
        "    total = 0\n"
        "    for item in cart:\n"
        "        total += item.price\n"
        "    return total\n"
    )
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)
    assert result.findings == []
    assert result.counts_by_severity.critical == 0


def test_orchestrator_isolates_a_failing_agent(monkeypatch):
    """If one agent raises, the other's findings still come back, and the failure is surfaced
    in agent_errors rather than crashing the whole request."""
    import app.agents.orchestrator as orch_module

    def boom(code):
        raise RuntimeError("simulated agent crash")

    monkeypatch.setitem(orch_module._CODE_ANALYSIS_AGENTS, "python", boom)

    code = _fake_secret_code()
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    assert any("Code Analysis Agent failed" in e for e in result.agent_errors)
    # The security agent's findings should still be present despite the other agent crashing.
    assert any(f.category == "security" for f in result.findings)


def test_orchestrator_narrative_and_remediation_not_yet_populated():
    """Contract check: narrative (PR Summary Agent) and remediation (Remediation Agent) are
    explicitly Milestone 3 scope — this locks in that M2 doesn't accidentally start filling
    them in with a placeholder that later looks like a real value."""
    code = _fake_secret_code()
    submission = _submission(Language.PYTHON, code)
    result = Orchestrator().run(submission)

    assert result.narrative == ""
    assert all(f.remediation is None for f in result.findings)
