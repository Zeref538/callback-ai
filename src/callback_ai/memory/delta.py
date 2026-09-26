"""FR-15: report a delta vs the previous session on repeated competencies."""


def compute_delta(previous_scores: dict[str, float], session_scores: dict[str, float]) -> dict[str, dict]:
    """previous_scores: competency -> the caller's score for it last time."""
    delta = {}
    for competency, score in session_scores.items():
        previous_score = previous_scores.get(competency)
        delta[competency] = {
            "previous": previous_score,
            "current": score,
            "delta": (score - previous_score) if previous_score is not None else None,
        }
    return delta
