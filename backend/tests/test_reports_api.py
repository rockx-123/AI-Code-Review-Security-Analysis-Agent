from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_submission(language: str, code: str) -> str:
    resp = client.post("/api/submissions/paste", json={"language": language, "code": code})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_pdf_report_downloads_for_a_real_submission():
    fake_key = "sk_live_" + "NOTAREALKEYUSEDONLYFORUNITTESTS"
    submission_id = _create_submission("python", f'api_key = "{fake_key}"\n')

    resp = client.get(f"/api/reports/{submission_id}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert submission_id[:8] in resp.headers["content-disposition"]
    # A real PDF file starts with this exact magic-byte signature.
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 500


def test_pdf_report_unknown_submission_404():
    resp = client.get("/api/reports/does-not-exist/pdf")
    assert resp.status_code == 404


def test_pdf_report_clean_code_still_generates_a_valid_pdf():
    submission_id = _create_submission("python", "def add(a, b):\n    return a + b\n")
    resp = client.get(f"/api/reports/{submission_id}/pdf")
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"
