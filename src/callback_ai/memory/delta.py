"""FR-15: report a delta vs the previous session on repeated competencies."""


def compute_delta(profile_before: dict, session_scores: dict[str, float]) -> dict[str, dict]:
    """profile_before is the profile as it was BEFORE this session's update
    (i.e. last_score reflects the prior session, if any)."""
    delta = {}
    for competency, score in session_scores.items():
        prior = profile_before.get(competency)
        previous_score = prior["last_score"] if prior else None
        delta[competency] = {
            "previous": previous_score,
            "current": score,
            "delta": (score - previous_score) if previous_score is not None else None,
        }
    return delta
