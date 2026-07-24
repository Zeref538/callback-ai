# callback-ai

An adaptive interview simulator. Most prep tools ask questions; this one asks
again.

- **It probes.** Say "I improved performance" and you'll be asked by how much
  and how you measured it — quoting your own words back at you. That follow-up
  is where real interviews are won or lost.
- **It budgets.** A fixed 12 questions, reallocated after every answer toward
  the competencies it's least sure about, not spread evenly over a checklist.
- **It cites.** Every score must quote your transcript verbatim. A score whose
  quote can't be found is rejected and regenerated rather than shown.
- **It remembers.** Weak competencies persist between sessions and bias the
  next session's budget toward them.

Three interviewers, each with their own manner: **Mira** (engineering manager,
warm), **Sam** (senior engineer, plain), **Rook** (principal engineer,
skeptical). Persona changes how hard you get pushed — never how you're graded.

See [PRD.md](PRD.md) for the full spec.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"     # Windows; use .venv/bin/pip elsewhere
cp .env.example .env
```

**Try it with no API key.** The mock provider answers every prompt type with
keyword heuristics, so the whole app runs offline:

```bash
CALLBACK_AI_PROVIDER=mock .venv/Scripts/python -m uvicorn callback_ai.api.app:app --reload
```

**Run it for real.** Get a key at [build.nvidia.com](https://build.nvidia.com)
(pick a model → "Get API Key"), put it in `.env` as `NIM_API_KEY`, leave
`CALLBACK_AI_PROVIDER=nim`, then:

```bash
.venv/Scripts/python -m uvicorn callback_ai.api.app:app --reload
```

Open <http://localhost:8000>. Check wiring at `/api/health` — it reports the
active provider, model, and whether a key is configured.

CLI instead of the browser:

```bash
.venv/Scripts/python -m callback_ai.cli.main \
  --job-post eval/fixtures/job_posts/01_backend_engineer.txt \
  --resume   eval/fixtures/resumes/sample_resume.txt \
  --persona  adversarial
```

Tests: `.venv/Scripts/python -m pytest` — 58 tests, all against fake providers,
so no key is needed to verify the logic.

## Architecture

`session_engine.py` runs an agent loop, not a fixed pipeline: each turn it
re-reads competency uncertainty and the probe/move-on/switch decision, then
dispatches the next tool (`interview/tools.py`) — ask, probe, score, or
reallocate. The guardrails that must never be left to model discretion are
enforced in code around those calls: the evidence gate's verbatim-quote check,
the fixed question budget, and persona-invariant scoring.

```
ingest/     job post + resume + portfolio link -> one merged claim inventory
            (conflicting claims are flagged, not silently resolved)
interview/  the agent loop, budget allocator, probe policy, personas, evidence gate
grading/    the debrief + model answers constrained to your real claims
memory/     JSONL session logs + cross-session weak-competency profile
llm/        NIM provider, Ollama fallback, offline mock, tolerant JSON parsing
api/, web/  FastAPI backend + a single static page (no build step)
eval/       the five metrics below
```

## Published metrics (PRD section 7)

| metric | target | status |
|---|---|---|
| Grading consistency (same transcript re-graded 5×) | ≤ 1 pt / 10 | **not yet measured** — `python -m eval.grading_consistency`, needs a real key |
| Discrimination (Spearman ρ vs. human ranking) | ρ ≥ 0.8 | **not yet measured** — corpus has 10 hand-written answers; the headline tier wants 20 |
| Probe precision (fires on vague, not specific) | ≥ 0.8 / ≤ 0.1 | **not yet measured** — `python -m eval.probe_precision` |
| Evidence-gate rejection rate | reported honestly | **not yet measured** — read from real session logs |
| Budget adaptivity (share vs. uniform) | measurably non-uniform | **not yet measured** — same source |

These are unmeasured, not hidden. Every eval script is built and unit-tested
against a fake provider (`tests/test_eval_*.py`), but real numbers require
running them against a live model. Run the four scripts plus a few real
sessions, then replace this table.

**Ship tier:** Minimum (rubric + adaptive 12-question session + evidence-quoted
debrief) is complete and runnable today. Good and Headline depend on the
metrics above.

## Known limits

- Sessions live in the server process. A restart or a redeploy drops any
  in-flight interview; the UI warns before you navigate away. Fine for a
  single-user demo, not for concurrent users.
- Portfolio-link parsing is best-effort HTML text extraction. JS-rendered
  sites won't parse; the session continues on resume + role instead of failing.
- The mock provider is a keyword heuristic, not a small model. It exists to
  make the app runnable and demoable offline, not to approximate real grading.
