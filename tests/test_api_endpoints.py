"""Endpoint tests for the surfaces added after the original test_api.py:
input validation, /extract, /tts, session eviction, and the finished-session
and empty-answer guards."""
import io
import json

import docx
import pytest
from fastapi.testclient import TestClient

import callback_ai.api.routes.session as session_routes
from callback_ai.api.app import app
from conftest import FakeChat

client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    # Fresh cwd per test so the on-disk rubric cache can't leak between tests
    # (a cache hit would skip a chat() call and desync the FakeChat queue).
    monkeypatch.chdir(tmp_path)
    session_routes.SESSIONS.clear()

RUBRIC = json.dumps({
    "target_position": "Backend Engineer",
    "competencies": [{"name": "System Design", "weight": 1.0, "seniority_bar": "mid", "description": "Designs systems"}],
})
QUESTION = "Tell me about a system you designed."
GOOD_JOB = "Backend engineer on the payments team; distributed systems and on-call."


# ---------- /sessions validation ----------

def test_empty_job_post_rejected():
    assert client.post("/api/sessions", json={"job_post": "   "}).status_code == 422


def test_too_short_job_post_rejected():
    assert client.post("/api/sessions", json={"job_post": "hi"}).status_code == 422


def test_too_long_job_post_rejected():
    huge = "x" * (session_routes.MAX_JOB_POST_CHARS + 1)
    assert client.post("/api/sessions", json={"job_post": huge}).status_code == 422


def test_unknown_persona_rejected():
    r = client.post("/api/sessions", json={"job_post": GOOD_JOB, "persona": "hacker"})
    assert r.status_code == 422


def test_empty_rubric_rejected(monkeypatch):
    empty = json.dumps({"target_position": None, "competencies": []})
    monkeypatch.setattr(session_routes, "build_chat", lambda: FakeChat([empty]))
    r = client.post("/api/sessions", json={"job_post": GOOD_JOB})
    assert r.status_code == 422


def test_budget_is_clamped(monkeypatch):
    monkeypatch.setattr(session_routes, "build_chat", lambda: FakeChat([RUBRIC, QUESTION]))
    r = client.post("/api/sessions", json={"job_post": GOOD_JOB, "budget": 999})
    assert r.status_code == 200 and r.json()["budget"] == 30


# ---------- answer guards ----------

def test_answer_unknown_session_404():
    assert client.post("/api/sessions/nope/answer", json={"answer": "hi"}).status_code == 404


def test_empty_answer_rejected(monkeypatch):
    monkeypatch.setattr(session_routes, "build_chat", lambda: FakeChat([RUBRIC, QUESTION]))
    session_routes.SESSIONS.clear()
    sid = client.post("/api/sessions", json={"job_post": GOOD_JOB, "budget": 3}).json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/answer", json={"answer": "  "}).status_code == 422


def test_answer_after_finish_409(monkeypatch):
    score = json.dumps({"coverage_score": 0.8, "evidence_quote": "I built a cache.",
                        "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "ok"}})
    monkeypatch.setattr(session_routes, "build_chat", lambda: FakeChat([RUBRIC, QUESTION, score]))
    session_routes.SESSIONS.clear()
    sid = client.post("/api/sessions", json={"job_post": GOOD_JOB, "budget": 1}).json()["session_id"]
    assert client.post(f"/api/sessions/{sid}/answer", json={"answer": "I built a cache."}).json()["done"] is True
    # second answer on a finished session
    assert client.post(f"/api/sessions/{sid}/answer", json={"answer": "again"}).status_code == 409


# ---------- session eviction ----------

def test_trace_reports_turn_decisions(monkeypatch):
    score = json.dumps({"coverage_score": 0.8, "evidence_quote": "I built a cache.",
                        "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "ok"}})
    monkeypatch.setattr(session_routes, "build_chat", lambda: FakeChat([RUBRIC, QUESTION, score]))
    sid = client.post("/api/sessions", json={"job_post": GOOD_JOB, "budget": 1}).json()["session_id"]
    client.post(f"/api/sessions/{sid}/answer", json={"answer": "I built a cache."})
    trace = client.get(f"/api/sessions/{sid}/trace").json()["trace"]
    assert trace and trace[0]["turn"] == 1
    assert trace[0]["competency"] == "System Design"
    assert trace[0]["score"] == 0.8
    assert trace[0]["action"] in {"probe", "move_on", "switch"}


def test_trace_unknown_session_404():
    assert client.get("/api/sessions/nope/trace").status_code == 404


def test_sessions_are_evicted_past_cap(monkeypatch):
    monkeypatch.setattr(session_routes, "MAX_SESSIONS", 3)
    session_routes.SESSIONS.clear()
    for i in range(5):
        session_routes._remember_session(f"s{i}", object())
    assert len(session_routes.SESSIONS) == 3
    assert "s0" not in session_routes.SESSIONS and "s4" in session_routes.SESSIONS


# ---------- /extract ----------

def test_extract_txt():
    r = client.post("/api/extract", files={"file": ("r.txt", b"Plain resume text here.", "text/plain")})
    assert r.status_code == 200
    assert r.json()["text"] == "Plain resume text here."


def test_extract_docx():
    d = docx.Document()
    d.add_paragraph("Built an idempotent retry layer with Redis.")
    buf = io.BytesIO(); d.save(buf)
    r = client.post("/api/extract", files={"file": ("r.docx", buf.getvalue(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document")})
    assert r.status_code == 200 and "idempotent retry" in r.json()["text"]


def test_extract_unsupported_type():
    r = client.post("/api/extract", files={"file": ("a.zip", b"PK\x03\x04", "application/zip")})
    assert r.status_code == 422


def test_extract_oversize():
    big = b"x" * (session_routes.MAX_UPLOAD_BYTES + 1)
    r = client.post("/api/extract", files={"file": ("big.txt", big, "text/plain")})
    assert r.status_code == 413


# ---------- /tts ----------

def test_tts_empty_text_rejected():
    assert client.post("/api/tts", json={"text": "  "}).status_code == 422


def test_tts_streams_audio(monkeypatch):
    # Stub edge_tts so the test is hermetic (no Microsoft network call).
    import types

    class FakeCommunicate:
        def __init__(self, text, voice, **kw):
            self.captured = (text, voice, kw)
        async def stream(self):
            yield {"type": "audio", "data": b"ID3fakeaudio"}

    fake = types.ModuleType("edge_tts")
    fake.Communicate = FakeCommunicate
    monkeypatch.setitem(__import__("sys").modules, "edge_tts", fake)

    r = client.post("/api/tts", json={"text": "How did you measure that?", "voice": "en-US-AndrewNeural", "rate": 1.06})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("audio/mpeg")
    assert r.content == b"ID3fakeaudio"


def test_tts_bad_voice_is_sanitized(monkeypatch):
    import types
    captured = {}

    class FakeCommunicate:
        def __init__(self, text, voice, **kw):
            captured["voice"] = voice
        async def stream(self):
            yield {"type": "audio", "data": b"x"}

    fake = types.ModuleType("edge_tts")
    fake.Communicate = FakeCommunicate
    monkeypatch.setitem(__import__("sys").modules, "edge_tts", fake)

    client.post("/api/tts", json={"text": "hi there friend", "voice": "evil; rm -rf /"})
    assert captured["voice"] == "en-US-AndrewNeural"  # fell back to the safe default


# ---------- health ----------

def test_health_ok():
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and "provider" in body
