import json

import pytest

from eval.discrimination import measure_discrimination, spearman_rho
from eval.grading_consistency import measure_consistency
from eval.probe_precision import measure_probe_precision
from conftest import FakeChat


def test_spearman_rho_perfect_agreement():
    assert spearman_rho([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)


def test_spearman_rho_perfect_disagreement():
    assert spearman_rho([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


def test_measure_consistency_zero_variance_on_identical_scores():
    response = json.dumps(
        {"coverage_score": 0.7, "evidence_quote": "did the thing", "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "ok"}}
    )
    chat = FakeChat([response] * 5)

    result = measure_consistency("Q?", "I did the thing", "C", "d", chat, n=5)

    assert result["stdev_10pt"] == 0.0
    assert result["meets_target"]


def test_measure_discrimination_rho_high_when_agent_tracks_human(tmp_path):
    corpus = [
        {"question": "Q1", "answer": "weak answer", "human_score": 2},
        {"question": "Q1", "answer": "strong answer", "human_score": 9},
    ]
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus), encoding="utf-8")

    responses = [
        json.dumps({"coverage_score": 0.2, "evidence_quote": "weak answer", "vagueness_signals": [], "live_feedback": {"verdict": "incomplete", "suggestion": "x"}}),
        json.dumps({"coverage_score": 0.9, "evidence_quote": "strong answer", "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "x"}}),
    ]
    chat = FakeChat(responses)

    result = measure_discrimination(chat, corpus_path=corpus_path)

    assert result["rho"] == pytest.approx(1.0)
    assert result["meets_target"]


def test_measure_probe_precision_fires_only_on_vague(tmp_path):
    fixture = [
        {"question": "Q1", "answer": "vague one", "label": "vague"},
        {"question": "Q1", "answer": "specific one", "label": "specific"},
    ]
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    responses = [
        json.dumps({"coverage_score": 0.1, "evidence_quote": "vague one", "vagueness_signals": ["no numbers"], "live_feedback": {"verdict": "incomplete", "suggestion": "x"}}),
        json.dumps({"coverage_score": 0.95, "evidence_quote": "specific one", "vagueness_signals": [], "live_feedback": {"verdict": "correct", "suggestion": "x"}}),
    ]
    chat = FakeChat(responses)

    result = measure_probe_precision(chat, fixture_path=fixture_path)

    assert result["vague_probe_rate"] == 1.0
    assert result["specific_probe_rate"] == 0.0
    assert result["meets_target"]
