"""
Milestone 2, Task 4: "Validate agent detection accuracy across sample Python and Java
codebases containing known quality issues and vulnerabilities."

Two directions of validation:
  1. True positives — the vulnerable fixtures must trigger every rule they were built to
     demonstrate (asserted by rule_id, not just "some finding exists").
  2. False positives — the clean fixtures must trigger *zero* findings from either agent, in
     either language. A tool that flags reasonably-written code erodes trust fast.

Fixture files live in tests/fixtures/ and are plain source text — never imported or executed,
only read and passed to the analyzers as strings.
"""
from pathlib import Path

from app.agents.code_analysis_java import analyze_java
from app.agents.code_analysis_python import analyze_python
from app.agents.security_java import analyze_java_security
from app.agents.security_python import analyze_python_security

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _read(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def _rule_ids(findings) -> set[str]:
    return {f.rule_id for f in findings}


# ---------------------------------------------------------------------------
# True positives — vulnerable fixtures
# ---------------------------------------------------------------------------

def test_python_vulnerable_fixture_code_quality_detections():
    findings = analyze_python(_read("vulnerable_sample.py"))
    rule_ids = _rule_ids(findings)
    expected = {
        "long-parameter-list", "deep-nesting", "bare-except",
        "god-class", "mutable-default-argument",
    }
    missing = expected - rule_ids
    assert not missing, f"Code Analysis Agent (Python) missed expected rules: {missing}"


def test_python_vulnerable_fixture_security_detections():
    findings = analyze_python_security(_read("vulnerable_sample.py"))
    rule_ids = _rule_ids(findings)
    expected = {
        "sql-injection", "hardcoded-secret", "weak-password-hash", "csrf-protection-disabled",
    }
    missing = expected - rule_ids
    assert not missing, f"Security Vulnerability Agent (Python) missed expected rules: {missing}"

    sql_findings = [f for f in findings if f.rule_id == "sql-injection"]
    assert len(sql_findings) >= 2, "Expected both SQL injection variants (concat and f-string) to be caught"
    assert all(f.severity == "critical" for f in sql_findings)
    assert all(f.owasp_category and f.owasp_category.startswith("A03") for f in sql_findings)
    assert all(f.cwe_id == "CWE-89" for f in sql_findings)


def test_java_vulnerable_fixture_code_quality_detections():
    findings = analyze_java(_read("vulnerable_sample.java"))
    rule_ids = _rule_ids(findings)
    expected = {"long-parameter-list", "deep-nesting", "swallowed-exception", "god-class"}
    missing = expected - rule_ids
    assert not missing, f"Code Analysis Agent (Java) missed expected rules: {missing}"


def test_java_vulnerable_fixture_security_detections():
    findings = analyze_java_security(_read("vulnerable_sample.java"))
    rule_ids = _rule_ids(findings)
    expected = {
        "sql-injection", "hardcoded-secret", "weak-password-hash",
        "reflected-xss", "csrf-protection-disabled",
    }
    missing = expected - rule_ids
    assert not missing, f"Security Vulnerability Agent (Java) missed expected rules: {missing}"


# ---------------------------------------------------------------------------
# False positives — clean fixtures must come back empty
# ---------------------------------------------------------------------------

def test_python_clean_fixture_has_no_findings():
    quality = analyze_python(_read("clean_sample.py"))
    security = analyze_python_security(_read("clean_sample.py"))
    assert quality == [], f"Unexpected code-quality false positives: {[f.rule_id for f in quality]}"
    assert security == [], f"Unexpected security false positives: {[f.rule_id for f in security]}"


def test_java_clean_fixture_has_no_findings():
    quality = analyze_java(_read("clean_sample.java"))
    security = analyze_java_security(_read("clean_sample.java"))
    assert quality == [], f"Unexpected code-quality false positives: {[f.rule_id for f in quality]}"
    assert security == [], f"Unexpected security false positives: {[f.rule_id for f in security]}"


# ---------------------------------------------------------------------------
# Location-specific flagging (Milestone 2, Task 2 requirement)
# ---------------------------------------------------------------------------

def test_findings_carry_specific_line_numbers_not_just_file_level():
    findings = analyze_python_security(_read("vulnerable_sample.py"))
    for f in findings:
        assert f.start_line > 0
        assert f.end_line >= f.start_line
        assert f.snippet.strip(), "Every finding should carry a non-empty source snippet"
