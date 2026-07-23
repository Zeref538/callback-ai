# PRD — Adaptive Interview Simulator Agent

**Status:** draft · **Target start:** August 2026 · **Est. effort:** ~4 weeks
part-time · **Name:** TBD

---

## 1. Problem

Interview-prep tools ask canned questions from a static list. Real interviewers
do two things those tools don't:

1. **They probe.** A vague answer earns a follow-up — *"you said you improved
   performance; by how much, and how did you measure it?"* — and that follow-up
   is where candidates actually get filtered.
2. **They budget.** An interviewer has ~12 questions and spends them where they
   are still uncertain about the candidate, not evenly across a checklist.

The result: candidates practice against a quiz, then fail at the probing. They
also get feedback that is either generic ("be more specific") or flattering,
because most LLM graders over-praise and cite nothing.

## 2. Goals

- Run an interview that **adapts** — question selection driven by a rubric
  derived from the specific job post, and by what the candidate has already
  revealed.
- Grade with **evidence**: every score cites a verbatim quote from the
  transcript.
- Show **improvement over time** — weak competencies persist across sessions
  and future sessions target them.

### Non-goals (v1)

- Not a job board, resume rewriter, or career platform.
- No user accounts, teams, or multi-user features.
- No video/body-language analysis.
- Not a hiring tool — this evaluates practice answers for the candidate's own
  use, never real applicants.

## 3. Users

| user | need |
|---|---|
| **Primary — job-seeking student/junior engineer (me)** | Realistic practice for a specific role, with feedback specific enough to act on |
| Secondary — recruiter/hiring manager viewing the portfolio | Understand in 60 seconds what this is and that it works |

## 4. User stories

1. As a candidate, I paste a job post and my resume, and get an interview
   tailored to *that* role rather than generic questions.
2. As a candidate, when I give a vague answer, I get pushed on it — like a real
   interviewer would — so I learn to answer with specifics.
3. As a candidate, I want scores I can trust, so each one must point at what I
   actually said.
4. As a candidate, I want to know what a stronger version of my answer sounds
   like.
5. As a returning candidate, I want the next session to focus on what I was
   weak at last time, and to tell me if I improved.

## 5. Functional requirements

### 5.1 Rubric derivation
- **FR-1** Parse a job post into weighted competencies (technical areas,
  seniority bar, soft skills) as validated JSON.
- **FR-2** Parse the resume into a claim inventory (projects, metrics, tech)
  the interviewer can reference by name — e.g. probing a stated metric.
- **FR-3** Same job post → same rubric (cached); different job post →
  measurably different rubric.

### 5.2 Interview loop
- **FR-4** Fixed question budget per session (default 12, configurable).
- **FR-5** The agent **allocates** budget across competencies by weight and by
  remaining uncertainty; allocation is re-evaluated after every answer.
- **FR-6** After each answer, score its coverage of the target rubric item and
  decide: **probe deeper**, **move on**, or **switch competency**.
- **FR-7** Probes must reference the candidate's own words.
- **FR-8** Every decision is logged (competency, remaining budget, why).

### 5.3 Grading & report
- **FR-9** Per-competency scores, each accompanied by a verbatim transcript
  quote.
- **FR-10** **Evidence gate:** a score whose quote does not appear in the
  transcript is rejected and regenerated. Rejections are counted.
- **FR-11** For weak answers, generate a stronger model answer using the
  candidate's real project facts (no invented achievements).
- **FR-12** Report includes overall readiness summary and top 3 things to fix.

### 5.4 Memory
- **FR-13** Persist a weak-competency profile between sessions.
- **FR-14** New sessions bias budget toward persisted weak areas.
- **FR-15** Report a delta vs the previous session on repeated competencies.

### 5.5 Interfaces
- **FR-16** CLI for a full text session.
- **FR-17** Minimal web UI (terminal-styled, consistent with portfolio).
- **FR-18** *(stretch)* Voice mode — speak answers, transcribed locally.

## 6. Non-functional requirements

- **NFR-1 Cost:** runs on NVIDIA's free API tier; a full session must cost ₱0.
- **NFR-2 Latency:** < 5s to next question on a warm session.
- **NFR-3 Fallback:** the frequent, cheap call (coverage scoring) can run on a
  local Ollama model if the API is rate-limited.
- **NFR-4 Privacy:** resume content stays local except for the API calls
  required to run the session; no third-party storage; transcripts local only.
- **NFR-5 Reproducibility:** temperature 0 where determinism matters (rubric,
  grading); session logs replayable.
- **NFR-6 No fabrication:** model answers may only use facts present in the
  resume/transcript.

## 7. Success metrics (published in the README)

| metric | definition | target |
|---|---|---|
| **Grading consistency** | score variance when the same transcript is graded 5× | ≤ 1 pt on a 10-pt scale |
| **Discrimination** | Spearman ρ between agent ranking and human ranking of 20 hand-written answers spanning weak→strong | ρ ≥ 0.8 |
| **Probe precision** | probe fires on vague answers, not specific ones | ≥ 0.8 on vague, ≤ 0.1 on specific |
| **Evidence-gate rejection rate** | % of draft scores rejected for unsupported quotes | reported honestly (the trust number) |
| **Budget adaptivity** | share of questions allocated to weak competencies vs uniform | measurably non-uniform |

Ship criteria tiers:

- **Minimum:** rubric + adaptive 12-question session + evidence-quoted report.
- **Good:** + cross-session memory with measured improvement, consistency eval.
- **Headline:** ρ ≥ 0.8, probe precision ≥ 0.8, zero unsupported scores.

## 8. Milestones

| week | deliverable | exit gate |
|---|---|---|
| 1 | Rubric + resume parsing, single-question grading with evidence gate | 5 real job posts → sensible rubrics; no score without a verbatim quote |
| 2 | Budget allocator, coverage scorer, probe policy, session logging, CLI | full 12-question session; decision log shows budget shifting to weak areas |
| 3 | Report generation, model answers, cross-session memory, web UI | two sessions on one job post show re-allocation + improvement delta |
| 4 | Evaluation suite, README, demo GIF, portfolio card | all five metrics measured and published |

## 9. Risks

| risk | mitigation |
|---|---|
| Grader flatters (LLM over-praise) | Calibrate against hand-written weak-answer set; add per-band anchor examples to the rubric prompt |
| Probing feels like a quiz | Probe policy is the core product — build and test it in week 2, not last |
| Free-tier rate limits | Cache rubrics, keep sessions short, local Ollama for the high-frequency coverage call |
| Scope creep into a career platform | Non-goals section is binding; v1 = one job post, one session, one report |
| Resume PII in prompts | Document exactly what leaves the machine; offer a redaction toggle |

## 10. Open questions

- Question budget: fixed at 12, or scaled by role seniority?
- Should the agent simulate interviewer *personas* (friendly vs adversarial),
  or is one neutral interviewer enough for v1?
- Voice mode in v1 or deferred — does typing answers undermine realism enough
  to justify the extra scope?

## 11. Stack

Python · NVIDIA NIM free API (Llama/Nemotron class) · Ollama fallback ·
FastAPI + React terminal-styled UI · JSONL session logs · pytest.
