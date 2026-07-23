"""Discrimination: Spearman rho between the agent's ranking and a human
ranking of hand-written answers spanning weak to strong. Target (PRD
section 7): rho >= 0.8.

ponytail: fixtures/answers/graded_corpus.json currently has 10 hand-written
answers, not the 20 the PRD's headline tier calls for -- grow the corpus
before treating this number as final.

Needs a real LLM (NIM_API_KEY set) to produce a real number -- run as:
    python -m eval.discrimination
"""
import json
from pathlib import Path

from callback_ai.interview.coverage_scorer import score_answer
from callback_ai.interview.evidence_gate import EvidenceGate
from callback_ai.llm.client import ChatProvider

CORPUS_PATH = Path(__file__).parent / "fixtures" / "answers" / "graded_corpus.json"
COMPETENCY = "General"
DESCRIPTION = "Overall answer quality and specificity"


def _rank(values: list[float]) -> list[float]:
    """Average-rank ranking (ties share the mean rank), stdlib only."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def spearman_rho(a: list[float], b: list[float]) -> float:
    ra, rb = _rank(a), _rank(b)
    n = len(a)
    mean_ra, mean_rb = sum(ra) / n, sum(rb) / n
    cov = sum((ra[i] - mean_ra) * (rb[i] - mean_rb) for i in range(n))
    var_a = sum((x - mean_ra) ** 2 for x in ra) ** 0.5
    var_b = sum((x - mean_rb) ** 2 for x in rb) ** 0.5
    return cov / (var_a * var_b) if var_a and var_b else 0.0


def measure_discrimination(chat: ChatProvider, corpus_path: Path = CORPUS_PATH) -> dict:
    corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    agent_scores, human_scores = [], []

    for item in corpus:
        gate = EvidenceGate(max_regenerate_attempts=1)
        result = score_answer(item["question"], item["answer"], COMPETENCY, DESCRIPTION, chat, gate)
        agent_scores.append(result.result.coverage_score)
        human_scores.append(item["human_score"])

    rho = spearman_rho(agent_scores, human_scores)
    return {"n": len(corpus), "rho": rho, "meets_target": rho >= 0.8}


if __name__ == "__main__":
    from callback_ai.llm.router import Router

    print(measure_discrimination(Router()))
