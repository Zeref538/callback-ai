import json

from callback_ai.ingest.schemas import Competency, Rubric
from callback_ai.interview.persona import get_persona
from callback_ai.interview.session_engine import InterviewSession
from callback_ai.memory.session_store import SessionLogger

RUBRIC = Rubric(
    job_post_hash="abc123",
    target_position="Engineer",
    competencies=[
        Competency(name="System Design", weight=0.5, seniority_bar="mid", description="Designs systems"),
        Competency(name="Communication", weight=0.5, seniority_bar="mid", description="Explains tradeoffs"),
    ],
)

ANSWER_TEXT = "a fixed answer about my project"


class ScriptedChat:
    """Content-aware fake: question/probe generation return plain text,
    scoring returns JSON whose score depends on which competency is being
    scored -- System Design always answered weakly, Communication strongly."""

    def chat(self, messages, *, temperature: float = 0.0, json_schema=None) -> str:
        system = messages[0]["content"]
        if system.startswith("You are scoring"):
            score = 0.2 if "System Design" in system else 0.9
            return json.dumps(
                {
                    "coverage_score": score,
                    "evidence_quote": ANSWER_TEXT,
                    "vagueness_signals": ["no numbers"] if score < 0.5 else [],
                    "live_feedback": {"verdict": "incomplete" if score < 0.5 else "correct", "suggestion": "..."},
                }
            )
        return "Generated question text?"


def test_weak_competency_gets_more_of_the_budget(tmp_path):
    chat = ScriptedChat()
    logger = SessionLogger(sessions_dir=tmp_path)
    session = InterviewSession(
        rubric=RUBRIC, claims=[], persona=get_persona("neutral"), chat=chat, logger=logger, budget=6
    )

    session.run(ask_fn=lambda q: ANSWER_TEXT, on_feedback=lambda _: None)

    weak = session.state["System Design"]
    strong = session.state["Communication"]
    assert weak.asked_count > strong.asked_count

    decisions = [e for e in logger.events if e["type"] == "decision"]
    assert len(decisions) == 6
    # At least one probe should have fired on the weak competency.
    assert any(d["action"] == "probe" and d["competency"] == "System Design" for d in decisions)


def test_session_logs_start_and_end_events(tmp_path):
    chat = ScriptedChat()
    logger = SessionLogger(sessions_dir=tmp_path)
    session = InterviewSession(
        rubric=RUBRIC, claims=[], persona=get_persona("neutral"), chat=chat, logger=logger, budget=2
    )

    session.run(ask_fn=lambda q: ANSWER_TEXT, on_feedback=lambda _: None)

    types = [e["type"] for e in logger.events]
    assert types[0] == "session_start"
    assert types[-1] == "session_end"
