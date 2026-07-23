from pydantic import BaseModel


class LiveFeedback(BaseModel):
    verdict: str  # "correct" | "partial" | "incomplete"
    suggestion: str


class ScoredAnswer(BaseModel):
    coverage_score: float  # 0.0-1.0
    evidence_quote: str  # verbatim substring of the candidate's answer
    vagueness_signals: list[str] = []
    live_feedback: LiveFeedback
    low_confidence: bool = False  # set by the evidence gate on repeated rejection
