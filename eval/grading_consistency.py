"""Grading consistency: score variance when the same transcript is graded 5x.
Target (PRD section 7): <= 1 pt on a 10-pt scale.

Needs a real LLM (NIM_API_KEY set) to produce a real number -- run as:
    python -m eval.grading_consistency
"""
import statistics

from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.interview.evidence_gate import EvidenceGate
from callback_ai.llm.client import ChatProvider

N_REGRADES = 5


def measure_consistency(
    question: str, answer: str, competency: str, description: str, chat: ChatProvider, n: int = N_REGRADES
) -> dict:
    scores = []
    for _ in range(n):
        gate = EvidenceGate(max_regenerate_attempts=1)  # fresh gate per regrade -- consistency, not rejection rate
        result = score_answer(question, answer, competency, description, chat, gate)
        scores.append(result.result.coverage_score * 10)  # 0-1 -> 10-pt scale

    variance = statistics.pstdev(scores) if len(scores) > 1 else 0.0
    return {"scores_10pt": scores, "stdev_10pt": variance, "meets_target": variance <= 1.0}


if __name__ == "__main__":
    from callback_ai.llm.router import Router

    result = measure_consistency(
        question="Tell me about a time you improved performance.",
        answer=(
            "I profiled our payment webhook handler, found N+1 queries hitting Postgres, "
            "added a Redis cache in front of the lookup, and cut p99 latency from 800ms to 120ms."
        ),
        competency="System Design",
        description="Designs scalable systems",
        chat=Router(),
    )
    print(result)
