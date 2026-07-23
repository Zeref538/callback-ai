import json

from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.interview.evidence_gate import EvidenceGate
from conftest import FakeChat

GOOD_RESPONSE = json.dumps({
    "coverage_score": 0.8,
    "evidence_quote": "reduced latency by 30%",
    "vagueness_signals": [],
    "live_feedback": {"verdict": "correct", "suggestion": "Good, you quantified the improvement."},
})

BAD_QUOTE_RESPONSE = json.dumps({
    "coverage_score": 0.8,
    "evidence_quote": "something not actually said",
    "vagueness_signals": [],
    "live_feedback": {"verdict": "correct", "suggestion": "Looks good."},
})


def test_score_answer_accepts_supported_quote():
    chat = FakeChat([GOOD_RESPONSE])
    gate = EvidenceGate(max_regenerate_attempts=1)

    result = score_answer(
        question="Tell me about a performance improvement.",
        answer="I reduced latency by 30% by adding a cache.",
        competency="System Design",
        description="Designs scalable systems",
        chat=chat,
        gate=gate,
    )

    assert result.accepted
    assert result.result.coverage_score == 0.8
    assert result.result.live_feedback.verdict == "correct"


def test_score_answer_flags_low_confidence_when_quote_never_matches():
    chat = FakeChat([BAD_QUOTE_RESPONSE, BAD_QUOTE_RESPONSE])
    gate = EvidenceGate(max_regenerate_attempts=1)

    result = score_answer(
        question="Tell me about a performance improvement.",
        answer="I reduced latency by 30% by adding a cache.",
        competency="System Design",
        description="Designs scalable systems",
        chat=chat,
        gate=gate,
    )

    assert not result.accepted
    assert result.low_confidence
