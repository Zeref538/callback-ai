"""FR-10: a score whose quote doesn't appear verbatim in the transcript is
rejected and regenerated once. Shared by the live per-answer path and the
final report path so there is a single rejection counter (deterministic
guardrail -- not left to the model's discretion)."""
import re
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def quote_is_supported(quote: str, transcript: str) -> bool:
    if not quote:
        return False
    return _normalize(quote) in _normalize(transcript)


@dataclass
class GateResult:
    result: T
    accepted: bool
    regenerated: bool
    low_confidence: bool


class EvidenceGate:
    """Tracks the single rejection counter the PRD's evidence-gate metric reports."""

    def __init__(self, max_regenerate_attempts: int = 1):
        self.max_regenerate_attempts = max_regenerate_attempts
        self.rejections = 0
        self.checked = 0

    def check_and_regenerate(
        self,
        transcript: str,
        generate: Callable[[], T],
        extract_quote: Callable[[T], str],
    ) -> GateResult:
        """generate() produces a result with a quote; extract_quote pulls the quote
        out of it. Retries generate() up to max_regenerate_attempts times if the
        quote fails the substring check, then flags low_confidence rather than
        looping further (protects the 5s latency budget, NFR-2)."""
        self.checked += 1
        attempts = 0
        result = generate()

        while not quote_is_supported(extract_quote(result), transcript):
            self.rejections += 1
            attempts += 1
            if attempts > self.max_regenerate_attempts:
                return GateResult(result=result, accepted=False, regenerated=attempts > 1, low_confidence=True)
            result = generate()

        return GateResult(result=result, accepted=True, regenerated=attempts > 0, low_confidence=False)

    @property
    def rejection_rate(self) -> float:
        return self.rejections / self.checked if self.checked else 0.0
