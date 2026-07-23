"""FR-3: same job post -> same cached rubric; different post -> different rubric."""
import hashlib
import json
from pathlib import Path

from callback_ai.ingest.schemas import Rubric

CACHE_DIR = Path("data/rubric_cache")


def hash_job_post(job_post_text: str) -> str:
    return hashlib.sha256(job_post_text.strip().encode("utf-8")).hexdigest()[:16]


def get_cached(job_post_hash: str) -> Rubric | None:
    path = CACHE_DIR / f"{job_post_hash}.json"
    if not path.exists():
        return None
    return Rubric.model_validate_json(path.read_text(encoding="utf-8"))


def put_cached(rubric: Rubric) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{rubric.job_post_hash}.json"
    path.write_text(rubric.model_dump_json(indent=2), encoding="utf-8")
