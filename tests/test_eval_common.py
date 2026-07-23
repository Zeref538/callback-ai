import json

import pytest

from eval.common import budget_adaptivity, evidence_gate_rejection_rate, load_all_sessions


def _write_session(path, events):
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def test_load_all_sessions_reads_every_jsonl(tmp_path):
    _write_session(tmp_path / "s1.jsonl", [{"type": "session_start"}])
    _write_session(tmp_path / "s2.jsonl", [{"type": "session_start"}])

    sessions = load_all_sessions(tmp_path)
    assert len(sessions) == 2


def test_evidence_gate_rejection_rate_averages_across_sessions(tmp_path):
    _write_session(tmp_path / "s1.jsonl", [{"type": "session_end", "evidence_gate_rejection_rate": 0.2}])
    _write_session(tmp_path / "s2.jsonl", [{"type": "session_end", "evidence_gate_rejection_rate": 0.4}])

    sessions = load_all_sessions(tmp_path)
    assert evidence_gate_rejection_rate(sessions) == pytest.approx(0.3)


def test_budget_adaptivity_reports_nonuniform_share(tmp_path):
    events = [
        {"type": "question", "competency": "System Design"},
        {"type": "question", "competency": "System Design"},
        {"type": "question", "competency": "Communication"},
    ]
    _write_session(tmp_path / "s1.jsonl", events)

    sessions = load_all_sessions(tmp_path)
    shares = budget_adaptivity(sessions)
    assert shares["System Design"] > shares["Communication"]


def test_empty_sessions_dir_returns_none(tmp_path):
    assert load_all_sessions(tmp_path / "does-not-exist") == []
    assert evidence_gate_rejection_rate([]) is None
    assert budget_adaptivity([]) is None
