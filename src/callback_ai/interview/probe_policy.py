"""FR-6 pt2/FR-7: probe deeper, move on, or switch competency. Deterministic
rule read from the coverage_scorer's output -- not a second LLM call (see
plan section 2)."""
from callback_ai.interview.budget_allocator import CompetencyState
from callback_ai.interview.persona import Persona

MAX_PROBES_PER_COMPETENCY = 1  # ponytail: fixed, tune against probe-precision metric in week 2


def decide(coverage_score: float, competency_state: CompetencyState, persona: Persona) -> str:
    """Returns "probe", "move_on", or "switch"."""
    if coverage_score < persona.probe_threshold and competency_state.probe_count < MAX_PROBES_PER_COMPETENCY:
        return "probe"
    if coverage_score < persona.probe_threshold:
        # Already probed this competency to the cap and it's still weak -- give up on it for now.
        return "switch"
    return "move_on"
