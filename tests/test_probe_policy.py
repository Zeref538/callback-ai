from callback_ai.interview.budget_allocator import CompetencyState
from callback_ai.interview.persona import get_persona
from callback_ai.interview.probe_policy import decide


def test_low_score_below_threshold_probes():
    persona = get_persona("neutral")  # threshold 0.45
    state = CompetencyState(weight=0.5)
    assert decide(0.2, state, persona) == "probe"


def test_high_score_moves_on():
    persona = get_persona("neutral")
    state = CompetencyState(weight=0.5)
    assert decide(0.9, state, persona) == "move_on"


def test_already_probed_to_cap_switches_instead_of_probing_again():
    persona = get_persona("neutral")
    state = CompetencyState(weight=0.5, probe_count=1)  # MAX_PROBES_PER_COMPETENCY == 1
    assert decide(0.1, state, persona) == "switch"


def test_adversarial_probes_at_higher_scores_than_friendly():
    adversarial = get_persona("adversarial")
    friendly = get_persona("friendly")
    state = CompetencyState(weight=0.5)

    # A middling 0.4 score: adversarial (threshold 0.6) probes, friendly (threshold 0.3) moves on.
    assert decide(0.4, state, adversarial) == "probe"
    assert decide(0.4, state, friendly) == "move_on"
