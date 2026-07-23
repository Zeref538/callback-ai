"""The agent loop: each turn re-reads session state and dispatches to the
next tool (allocate a competency, ask, score, probe, or move on) rather than
running a fixed sequence. Guardrails (evidence gate, fixed budget ceiling,
persona-invariant scoring) are enforced here in code, not left to the model.
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

    def run(self, ask_fn: Callable[[str], str], on_feedback: Callable[[str], None] = print) -> None:
        """ask_fn(question) -> answer; typically prints the question and reads input."""
        self.logger.log(
            "session_start",
            persona=self.persona.name,
            budget=self.budget,
            competencies=list(self.competencies_by_name),
        )

        pending_probe: PendingProbe | None = None

        for turn in range(1, self.budget + 1):
            if pending_probe is not None:
                competency = pending_probe.competency
                question = generate_probe(
                    competency, pending_probe.last_answer, pending_probe.vagueness_signals, self.persona, self.chat
                )
            else:
                competency = allocate_next_competency(self.state)
                comp = self.competencies_by_name[competency]
                question = generate_question(competency, comp.description, self.claims, self.persona, self.chat)

            self.logger.log("question", turn=turn, competency=competency, text=question)
            answer = ask_fn(question)
            self.logger.log("answer", turn=turn, text=answer)

            comp = self.competencies_by_name[competency]
            gate_result = score_answer(question, answer, competency, comp.description, self.chat, self.gate)
            scored = gate_result.result
            scored.low_confidence = gate_result.low_confidence

            self.logger.log(
                "scoring",
                turn=turn,
                competency=competency,
                coverage_score=scored.coverage_score,
                evidence_quote=scored.evidence_quote,
                gate_accepted=gate_result.accepted,
                low_confidence=gate_result.low_confidence,
                live_feedback=scored.live_feedback.model_dump(),
            )
            on_feedback(format_live_feedback(scored.live_feedback, self.persona, gate_result.low_confidence))

            state = self.state[competency]
            action = decide_next_action(scored.coverage_score, state, self.persona)
            update_after_answer(self.state, competency, scored.coverage_score)

            self.logger.log(
                "decision",
                turn=turn,
                competency=competency,
                action=action,
                remaining_budget=self.budget - turn,
                reason=f"coverage_score={scored.coverage_score:.2f} threshold={self.persona.probe_threshold}",
            )

            if action == "probe":
                state.probe_count += 1
                pending_probe = PendingProbe(
                    competency=competency, last_answer=answer, vagueness_signals=scored.vagueness_signals
                )
            else:
                pending_probe = None

        self.logger.log("session_end", turns=self.budget, evidence_gate_rejection_rate=self.gate.rejection_rate)
