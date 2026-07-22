from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import RandomJoke
from app.services.joke_service import JokeFetchError

client = TestClient(app)


def test_random_joke_success(monkeypatch):
    def fake_fetch() -> RandomJoke:
        return RandomJoke(setup="Setup line", punchline="Punchline line", source="example.com")

    monkeypatch.setattr("app.api.routes.jokes.fetch_random_joke", fake_fetch)
    resp = client.get("/api/jokes/random")
    assert resp.status_code == 200
    assert resp.json() == {
        "setup": "Setup line",
        "punchline": "Punchline line",
        "source": "example.com",
    }


def test_random_joke_upstream_error(monkeypatch):
    def fake_fetch() -> RandomJoke:
        raise JokeFetchError("Couldn't fetch a joke right now. Please try again.")

    monkeypatch.setattr("app.api.routes.jokes.fetch_random_joke", fake_fetch)
    resp = client.get("/api/jokes/random")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "Couldn't fetch a joke right now. Please try again."
