"""Run the three model-graded evals once and save everything they measured.

    NIM_MODEL=<model id> python -m eval.run_all <run-name>

Writes eval/results/<run-name>.json. Calls NVIDIA NIM directly instead of the
app's Router, because the Router falls back to Ollama on a rate limit and the
saved numbers must all come from the one model named in the file.
"""
import json
import sys
import time
from pathlib import Path

from callback_ai.config import settings
from callback_ai.llm.nim_provider import NimProvider
from eval.discrimination import measure_discrimination
from eval.grading_consistency import measure_consistency
from eval.probe_precision import measure_probe_precision

RESULTS_DIR = Path(__file__).parent / "results"

# The same transcript grading_consistency.py's own __main__ uses.
CONSISTENCY_CASE = dict(
    question="Tell me about a time you improved performance.",
    answer=(
        "I profiled our payment webhook handler, found N+1 queries hitting Postgres, "
        "added a Redis cache in front of the lookup, and cut p99 latency from 800ms to 120ms."
    ),
    competency="System Design",
    description="Designs scalable systems",
)


def main(run_name: str) -> Path:
    chat = NimProvider()
    started = time.time()
    out = {
        "model": settings.nim_model,
        "run": run_name,
        "date": time.strftime("%Y-%m-%d"),
        "discrimination": measure_discrimination(chat),
        "consistency": measure_consistency(chat=chat, **CONSISTENCY_CASE),
        "probe_precision": measure_probe_precision(chat),
    }
    out["seconds"] = round(time.time() - started, 1)
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{run_name}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)   # never leave a half-written result behind
    return path


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else "run"))
