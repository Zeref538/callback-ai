"""FR-9/12: per-competency scores with a verbatim quote, overall summary, and
top-3 fixes. FR-10: each competency score is gated the same way as the live
per-answer scores (same EvidenceGate instance, so the session's rejection
rate is one number, not two)."""
from callback_ai.llm.json_parse import parse_json_response

from callback_ai.grading.model_answer import generate_model_answer
from callback_ai.grading.schemas import CompetencyReport, Report
from callback_ai.ingest.schemas import Claim, Rubric
from callback_ai.interview.evidence_gate import EvidenceGate
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """You are scoring a candidate's overall performance on the
competency "{competency}" ({description}), based on everything they said
about it in this interview. Return ONLY JSON:
{{"score": 0.0-1.0, "evidence_quote": "<verbatim substring from their answers below>"}}

Their answers on this competency:
{transcript}"""

WEAK_THRESHOLD = 0.5  # ponytail: fixed cutoff for "generate a model answer", tune against real sessions


def build_competency_transcripts(events: list[dict]) -> dict[str, str]:
    """Groups answer text by competency from a session's logged events."""
    transcripts: dict[str, list[str]] = {}
    for event in events:
        if event["type"] == "answer":
            transcripts.setdefault(event["competency"], []).append(event["text"])
    return {competency: " ".join(answers) for competency, answers in transcripts.items()}


def _generate_competency_score(chat: ChatProvider, competency: str, description: str, transcript: str) -> dict:
    raw = chat.chat(
        [{"role": "system", "content": SYSTEM_PROMPT.format(competency=competency, description=description, transcript=transcript)}],
        temperature=0.0,
    )
    return parse_json_response(raw)


def generate_report(
    rubric: Rubric,
    events: list[dict],
    claims: list[Claim],
    chat: ChatProvider,
    gate: EvidenceGate,
) -> Report:
    transcripts = build_competency_transcripts(events)
    competency_reports: list[CompetencyReport] = []

    for competency in rubric.competencies:
        transcript = transcripts.get(competency.name, "")
        if not transcript:
            continue

        gate_result = gate.check_and_regenerate(
            transcript=transcript,
            generate=lambda: _generate_competency_score(chat, competency.name, competency.description, transcript),
            extract_quote=lambda data: data["evidence_quote"],
        )
        data = gate_result.result
        competency_reports.append(
            CompetencyReport(
                competency=competency.name,
                score=data["score"],
                evidence_quote=data["evidence_quote"],
                low_confidence=gate_result.low_confidence,
            )
        )

    ranked = sorted(competency_reports, key=lambda r: r.score)
    top_fixes = [r.competency for r in ranked[:3]]

    model_answers = {}
    for r in ranked:
        if r.score < WEAK_THRESHOLD:
            model_answers[r.competency] = generate_model_answer(r.competency, transcripts[r.competency], claims, chat)

    avg = sum(r.score for r in competency_reports) / len(competency_reports) if competency_reports else 0.0
    overall_summary = (
        f"Overall readiness score: {avg:.2f}/1.0 across {len(competency_reports)} competencies. "
        f"Weakest areas: {', '.join(top_fixes) if top_fixes else 'none'}."
    )

    return Report(
        competency_reports=competency_reports,
        overall_summary=overall_summary,
        top_fixes=top_fixes,
        model_answers=model_answers,
    )
