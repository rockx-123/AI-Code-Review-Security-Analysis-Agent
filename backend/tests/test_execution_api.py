from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app

client = TestClient(app)


def test_execution_disabled_by_default():
    get_settings.cache_clear()
    resp = client.post(
        "/api/execution/run",
        json={"language": "python", "code": "print('hi')"},
    )
    assert resp.status_code == 403
    assert "disabled" in resp.json()["detail"].lower()


def test_execution_runs_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/execution/run",
            json={"language": "python", "code": "print('hello from test')"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ran"] is True
        assert "hello from test" in body["stdout"]
        assert body["exit_code"] == 0
        assert body["timed_out"] is False
    finally:
        monkeypatch.delenv("ENABLE_CODE_EXECUTION", raising=False)
        get_settings.cache_clear()


def test_execution_rejects_invalid_syntax_even_when_enabled(monkeypatch):
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/execution/run",
            json={"language": "python", "code": "def broken(\n"},
        )
        assert resp.status_code == 422
    finally:
        monkeypatch.delenv("ENABLE_CODE_EXECUTION", raising=False)
        get_settings.cache_clear()


def test_execution_python_timeout(monkeypatch):
    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")
    monkeypatch.setenv("EXECUTION_TIMEOUT_SECONDS", "1")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/execution/run",
            json={"language": "python", "code": "while True:\n    pass\n"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["timed_out"] is True
    finally:
        monkeypatch.delenv("ENABLE_CODE_EXECUTION", raising=False)
        monkeypatch.delenv("EXECUTION_TIMEOUT_SECONDS", raising=False)
        get_settings.cache_clear()


def test_java_execution_not_broken_by_memory_rlimit(monkeypatch):
    """
    Regression test: RLIMIT_AS (256MB) applied to a JVM process makes it fail to even start
    (the JVM reserves far more virtual address space than that just to boot), independent of
    javac/java actually being installed. This test skips itself if no JDK is present, since the
    point is to catch the rlimit regression specifically, not to assert a JDK exists in CI.
    """
    import shutil

    if not shutil.which("javac") or not shutil.which("java"):
        import pytest
        pytest.skip("No JDK on this host — nothing to regress-test here.")

    monkeypatch.setenv("ENABLE_CODE_EXECUTION", "true")
    get_settings.cache_clear()
    try:
        resp = client.post(
            "/api/execution/run",
            json={
                "language": "java",
                "code": (
                    "public class Calculator {\n"
                    "    public static int add(int a, int b) { return a + b; }\n"
                    "    public static void main(String[] args) {\n"
                    "        System.out.println(add(4, 7));\n"
                    "    }\n"
                    "}\n"
                ),
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ran"] is True, f"Java execution failed unexpectedly: {body}"
        assert "11" in body["stdout"]
    finally:
        monkeypatch.delenv("ENABLE_CODE_EXECUTION", raising=False)
        get_settings.cache_clear()
