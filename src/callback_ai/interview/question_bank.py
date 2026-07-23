"""Persona-flavored question and probe generation. FR-7: probes must
reference the candidate's own words."""
from callback_ai.ingest.schemas import Claim
from callback_ai.interview.persona import Persona
from callback_ai.llm.client import ChatProvider

QUESTION_SYSTEM_PROMPT = """You are an interviewer with this persona: {tone}.
Ask ONE interview question targeting the competency "{competency}"
({description}). Reference one of the candidate's claims below if relevant,
so the question feels tailored, not generic. Return ONLY the question text,
no preamble.

Candidate's claims:
{claims}"""

PROBE_SYSTEM_PROMPT = """You are an interviewer with this persona: {tone}.
The candidate's last answer was vague on "{competency}". Ask ONE follow-up
question that quotes or directly references their own words below to push
for specifics (a number, a name, a mechanism). Return ONLY the question text.

Candidate's answer: {answer}
Vagueness signals noticed: {vagueness_signals}"""


def _format_claims(claims: list[Claim]) -> str:
    return "\n".join(f"- {c.text}" for c in claims) or "(none provided)"


def generate_question(
    competency: str, description: str, claims: list[Claim], persona: Persona, chat: ChatProvider
) -> str:
    return chat.chat(
        [
            {
                "role": "system",
                "content": QUESTION_SYSTEM_PROMPT.format(
                    tone=persona.tone, competency=competency, description=description, claims=_format_claims(claims)
                ),
            },
        ],
        temperature=0.3,
    ).strip()


def generate_probe(
    competency: str, answer: str, vagueness_signals: list[str], persona: Persona, chat: ChatProvider
) -> str:
    return chat.chat(
        [
            {
                "role": "system",
                "content": PROBE_SYSTEM_PROMPT.format(
                    tone=persona.tone,
                    competency=competency,
                    answer=answer,
                    vagueness_signals=", ".join(vagueness_signals) or "none listed",
                ),
            },
        ],
        temperature=0.3,
    ).strip()
