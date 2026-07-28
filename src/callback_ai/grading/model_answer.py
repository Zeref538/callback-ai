"""FR-11: for weak answers, generate a stronger model answer using the
candidate's real claims. Constrained to those facts (NFR-6: no fabrication)."""
from callback_ai.ingest.schemas import Claim
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """A candidate gave a weak answer to an interview question about
"{competency}". Rewrite it as the answer they SHOULD have given, written in
their own voice -- first person ("I built...", "I reduced..."), as if they are
speaking it aloud in the interview.

Rules:
- Write ONLY the spoken answer. No preamble, no "Here's a stronger version",
  no third-person commentary about "the candidate" or "their answer".
- Use ONLY facts from the claims list below. Do not invent metrics, projects,
  or outcomes that aren't listed.
- If the claims don't support a strong answer, write one first-person sentence
  saying what specific detail they'd need to gather -- still in their voice
  ("I'd want to have the exact latency numbers on hand here").

Candidate's claims:
{claims}

Their weak answer: {weak_answer}"""


def generate_model_answer(competency: str, weak_answer: str, claims: list[Claim], chat: ChatProvider) -> str:
    claims_text = "\n".join(f"- {c.text}" for c in claims) or "(no claims on file)"
    return chat.chat(
        [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(competency=competency, claims=claims_text, weak_answer=weak_answer),
            }
        ],
        temperature=0.0,
    ).strip()
