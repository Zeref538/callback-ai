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
    # 8B by default: on NIM's free tier the 70B sits in a serverless queue and
    # took ~55-110s per call in testing, vs ~0.4-1.6s for the 8B, which is the
    # difference between an interactive interview and an unusable one. The 8B is
    # plenty for question generation and scoring. Set NIM_MODEL to the 70B if you
    # want higher-quality grading and can tolerate the latency.
    nim_model: str = os.getenv("NIM_MODEL", "meta/llama-3.1-8b-instruct")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    question_budget: int = 12
    # 70B models can take 30s+ on a cold request; 20s was too tight and timed
    # out the first real call. Override with REQUEST_TIMEOUT_S if needed.
    request_timeout_s: float = float(os.getenv("REQUEST_TIMEOUT_S", "60"))
    max_regenerate_attempts: int = 1  # evidence-gate: one retry, then flag low-confidence


settings = Settings()
