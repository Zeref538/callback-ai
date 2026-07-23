"""FR-5: allocate the question budget across competencies by weight and by
remaining uncertainty, re-evaluated after every answer. Deterministic --
no LLM call needed to pick a competency name."""
from dataclasses import dataclass, field

from callback_ai.ingest.schemas import Competency

MAX_ASKS_PER_COMPETENCY = 4  # ponytail: fixed cap, revisit if a rubric ever has <3 competencies


@dataclass
class CompetencyState:
    weight: float
    ema_score: float = 0.5  # prior: unknown, so mid-uncertainty
    asked_count: int = 0
    probe_count: int = 0

    @property
    def uncertainty(self) -> float:
        return 1.0 - self.ema_score

    @property
    def priority(self) -> float:
        return self.weight * self.uncertainty


def init_state(competencies: list[Competency]) -> dict[str, CompetencyState]:
    return {c.name: CompetencyState(weight=c.weight) for c in competencies}


def allocate_next_competency(state: dict[str, CompetencyState]) -> str:
    """Highest weight*uncertainty wins; competencies at the per-competency ask
    cap are excluded so budget doesn't collapse onto a single weak area."""
    eligible = {name: s for name, s in state.items() if s.asked_count < MAX_ASKS_PER_COMPETENCY}
    if not eligible:
        eligible = state  # cap hit everywhere (small rubric) -- allow overflow rather than crash
    return max(eligible, key=lambda name: eligible[name].priority)


def update_after_answer(state: dict[str, CompetencyState], competency: str, coverage_score: float) -> None:
    s = state[competency]
    s.asked_count += 1
    # Exponential moving average, alpha=0.6 weights the latest answer heavily
    # since a 12-question session gives little data per competency.
    s.ema_score = 0.6 * coverage_score + 0.4 * s.ema_score
