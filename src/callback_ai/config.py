"""Environment-driven settings. Loaded once at import time."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # "nim" (default) or "mock" -- mock runs the whole app offline with no API key.
    provider: str = os.getenv("CALLBACK_AI_PROVIDER", "nim").lower()

    nim_api_key: str = os.getenv("NIM_API_KEY", "")
    nim_base_url: str = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    # NVIDIA retired meta/llama-3.1-8b-instruct on 2026-08-26 (every call then
    # returned 410 Gone). On 2026-09-26 most models in NIM's /v1/models list
    # answered 404; two responded. Llama 3.2 11B returned invalid JSON (single-
    # quoted strings, placeholder values copied verbatim) on 3 of 3 resume parses,
    # which failed every session that included a resume. Nemotron 3 Super parsed
    # it correctly 3 of 3 times and ran a full interview. It is slower (~23s to
    # start, 8-25s per answer vs ~1s before) and its job-post rubric varies run to
    # run, which the rubric cache absorbs by reusing the first parse per post.
    nim_model: str = os.getenv("NIM_MODEL", "nvidia/nemotron-3-super-120b-a12b")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    question_budget: int = 12
    # 70B models can take 30s+ on a cold request; 20s was too tight and timed
    # out the first real call. Override with REQUEST_TIMEOUT_S if needed.
    request_timeout_s: float = float(os.getenv("REQUEST_TIMEOUT_S", "60"))
    max_regenerate_attempts: int = 1  # evidence-gate: one retry, then flag low-confidence


settings = Settings()
