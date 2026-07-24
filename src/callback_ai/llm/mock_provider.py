"""Offline stand-in for a real model, selected with CALLBACK_AI_PROVIDER=mock.

Two jobs:
1. Let the whole app -- CLI, API, web UI -- be run and demoed with no API key
   and no network, which is also how the deployed build stays clickable if the
   key is missing or the free tier is exhausted.
2. Exercise every code path (rubric -> claims -> question -> score -> probe ->
   report) so integration bugs surface here instead of on a live key.

It is deliberately dumb: keyword heuristics, no model. Answers that contain
numbers/specifics score well, vague ones score badly, which is enough to make
the probe policy and budget allocator visibly do their thing in a demo.
"""
import json
import re

VAGUE_MARKERS = ("some", "stuff", "things", "a lot", "better", "improved it", "worked well", "various")
_NUMBER = re.compile(r"\d")


def _looks_specific(answer: str) -> bool:
    """A specific answer names numbers or concrete tech, not just adjectives."""
    if len(answer.split()) < 8:
        return False
    if _NUMBER.search(answer):
        return True
    return not any(m in answer.lower() for m in VAGUE_MARKERS)


def _longest_sentence(text: str) -> str:
    """Evidence quotes must be verbatim substrings, so slice, never paraphrase."""
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p.strip()]
    return max(parts, key=len) if parts else text.strip()


class MockProvider:
    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        system = messages[0]["content"] if messages else ""
        user = messages[-1]["content"] if len(messages) > 1 else ""

        if system.startswith("You are extracting a grading rubric"):
            return self._rubric(user)
        if system.startswith("You are extracting factual claims"):
            return self._claims(user)
        if system.startswith("You are scoring a candidate's interview answer"):
            return self._score_answer(system, user)
        if system.startswith("You are scoring a candidate's overall performance"):
            return self._score_competency(system)
        if system.startswith("You are coaching a candidate"):
            return self._model_answer(system)
        # Match on a fragment that survives the prompt's line wrapping -- the
        # real prompt breaks "Ask ONE follow-up\nquestion" across two lines.
        if "Ask ONE follow-up" in system:
            return self._probe(system)
        if "Ask ONE interview question" in system:
            return self._question(system)
        return "Tell me more about that."

    # ---- rubric ----
    def _rubric(self, job_post: str) -> str:
        text = job_post.lower()
        pool = [
            ("System Design", ("design", "architecture", "distributed", "scalab", "api")),
            ("Debugging & Incidents", ("incident", "debug", "postmortem", "production", "on-call")),
            ("Data & Correctness", ("sql", "database", "consistency", "idempot", "data")),
            ("Communication", ("communicat", "stakeholder", "collaborat", "mentor", "explain")),
            ("Testing & Quality", ("test", "quality", "review", "ci")),
        ]
        picked = [name for name, kws in pool if any(k in text for k in kws)]
        if len(picked) < 3:
            picked = [name for name, _ in pool[:4]]
        weight = round(1.0 / len(picked), 3)
        first_line = job_post.strip().splitlines()[0][:60] if job_post.strip() else None
        return json.dumps({
            "target_position": first_line,
            "competencies": [
                {"name": n, "weight": weight, "seniority_bar": "mid",
                 "description": f"Demonstrates {n.lower()} at the level this role expects."}
                for n in picked
            ],
        })

    # ---- claims ----
    def _claims(self, text: str) -> str:
        claims = []
        for i, line in enumerate(self._claim_lines(text)[:8]):
            metric = re.search(r"(\d+(?:\.\d+)?\s*%|\d+\s*(?:ms|s|x))", line)
            claims.append({
                "claim_id": f"c{i+1}",
                "subject": "metric" if metric else "project",
                "text": line[:180],
                "tech": re.findall(r"\b(Python|Go|Java|Redis|Postgres\w*|Django|Kubernetes|Terraform|SQL|React)\b", line),
                "metric_value": metric.group(1) if metric else None,
            })
        return json.dumps({"claims": claims})

    # ---- per-answer score + live feedback ----
    def _score_answer(self, system: str, user: str) -> str:
        answer = user.split("Answer:", 1)[-1].strip()
        specific = _looks_specific(answer)
        score = 0.82 if specific else 0.24
        return json.dumps({
            "coverage_score": score,
            "evidence_quote": _longest_sentence(answer),
            "vagueness_signals": [] if specific else ["no concrete numbers or named systems"],
            "live_feedback": {
                "verdict": "correct" if specific else "incomplete",
                "suggestion": (
                    "Good -- you named specifics and a measurable outcome."
                    if specific else
                    "Too general. Name the system, what you changed, and a number that shows the impact."
                ),
            },
        })

    # ---- final per-competency score ----
    def _score_competency(self, system: str) -> str:
        transcript = system.split("Their answers on this competency:", 1)[-1].strip()
        specific = _looks_specific(transcript)
        return json.dumps({
            "score": 0.78 if specific else 0.35,
            "evidence_quote": _longest_sentence(transcript),
        })

    # ---- generated text ----
    def _question(self, system: str) -> str:
        competency = self._between(system, 'targeting the competency "', '"') or "your experience"
        claims = [c.strip("- ").strip() for c in system.split("Candidate's claims:")[-1].splitlines() if c.strip().startswith("-")]
        if claims:
            return f"You mention: \"{claims[0][:90]}\". Walk me through the {competency.lower()} decisions behind that -- what did you weigh, and what did you measure?"
        return f"Tell me about a time your work was judged on {competency.lower()}. What was the situation and what did you do?"

    def _probe(self, system: str) -> str:
        answer = self._between(system, "Candidate's answer:", "\nVagueness signals") or ""
        snippet = answer.strip()[:70]
        return f"You said \"{snippet}...\" -- give me the specifics: which system, what exactly changed, and what number moved?"

    def _model_answer(self, system: str) -> str:
        claims = [c.strip("- ").strip() for c in system.split("Candidate's claims:")[-1].splitlines() if c.strip().startswith("-")]
        if not claims:
            return ("Not enough detail on file to write a stronger answer. Before the next session, write down "
                    "one project with the system involved, the change you made, and a number that moved.")
        return (f"A stronger version anchors on something you actually did: \"{claims[0][:120]}\". "
                "State the situation, the specific change you made, and the measured result -- in that order, in about 60 seconds.")

    @staticmethod
    def _claim_lines(text: str) -> list[str]:
        """Skip name/section headers -- quoting "Jane Doe - Backend Engineer"
        back at the candidate as if it were a project makes the demo look broken."""
        HEADERS = ("projects:", "skills:", "experience:", "education:", "summary:", "about")
        out = []
        for raw in text.splitlines():
            line = raw.strip(" -•\t")
            low = line.lower()
            if len(line) < 30 or low.startswith(HEADERS) or low.endswith(":"):
                continue
            if " " not in line.strip():
                continue
            out.append(line)
        return out

    @staticmethod
    def _between(text: str, start: str, end: str) -> str | None:
        i = text.find(start)
        if i == -1:
            return None
        j = text.find(end, i + len(start))
        return text[i + len(start): j if j != -1 else None].strip()
