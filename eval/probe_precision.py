"""Probe precision: the probe fires on vague answers, not specific ones.
Target (PRD section 7): >= 0.8 on vague, <= 0.1 on specific.

Needs a real LLM (NIM_API_KEY set) to produce a real number -- run as:
    python -m eval.probe_precision
"""
import json
from pathlib import Path

from callback_ai.interview.budget_allocator import CompetencyState
from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.interview.evidence_gate import EvidenceGate
from callback_ai.interview.persona import get_persona
from callback_ai.interview.probe_policy import decide
from callback_ai.llm.client import ChatProvider

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "answers" / "vague_and_specific.json"
COMPETENCY = "General"
DESCRIPTION = "Overall answer quality and specificity"


def measure_probe_precision(chat: ChatProvider, persona_name: str = "neutral", fixture_path: Path = FIXTURE_PATH) -> dict:
    items = json.loads(fixture_path.read_text(encoding="utf-8"))
    persona = get_persona(persona_name)

    fires = {"vague": [], "specific": []}
    for item in items:
        gate = EvidenceGate(max_regenerate_attempts=1)
        result = score_answer(item["question"], item["answer"], COMPETENCY, DESCRIPTION, chat, gate)
        state = CompetencyState(weight=1.0)  # fresh per item, so probe_count cap doesn't cross items
        action = decide(result.result.coverage_score, state, persona)
        fires[item["label"]].append(action == "probe")

    vague_rate = sum(fires["vague"]) / len(fires["vague"]) if fires["vague"] else None
    specific_rate = sum(fires["specific"]) / len(fires["specific"]) if fires["specific"] else None

    return {
        "vague_probe_rate": vague_rate,
        "specific_probe_rate": specific_rate,
        "meets_target": (vague_rate is not None and vague_rate >= 0.8)
        and (specific_rate is not None and specific_rate <= 0.1),
    }


if __name__ == "__main__":
    from callback_ai.llm.router import Router

    print(measure_probe_precision(Router()))
