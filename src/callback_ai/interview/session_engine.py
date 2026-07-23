"""The agent loop: each turn re-reads session state and dispatches to the
next tool (allocate a competency, ask, score, probe, or move on) rather than
running a fixed sequence. Guardrails (evidence gate, fixed budget ceiling,
persona-invariant scoring) are enforced here in code, not left to the model.

Exposed step-wise (next_question / submit_answer) rather than as one blocking
loop, so the same engine drives both the CLI (a while-loop) and the FastAPI
backend (one HTTP request per turn) without duplicating the turn logic.
"""
from dataclasses import dataclass
from typing import Callable

from callback_ai.config import settings
from callback_ai.ingest.schemas import Claim, Rubric
from callback_ai.interview.budget_allocator import allocate_next_competency, init_state, update_after_answer
from callback_ai.interview.evidence_gate import EvidenceGate
from callback_ai.interview.live_feedback import format_live_feedback
from callback_ai.interview.persona import Persona
from callback_ai.interview.probe_policy import decide as decide_next_action
from callback_ai.interview.question_bank import generate_probe, generate_question
from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.llm.client import ChatProvider
from callback_ai.memory.session_store import SessionLogger


@dataclass
class PendingProbe:
    competency: str
    last_answer: str
    vagueness_signals: list[str]


class InterviewSession:
    def __init__(
        self,
        rubric: Rubric,
        claims: list[Claim],
        persona: Persona,
        chat: ChatProvider,
        logger: SessionLogger,
        budget: int = settings.question_budget,
    ):
        self.rubric = rubric
        self.competencies_by_name = {c.name: c for c in rubric.competencies}
        self.state = init_state(rubric.competencies)
        self.claims = claims
        self.persona = persona
        self.chat = chat
        self.logger = logger
        self.budget = budget
        self.gate = EvidenceGate(max_regenerate_attempts=settings.max_regenerate_attempts)

        self.turn = 0
        self.done = False
        self._started = False
        self._pending_probe: PendingProbe | None = None
        self._current_competency: str | None = None
        self._current_question: str | None = None

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self.logger.log(
            "session_start",
            persona=self.persona.name,
            budget=self.budget,
            competencies=list(self.competencies_by_name),
        )

    def next_question(self) -> str | None:
        """Returns the next question, or None once the budget is exhausted."""
        if not self._started:
            self.start()
        if self.turn >= self.budget:
            if not self.done:
                self.done = True
                self.logger.log(
                    "session_end", turns=self.budget, evidence_gate_rejection_rate=self.gate.rejection_rate
                )
            return None

        self.turn += 1
        if self._pending_probe is not None:
            competency = self._pending_probe.competency
            question = generate_probe(
                competency, self._pending_probe.last_answer, self._pending_probe.vagueness_signals, self.persona, self.chat
            )
        else:
            competency = allocate_next_competency(self.state)
            comp = self.competencies_by_name[competency]
            question = generate_question(competency, comp.description, self.claims, self.persona, self.chat)

        self._current_competency = competency
        self._current_question = question
        self.logger.log("question", turn=self.turn, competency=competency, text=question)
        return question

    def submit_answer(self, answer: str) -> dict:
        """Scores the answer for the question returned by the last next_question()
        call, logs the decision, and returns a dict with the live feedback line."""
        competency = self._current_competency
        question = self._current_question
        self.logger.log("answer", turn=self.turn, competency=competency, text=answer)

        comp = self.competencies_by_name[competency]
        gate_result = score_answer(question, answer, competency, comp.description, self.chat, self.gate)
        scored = gate_result.result
        scored.low_confidence = gate_result.low_confidence

        self.logger.log(
            "scoring",
            turn=self.turn,
            competency=competency,
            coverage_score=scored.coverage_score,
            evidence_quote=scored.evidence_quote,
            gate_accepted=gate_result.accepted,
            low_confidence=gate_result.low_confidence,
            live_feedback=scored.live_feedback.model_dump(),
        )
        feedback_line = format_live_feedback(scored.live_feedback, self.persona, gate_result.low_confidence)

        state = self.state[competency]
        action = decide_next_action(scored.coverage_score, state, self.persona)
        update_after_answer(self.state, competency, scored.coverage_score)

        self.logger.log(
            "decision",
            turn=self.turn,
            competency=competency,
            action=action,
            remaining_budget=self.budget - self.turn,
            reason=f"coverage_score={scored.coverage_score:.2f} threshold={self.persona.probe_threshold}",
        )

        if action == "probe":
            state.probe_count += 1
            self._pending_probe = PendingProbe(
                competency=competency, last_answer=answer, vagueness_signals=scored.vagueness_signals
            )
        else:
            self._pending_probe = None

        return {
            "feedback_line": feedback_line,
            "coverage_score": scored.coverage_score,
            "low_confidence": gate_result.low_confidence,
            "done": self.turn >= self.budget,
        }

    def run(self, ask_fn: Callable[[str], str], on_feedback: Callable[[str], None] = print) -> None:
        """Convenience blocking loop for the CLI; API callers should drive
        next_question()/submit_answer() directly, one HTTP request per turn."""
        while True:
            question = self.next_question()
            if question is None:
                break
            answer = ask_fn(question)
            result = self.submit_answer(answer)
            on_feedback(result["feedback_line"])
