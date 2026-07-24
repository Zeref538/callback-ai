from callback_ai.interview.budget_allocator import (
    MAX_ASKS_PER_COMPETENCY,
    allocate_next_competency,
    init_state,
    update_after_answer,
)
from callback_ai.ingest.schemas import Competency

COMPETENCIES = [
    Competency(name="System Design", weight=0.5, seniority_bar="mid", description="d"),
    Competency(name="Communication", weight=0.5, seniority_bar="mid", description="d"),
]


def test_equal_weight_equal_uncertainty_picks_first_deterministically():
    state = init_state(COMPETENCIES)
    # both start at ema_score=0.5 -> same priority; max() picks the first max, stable.
    assert allocate_next_competency(state) == "System Design"


def test_weaker_competency_gets_prioritized_after_a_bad_answer():
    state = init_state(COMPETENCIES)
    update_after_answer(state, "System Design", coverage_score=0.9)  # now confident, low priority
    assert allocate_next_competency(state) == "Communication"


def test_every_competency_is_asked_before_any_is_revisited():
    """Regression: a weak answer raises that competency's uncertainty, which on a
    pure weight*uncertainty ranking made it win every subsequent turn -- the
    budget collapsed onto the first few and the rest were never asked, so the
    report couldn't score them."""
    five = [
        Competency(name=f"C{i}", weight=0.2, seniority_bar="mid", description="d")
        for i in range(5)
    ]
    state = init_state(five)

    asked = []
    for _ in range(5):
        name = allocate_next_competency(state)
        asked.append(name)
        update_after_answer(state, name, coverage_score=0.1)  # always weak

    assert sorted(asked) == ["C0", "C1", "C2", "C3", "C4"]


def test_after_full_coverage_budget_goes_to_the_weakest():
    state = init_state(COMPETENCIES)
    update_after_answer(state, "System Design", coverage_score=0.1)   # weak
    update_after_answer(state, "Communication", coverage_score=0.95)  # strong

    assert allocate_next_competency(state) == "System Design"


def test_asked_count_cap_excludes_saturated_competency():
    state = init_state(COMPETENCIES)
    for _ in range(MAX_ASKS_PER_COMPETENCY):
        update_after_answer(state, "System Design", coverage_score=0.1)  # stays weak but capped out

    assert allocate_next_competency(state) == "Communication"
