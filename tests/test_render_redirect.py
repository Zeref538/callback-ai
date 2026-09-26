from fastapi.testclient import TestClient

from callback_ai.api.app import app


def test_on_render_page_visits_go_to_netlify_but_api_still_answers(monkeypatch):
    monkeypatch.setenv("RENDER", "true")   # Render sets this on every service
    client = TestClient(app, follow_redirects=False)

    page = client.get("/")
    assert page.status_code == 302
    assert page.headers["location"] == "https://callback-ai.netlify.app"
    assert client.get("/api/health").status_code == 200


def test_locally_the_page_is_still_served(monkeypatch):
    monkeypatch.delenv("RENDER", raising=False)
    page = TestClient(app).get("/")
    assert page.status_code == 200
    assert "callback-ai" in page.text
