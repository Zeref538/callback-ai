import json

from fastapi.testclient import TestClient

import callback_ai.api.routes.session as session_routes
from callback_ai.api.app import app
from conftest import FakeChat

JOB_POST_RESPONSE = json.dumps({
    "target_position": "Backend Engineer",
    "competencies": [
        {"name": "System Design", "weight": 1.0, "seniority_bar": "mid", "description": "Designs systems"},
    ],
})
QUESTION_RESPONSE = "Tell me about a system you designed."
ANSWER_TEXT = "I designed a caching layer using Redis."
SCORE_RESPONSE = json.dumps({
    "coverage_score": 0.8,
    "evidence_quote": ANSWER_TEXT,
    "vagueness_signals": [],
    "live_feedback": {"verdict": "correct", "suggestion": "Nicely specific."},
})
REPORT_SCORE_RESPONSE = json.dumps({"score": 0.8, "evidence_quote": ANSWER_TEXT})


def test_full_session_via_api(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_chat = FakeChat([JOB_POST_RESPONSE, QUESTION_RESPONSE, SCORE_RESPONSE, REPORT_SCORE_RESPONSE])
    monkeypatch.setattr(session_routes, "Router", lambda: fake_chat)
    session_routes.SESSIONS.clear()

    client = TestClient(app)

    start_resp = client.post("/api/sessions", json={"job_post": "some job post", "budget": 1})
    assert start_resp.status_code == 200
    data = start_resp.json()
    session_id = data["session_id"]
    assert data["question"] == QUESTION_RESPONSE
    assert data["competency"] == "System Design"
    assert data["competencies"] == ["System Design"]

    answer_resp = client.post(f"/api/sessions/{session_id}/answer", json={"answer": ANSWER_TEXT})
    assert answer_resp.status_code == 200
    answer_data = answer_resp.json()
    assert answer_data["done"] is True
    assert answer_data["coverage_score"] == 0.8
    assert answer_data["next_competency"] is None
    assert answer_data["turn"] == 1

    report_resp = client.get(f"/api/sessions/{session_id}/report")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["report"]["competency_reports"][0]["score"] == 0.8


def test_report_before_done_returns_409(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    fake_chat = FakeChat([JOB_POST_RESPONSE, QUESTION_RESPONSE])
    monkeypatch.setattr(session_routes, "Router", lambda: fake_chat)
    session_routes.SESSIONS.clear()

    client = TestClient(app)
    start_resp = client.post("/api/sessions", json={"job_post": "some job post", "budget": 3})
    session_id = start_resp.json()["session_id"]

    report_resp = client.get(f"/api/sessions/{session_id}/report")
    assert report_resp.status_code == 409
