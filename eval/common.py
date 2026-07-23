"""Shared helpers for pulling metrics out of real session logs (data/sessions/*.jsonl)."""
import json
from pathlib import Path

from callback_ai.memory.session_store import SESSIONS_DIR


def load_all_sessions(sessions_dir: Path = SESSIONS_DIR) -> list[list[dict]]:
    if not sessions_dir.exists():
        return []
    sessions = []
    for path in sessions_dir.glob("*.jsonl"):
        with path.open(encoding="utf-8") as f:
            sessions.append([json.loads(line) for line in f if line.strip()])
    return sessions


def evidence_gate_rejection_rate(sessions: list[list[dict]]) -> float | None:
    """Averages the per-session rejection rate logged in each session_end event."""
    rates = [
        e["evidence_gate_rejection_rate"]
        for session in sessions
        for e in session
        if e["type"] == "session_end" and "evidence_gate_rejection_rate" in e
    ]
    return sum(rates) / len(rates) if rates else None


def budget_adaptivity(sessions: list[list[dict]]) -> dict[str, float] | None:
    """Share of questions allocated to each competency, across all sessions.
    A uniform baseline would be 1/num_competencies per competency; report the
    actual share so it's visible whether allocation is measurably non-uniform."""
    counts: dict[str, int] = {}
    total = 0
    for session in sessions:
        for e in session:
            if e["type"] == "question":
                counts[e["competency"]] = counts.get(e["competency"], 0) + 1
                total += 1
    if total == 0:
        return None
    return {name: count / total for name, count in counts.items()}
