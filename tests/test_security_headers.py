from fastapi.testclient import TestClient

from callback_ai.api.app import app


def test_api_responses_carry_basic_security_headers():
    r = TestClient(app).get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
