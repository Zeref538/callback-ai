from callback_ai.interview.evidence_gate import EvidenceGate, quote_is_supported


def test_quote_is_supported_exact():
    assert quote_is_supported("reduced latency by 30%", "We reduced latency by 30% last quarter.")


def test_quote_is_supported_normalizes_whitespace():
    assert quote_is_supported("reduced   latency", "we reduced\nlatency here")


def test_quote_not_supported():
    assert not quote_is_supported("increased revenue", "We reduced latency by 30%.")


def test_gate_accepts_on_first_try():
    gate = EvidenceGate(max_regenerate_attempts=1)
    result = gate.check_and_regenerate(
        transcript="I reduced latency by 30%.",
        generate=lambda: {"quote": "reduced latency by 30%"},
        extract_quote=lambda r: r["quote"],
    )
    assert result.accepted
    assert not result.regenerated
    assert gate.rejection_rate == 0.0


def test_gate_regenerates_once_then_accepts():
    attempts = iter([{"quote": "made up thing"}, {"quote": "reduced latency by 30%"}])
    gate = EvidenceGate(max_regenerate_attempts=1)
    result = gate.check_and_regenerate(
        transcript="I reduced latency by 30%.",
        generate=lambda: next(attempts),
        extract_quote=lambda r: r["quote"],
    )
    assert result.accepted
    assert result.regenerated
    assert gate.rejections == 1


def test_gate_flags_low_confidence_after_exhausting_attempts():
    gate = EvidenceGate(max_regenerate_attempts=1)
    result = gate.check_and_regenerate(
        transcript="I reduced latency by 30%.",
        generate=lambda: {"quote": "made up thing"},
        extract_quote=lambda r: r["quote"],
    )
    assert not result.accepted
    assert result.low_confidence
    assert gate.rejections == 2  # initial + the one retry, both rejected
