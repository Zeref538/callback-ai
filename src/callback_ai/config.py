"""Environment-driven settings. Loaded once at import time."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    nim_api_key: str = os.getenv("NIM_API_KEY", "")
    nim_base_url: str = os.getenv("NIM_BASE_URL", "https://integrate.api.nvidia.com/v1")
    nim_model: str = os.getenv("NIM_MODEL", "meta/llama-3.1-70b-instruct")
    ollama_host: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    question_budget: int = 12
    request_timeout_s: float = 20.0
    max_regenerate_attempts: int = 1  # evidence-gate: one retry, then flag low-confidence


settings = Settings()
