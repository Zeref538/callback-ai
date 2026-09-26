"""Generate docs/index.html (the case study) from the real artifacts.

    python docs/build_site.py

The eval numbers come from eval/results/nemotron-run*.json, the demo's rubric
from eval/results/rubric-backend.json, and the demo's thresholds and caps from
the app's own Python modules. Nothing measured is typed in by hand. The prose
does quote some numbers, so check() recomputes each one and fails the build if
the page no longer says it.
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from callback_ai.config import settings  # noqa: E402
from callback_ai.interview import budget_allocator, probe_policy  # noqa: E402
from callback_ai.interview.persona import PERSONAS  # noqa: E402

RESULTS = ROOT / "eval" / "results"
TEMPLATE = ROOT / "docs" / "template.html"
OUT = ROOT / "docs" / "index.html"
ALPHA = 0.6


def main() -> None:
    runs = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(RESULTS.glob("nemotron-run*.json"))]
    assert len(runs) == 2, f"expected 2 runs, found {len(runs)}"
    rubric = json.loads((RESULTS / "rubric-backend.json").read_text(encoding="utf-8"))
    # The EMA weight is a literal inside update_after_answer; fail if it changes.
    assert f"{ALPHA} * coverage_score" in inspect.getsource(budget_allocator.update_after_answer)

    data = {
        "runs": runs,
        "rubric": [{"name": c["name"].replace("‑", "-"), "weight": c["weight"]} for c in rubric["competencies"]],
        "personas": {k: {"name": p.name, "threshold": p.probe_threshold} for k, p in PERSONAS.items()},
        "maxProbes": probe_policy.MAX_PROBES_PER_COMPETENCY,
        "maxAsks": budget_allocator.MAX_ASKS_PER_COMPETENCY,
        "budget": settings.question_budget,
        "alpha": ALPHA,
    }
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*%%DATA%%*/", json.dumps(data, separators=(",", ":")))
    check(html, runs, data)
    OUT.write_text(html, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


def check(html: str, runs: list[dict], data: dict) -> None:
    """Fail loudly rather than publish a number the results do not support."""
    rhos = {f"{r['discrimination']['rho']:.2f}" for r in runs}
    assert len(rhos) == 1, f"runs disagree on rho: {rhos}; the page says 'both runs gave the same number'"
    rho = rhos.pop()
    assert rho in html and f"&rho; {rho}" in html, f"page does not state rho {rho}"
    assert f"{runs[0]['discrimination']['rho']:.3f}" in html, "exact rho missing from the technical text"
    for r in runs:
        assert f"<b>{r['consistency']['stdev_10pt']:.2f}</b>" in html, "regrade spread missing"
        assert r["probe_precision"]["vague_probe_rate"] == 1.0 and r["probe_precision"]["specific_probe_rate"] == 0.0
    assert f"{max(r['consistency']['stdev_10pt'] for r in runs):.2f} / 10" in html, "hero regrade spread is stale"
    probed = sum(i["probed"] for r in runs for i in r["probe_precision"]["items"] if i["label"] == "vague")
    vague = sum(i["label"] == "vague" for r in runs for i in r["probe_precision"]["items"])
    assert f"{probed} of {vague}" in html, "follow-up count is stale"
    # "every answer I rated 3 to 6 got a 2 or a 3"
    for r in runs:
        d = r["discrimination"]
        mids = [a for h, a in zip(d["human_scores"], d["agent_scores"]) if 3 <= h <= 6]
        assert mids and all(round(a * 10) in (2, 3) for a in mids), f"middle-squeeze claim no longer true: {mids}"
    for p in data["personas"].values():
        assert f"<b>{p['threshold']:.2f}</b>" in html, f"threshold {p['threshold']} not on the page"
    assert chr(0x2014) not in html, "em dash on the page"
    print(f"  checked: rho {rho}, spread {[r['consistency']['stdev_10pt'] for r in runs]}, probes {probed}/{vague}")


if __name__ == "__main__":
    main()
