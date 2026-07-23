# callback-ai

An adaptive interview simulator agent. Unlike a canned-question quiz, it:

- **Probes vague answers** — a follow-up that references your own words, the
  way a real interviewer pushes for specifics.
- **Budgets questions by uncertainty** — a fixed 12-question session spends
  more of its budget where you're weakest, not evenly across a checklist.
- **Grades with evidence** — every score is checked against a verbatim quote
  from your own answer; a score whose quote can't be found is rejected and
  regenerated rather than shown.
- **Remembers across sessions** — weak competencies persist and bias the next
  session's question budget toward them.

See [PRD.md](PRD.md) for the full product spec and
[the implementation plan](https://github.com/Zeref538/callback-ai) for the
week-by-week build.

## Architecture

`session_engine.py` runs an agent loop, not a fixed pipeline: each turn it
re-reads competency uncertainty and the deterministic probe/move-on/switch
decision, then dispatches to the next tool (`interview/tools.py`) — ask a
fresh question, probe, score, or reallocate. Guardrails that must never be
left to model discretion (the evidence gate's verbatim-quote check, the fixed
question budget, persona-invariant scoring) are enforced in code around the
tool calls.

```
ingest/       job post + resume + portfolio-link -> one merged claim inventory
interview/    the agent loop, budget allocator, probe policy, personas, evidence gate
grading/      final report + evidence-constrained model answers
memory/       JSONL session logs + cross-session weak-competency profile
api/, web/    FastAPI backend + a single static terminal-styled page
eval/         the 5 metrics below
```

## Setup

```
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
cp .env.example .env   # fill in NIM_API_KEY
```

Run a CLI session:
```
python -m callback_ai.cli.main --job-post eval/fixtures/job_posts/01_backend_engineer.txt \
    --resume eval/fixtures/resumes/sample_resume.txt --persona neutral
```

Run the web UI:
```
.venv/Scripts/python -m uvicorn callback_ai.api.app:app --reload
```
then open http://localhost:8000.

Run tests: `pytest` (47 tests, all run against a fake LLM provider — no API
key needed to verify the logic).

## Published metrics (PRD section 7)

| metric | target | status |
|---|---|---|
| Grading consistency (variance re-grading the same transcript 5x) | ≤ 1 pt / 10 | not yet measured — `python -m eval.grading_consistency` needs `NIM_API_KEY` |
| Discrimination (Spearman ρ, agent vs. human ranking) | ρ ≥ 0.8 | not yet measured — corpus currently has 10 hand-written answers (`eval/fixtures/answers/graded_corpus.json`), PRD's headline tier wants 20 |
| Probe precision (fires on vague, not specific) | ≥ 0.8 vague / ≤ 0.1 specific | not yet measured — `python -m eval.probe_precision` |
| Evidence-gate rejection rate | reported honestly | not yet measured — pulled from real session logs via `eval/common.py`, needs sessions run against a live model |
| Budget adaptivity (share vs. uniform baseline) | measurably non-uniform | not yet measured — same source |

**Why these are unmeasured:** every eval script is built and unit-tested
against a fake chat provider (see `tests/test_eval_*.py`), but producing the
actual numbers requires running them against a live NIM model and a handful
of real sessions, which needs `NIM_API_KEY` set. Run the four scripts above
plus a few real CLI/web sessions, then replace this table with the results.

**Ship tier:** Minimum (rubric + adaptive 12-question session + evidence-quoted
report) is complete. Good and Headline tiers depend on the metrics above.
