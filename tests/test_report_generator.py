import json

from callback_ai.grading.report_generator import build_competency_transcripts, generate_report
from callback_ai.ingest.schemas import Competency, Rubric
from callback_ai.interview.evidence_gate import EvidenceGate
from conftest import FakeChat

RUBRIC = Rubric(
    job_post_hash="abc",
    competencies=[
        Competency(name="System Design", weight=0.5, seniority_bar="mid", description="Designs systems"),
        Competency(name="Communication", weight=0.5, seniority_bar="mid", description="Explains tradeoffs"),
    ],
)

EVENTS = [
    {"type": "answer", "competency": "System Design", "text": "I made things faster with a cache."},
    {"type": "answer", "competency": "Communication", "text": "I explained the tradeoff to my manager clearly."},
]


def test_build_competency_transcripts_groups_by_competency():
    transcripts = build_competency_transcripts(EVENTS)
    assert transcripts["System Design"] == "I made things faster with a cache."
    assert transcripts["Communication"] == "I explained the tradeoff to my manager clearly."


def test_generate_report_produces_scores_and_model_answer_for_weak_competency():
    weak_score = json.dumps({"score": 0.2, "evidence_quote": "I made things faster with a cache."})
    strong_score = json.dumps({"score": 0.9, "evidence_quote": "I explained the tradeoff to my manager clearly."})
    model_answer_text = "A stronger answer citing your real cache work."

    chat = FakeChat([weak_score, strong_score, model_answer_text])
    gate = EvidenceGate(max_regenerate_attempts=1)

    report = generate_report(RUBRIC, EVENTS, claims=[], chat=chat, gate=gate)

    scores = {r.competency: r.score for r in report.competency_reports}
    assert scores["System Design"] == 0.2
    assert scores["Communication"] == 0.9
    assert "System Design" in report.model_answers
    assert "Communication" not in report.model_answers
    assert report.top_fixes[0] == "System Design"
