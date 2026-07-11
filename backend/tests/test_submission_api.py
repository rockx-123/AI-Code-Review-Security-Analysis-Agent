import io

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_paste_valid_python():
    resp = client.post(
        "/api/submissions/paste",
        json={"language": "python", "code": "def add(a, b):\n    return a + b\n"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["validation"]["is_valid"] is True
    assert body["language"] == "python"
    assert body["source"] == "paste"


def test_paste_invalid_python_returns_error_detail():
    resp = client.post(
        "/api/submissions/paste",
        json={"language": "python", "code": "def add(a, b)\n    return a + b\n"},
    )
    assert resp.status_code == 201  # request succeeds; the *code* is invalid, not the API call
    body = resp.json()
    assert body["validation"]["is_valid"] is False
    assert body["validation"]["errors"]


def test_paste_empty_code_rejected():
    resp = client.post("/api/submissions/paste", json={"language": "python", "code": ""})
    assert resp.status_code == 422


def test_upload_valid_python_file():
    file_content = b"def add(a, b):\n    return a + b\n"
    resp = client.post(
        "/api/submissions/upload",
        files={"file": ("Add.py", io.BytesIO(file_content), "text/x-python")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "Add.py"
    assert body["validation"]["is_valid"] is True


def test_upload_rejects_disallowed_extension():
    resp = client.post(
        "/api/submissions/upload",
        files={"file": ("script.rb", io.BytesIO(b"puts 'hi'"), "text/plain")},
    )
    assert resp.status_code == 422


def test_upload_rejects_oversized_file():
    from app.config import get_settings

    get_settings.cache_clear()
    huge = b"x" * (get_settings().max_upload_size_bytes + 1)
    resp = client.post(
        "/api/submissions/upload",
        files={"file": ("Big.java", io.BytesIO(huge), "text/plain")},
    )
    assert resp.status_code == 422


def test_get_unknown_submission_404():
    resp = client.get("/api/submissions/does-not-exist")
    assert resp.status_code == 404
