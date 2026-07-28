"""End-to-end smoke test on the mock provider: the whole pipeline (rubric ->
claims -> question -> score -> probe -> report -> trace) with no key, which is
also the deploy path the keyless demo runs on."""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def mock_client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)                       # isolate cache/log/profile dirs
    monkeypatch.setenv("CALLBACK_AI_PROVIDER", "mock")
    # Re-import so build_chat() sees the mock provider via a fresh settings read.
    import importlib
    import callback_ai.config as config
    importlib.reload(config)
    import callback_ai.llm.router as router
    importlib.reload(router)
    import callback_ai.api.routes.session as session_routes
    importlib.reload(session_routes)
    import callback_ai.api.app as app_module
    importlib.reload(app_module)
    return TestClient(app_module.app), session_routes


JOB = """Backend Engineer — Payments
Design services that process millions of transactions a day. Idempotency and
data consistency under failure are essential. Debug production incidents and
write postmortems. Mentor junior teammates and communicate tradeoffs.
"""
RESUME = """Jane Doe — Backend Engineer
- Built an idempotent retry service for payment webhooks with Redis locks.
  Reduced duplicate-charge incidents by 30% over one quarter.
Skills: Python, Go, PostgreSQL, Redis.
"""


def test_full_mock_session_and_report(mock_client):
    client, _ = mock_client

    start = client.post("/api/sessions", json={
        "job_post": JOB, "resume": RESUME, "persona": "adversarial", "seniority": "senior", "budget": 6,
    })
    assert start.status_code == 200, start.text
    data = start.json()
    assert data["interviewer"]["name"] == "Kade"
    assert len(data["competencies"]) >= 3
    assert data["question"]
    sid = data["session_id"]

    # Answer with a specific answer, then a vague one, until the budget is spent.
    done = False
    answers = ["I cut p99 duplicate charges 30% using Redis SETNX idempotency keys.", "I improved it a lot."]
    turns = 0
    while not done and turns < 20:
        a = client.post(f"/api/sessions/{sid}/answer", json={"answer": answers[turns % 2]})
        assert a.status_code == 200, a.text
        done = a.json()["done"]
        turns += 1
    assert done

    report = client.get(f"/api/sessions/{sid}/report").json()
    reps = report["report"]["competency_reports"]
    assert len(reps) >= 3
    # scores discriminate: specific answers should outscore the vague ones somewhere
    scores = [r["score"] for r in reps]
    assert max(scores) > min(scores)
    # every score carries a verbatim quote (evidence gate)
    assert all(r["evidence_quote"] for r in reps)

    trace = client.get(f"/api/sessions/{sid}/trace").json()["trace"]
    assert len(trace) == turns
    assert all(t["action"] in {"probe", "move_on", "switch"} for t in trace)
