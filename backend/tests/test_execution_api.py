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
