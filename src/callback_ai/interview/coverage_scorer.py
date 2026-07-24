"""FR-6 pt1: score an answer's coverage of a rubric competency, in one LLM
call that also produces the verbatim quote and the live per-answer feedback.
Kept as a single call (not two) to protect NFR-2 latency and NIM's free-tier
rate limit -- see plan section 2 for the two-call fallback if this doesn't
hold up under real model behavior."""
from callback_ai.llm.json_parse import parse_json_response

from callback_ai.interview.evidence_gate import EvidenceGate, GateResult
from callback_ai.interview.schemas import LiveFeedback, ScoredAnswer
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """You are scoring a candidate's interview answer against one
competency. Return ONLY JSON:
{{"coverage_score": 0.0-1.0, "evidence_quote": "<verbatim substring of the candidate's answer>",
  "vagueness_signals": ["..."],
  "live_feedback": {{"verdict": "correct|partial|incomplete", "suggestion": "<1-2 sentences>"}}}}
The evidence_quote MUST be copied exactly from the candidate's answer, no paraphrasing.
Competency: {competency}
Competency description: {description}"""


def _generate(chat: ChatProvider, competency: str, description: str, question: str, answer: str) -> ScoredAnswer:
    raw = chat.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT.format(competency=competency, description=description)},
            {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"},
        ],
        temperature=0.0,
    )
    data = parse_json_response(raw)
    return ScoredAnswer(
        coverage_score=data["coverage_score"],
        evidence_quote=data["evidence_quote"],
        vagueness_signals=data.get("vagueness_signals", []),
        live_feedback=LiveFeedback(**data["live_feedback"]),
    )


def score_answer(
    question: str,
    answer: str,
    competency: str,
    description: str,
    chat: ChatProvider,
    gate: EvidenceGate,
) -> GateResult:
    """answer is also the transcript the quote is checked against (per-turn scope)."""
    return gate.check_and_regenerate(
        transcript=answer,
        generate=lambda: _generate(chat, competency, description, question, answer),
        extract_quote=lambda scored: scored.evidence_quote,
    )
