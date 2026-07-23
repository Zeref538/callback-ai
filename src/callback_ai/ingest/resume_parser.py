"""FR-2: resume text -> claim inventory (projects, metrics, tech)."""
import json

from callback_ai.ingest.schemas import Claim
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """You are extracting factual claims from a resume, so an interviewer
can later reference them by name. Return ONLY JSON: {"claims": [
  {"claim_id": "r1", "subject": "project|skill|metric", "text": "...",
   "tech": ["..."], "metric_value": "<e.g. '30%' or null>"}
]}
Do not invent facts not present in the text. Extract only what is written."""


def parse_resume(resume_text: str, chat: ChatProvider) -> list[Claim]:
    raw = chat.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": resume_text},
        ],
        temperature=0.0,
    )
    data = json.loads(raw)
    return [Claim(source="resume", **c) for c in data["claims"]]
