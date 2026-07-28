"""Rate limiting middleware + the cross-session delta the report returns."""
import json

import pytest
from fastapi.testclient import TestClient

import callback_ai.api.app as app_module
import callback_ai.api.routes.session as session_routes
from callback_ai.api.app import app
from conftest import FakeChat

GOOD_JOB = "Backend engineer on the payments team; distributed systems and on-call."
RUBRIC = json.dumps({
    "target_position": "Backend Engineer",
    "competencies": [{"name": "System Design", "weight": 1.0, "seniority_bar": "mid", "description": "Designs systems"}],
})
QUESTION = "Tell me about a system you designed."
SCORE = json.dumps({"coverage_score": 0.8, "evidence_quote": "I built a cache.",
                    "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "ok"}})
REPORT_SCORE = json.dumps({"score": 0.8, "evidence_quote": "I built a cache."})


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    session_routes.SESSIONS.clear()
    app_module._hits.clear()


def test_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(app_module, "RATE_LIMIT_PER_MIN", 3)
    client = TestClient(app)
    codes = [client.post("/api/tts", json={"text": " "}).status_code for _ in range(5)]
    # first 3 allowed (each 422 for empty text), then throttled
    assert codes[:3] == [422, 422, 422]
    assert 429 in codes[3:]


def test_health_not_rate_limited(monkeypatch):
    monkeypatch.setattr(app_module, "RATE_LIMIT_PER_MIN", 1)
    client = TestClient(app)
    assert all(client.get("/api/health").status_code == 200 for _ in range(5))


def _run_session(client, monkeypatch, score_val, job):
    score = json.dumps({"coverage_score": score_val, "evidence_quote": "I built a cache.",
                        "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "ok"}})
    report_score = json.dumps({"score": score_val, "evidence_quote": "I built a cache."})
    model_answer = "I built a Redis cache keyed on request id and cut duplicate work 30%."
    # extra model_answer response covers the weak-competency path in the report
    monkeypatch.setattr(session_routes, "build_chat",
                        lambda: FakeChat([RUBRIC, QUESTION, score, report_score, model_answer]))
    sid = client.post("/api/sessions", json={"job_post": job, "budget": 1}).json()["session_id"]
    client.post(f"/api/sessions/{sid}/answer", json={"answer": "I built a cache."})
    return client.get(f"/api/sessions/{sid}/report").json()


def test_delta_none_first_time_then_measured(monkeypatch):
    client = TestClient(app)
    # distinct job text avoids the rubric cache; the rubric stub yields the same
    # competency name either way, so the delta still compares like for like.
    first = _run_session(client, monkeypatch, 0.4, GOOD_JOB + " Kafka.")
    assert first["delta"]["System Design"]["previous"] is None
    assert first["delta"]["System Design"]["delta"] is None

    second = _run_session(client, monkeypatch, 0.8, GOOD_JOB + " gRPC.")
    d = second["delta"]["System Design"]
    assert d["previous"] == 0.4
    assert d["current"] == 0.8
    assert abs(d["delta"] - 0.4) < 1e-9
