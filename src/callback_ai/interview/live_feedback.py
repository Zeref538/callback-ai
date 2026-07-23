"""Wraps the coverage_scorer's live_feedback with persona phrasing. No LLM
call here -- the content already came out of coverage_scorer in the same
structured response; this just formats it for display."""
from callback_ai.interview.persona import Persona
from callback_ai.interview.schemas import LiveFeedback


def format_live_feedback(feedback: LiveFeedback, persona: Persona, low_confidence: bool) -> str:
    prefix = f"{persona.feedback_prefix} " if persona.feedback_prefix else ""
    line = f"{prefix}[{feedback.verdict}] {feedback.suggestion}"
    if low_confidence:
        line += " (low confidence -- couldn't verify this against your answer)"
    return line
