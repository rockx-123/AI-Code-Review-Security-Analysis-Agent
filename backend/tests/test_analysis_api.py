from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _create_submission(language: str, code: str) -> str:
    resp = client.post("/api/submissions/paste", json={"language": language, "code": code})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_analysis_runs_against_a_real_submission():
    fake_key = "sk_live_" + "NOTAREALKEYUSEDONLYFORUNITTESTS"  # split so it never appears whole in source
    submission_id = _create_submission(
        "python",
        f'api_key = "{fake_key}"\n',
    )
    resp = client.post(f"/api/analysis/{submission_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["submission_id"] == submission_id
    assert any(f["category"] == "security" for f in body["findings"])
    assert body["counts_by_severity"]["critical"] >= 1


def test_analysis_unknown_submission_404():
    resp = client.post("/api/analysis/does-not-exist")
    assert resp.status_code == 404


def test_analysis_clean_code_returns_no_findings():
    submission_id = _create_submission(
        "python",
        "def add(a, b):\n    return a + b\n",
    )
    resp = client.post(f"/api/analysis/{submission_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["findings"] == []
    assert body["counts_by_severity"]["critical"] == 0


def test_analysis_java_submission():
    submission_id = _create_submission(
        "java",
        (
            "public class Users {\n"
            "    public User getUser(String userId, Connection conn) throws Exception {\n"
            "        Statement stmt = conn.createStatement();\n"
            "        String query = \"SELECT * FROM users WHERE id = \" + userId;\n"
            "        ResultSet rs = stmt.executeQuery(query);\n"
            "        return null;\n"
            "    }\n"
            "}\n"
        ),
    )
    resp = client.post(f"/api/analysis/{submission_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert any(f["category"] == "security" for f in body["findings"])
