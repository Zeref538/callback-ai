"""FR-11: for weak answers, generate a stronger model answer using the
candidate's real claims. Constrained to those facts (NFR-6: no fabrication)."""
from callback_ai.ingest.schemas import Claim
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """You are coaching a candidate on their weak answer to an
interview question about "{competency}". Write a stronger version of their
answer, but you MUST only use facts from the claims list below -- do not
invent metrics, projects, or outcomes that aren't listed. If the claims don't
support a strong answer, say what additional detail the candidate should
gather instead of inventing it. Return only the improved answer text.

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
