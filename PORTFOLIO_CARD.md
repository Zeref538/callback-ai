# Portfolio card copy

**Title:** callback-ai — an interviewer that actually follows up

**One-liner:** Practice interviews with an agent that probes vague answers
like a real interviewer, budgets its 12 questions toward what you're weakest
at, and grades every score against a verbatim quote from your own transcript
— never generic praise.

**60-second pitch:**
Most interview-prep tools ask canned questions from a static list. This one
runs an agent loop: it reads a job post and your resume/portfolio, derives a
weighted competency rubric, and interviews you against it — reallocating its
fixed question budget after every answer toward the competencies you're
least certain about. Give a vague answer and it probes, quoting your own
words back at you. Every score in the final report is checked against a
verbatim quote from the transcript; if the quote can't be found, the score is
rejected and regenerated rather than shown. Weak areas persist across
sessions, so the next practice run starts where the last one left off.

**Demo:** _(record a ~60s terminal or web-UI walkthrough here once metrics
are measured — see README.md's published-metrics table)_

**Stack:** Python agent loop · NVIDIA NIM (free tier) with local Ollama
fallback · FastAPI · a single static terminal-styled page (no build step) ·
JSONL session logs · pytest.
