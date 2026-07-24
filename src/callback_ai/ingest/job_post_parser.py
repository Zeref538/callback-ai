"""FR-1: job post -> weighted competencies. FR-3: caching by hash."""
from callback_ai.llm.json_parse import parse_json_response

from callback_ai.ingest.rubric_cache import get_cached, hash_job_post, put_cached
from callback_ai.ingest.schemas import Competency, Rubric
from callback_ai.llm.client import ChatProvider

SYSTEM_PROMPT = """You are extracting a grading rubric from a job posting.
Return ONLY JSON: {"target_position": "<title or null>", "competencies": [
  {"name": "...", "weight": 0.0-1.0, "seniority_bar": "...", "description": "..."}
]}
Weights across all competencies must sum to approximately 1.0.
Include technical areas, seniority expectations, and soft skills the post implies.
Same job post text must always produce the same competencies."""


def parse_job_post(job_post_text: str, chat: ChatProvider, use_cache: bool = True) -> Rubric:
    job_post_hash = hash_job_post(job_post_text)

    if use_cache:
        cached = get_cached(job_post_hash)
        if cached is not None:
            return cached

    raw = chat.chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": job_post_text},
        ],
        temperature=0.0,
    )
    data = parse_json_response(raw)
    rubric = Rubric(
        job_post_hash=job_post_hash,
        target_position=data.get("target_position"),
        competencies=[Competency(**c) for c in data["competencies"]],
    )

    if use_cache:
        put_cached(rubric)
    return rubric
