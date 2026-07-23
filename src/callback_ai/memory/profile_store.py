"""FR-13/14: cross-session weak-competency profile, keyed globally by
competency name (not per-job-post) -- PRD's "next session" framing implies a
skill-level weakness that should carry across roles, not a role-specific
reset each time. Revisit if that assumption doesn't hold up in practice."""
import json
from pathlib import Path

PROFILE_PATH = Path("data/profiles/global.json")


def load_profile(path: Path = PROFILE_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_profile(session_scores: dict[str, float], session_id: str, path: Path = PROFILE_PATH) -> dict:
    """session_scores: competency name -> this session's final score (0-1)."""
    profile = load_profile(path)

    for competency, score in session_scores.items():
        entry = profile.setdefault(
            competency, {"ema_score": score, "sessions_seen": 0, "last_score": score, "history": []}
        )
        entry["sessions_seen"] += 1
        entry["ema_score"] = 0.6 * score + 0.4 * entry["ema_score"]
        entry["last_score"] = score
        entry["history"].append({"session_id": session_id, "score": score})

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def weakest_competencies(profile: dict, n: int = 3) -> list[str]:
    return sorted(profile, key=lambda name: profile[name]["ema_score"])[:n]
