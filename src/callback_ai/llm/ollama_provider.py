"""Local Ollama fallback, used when NIM is rate-limited (NFR-3)."""
import httpx

from callback_ai.config import settings
from callback_ai.llm.client import ProviderError


class OllamaProvider:
    def __init__(self):
        self.host = settings.ollama_host.rstrip("/")
        self.model = settings.ollama_model

    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        body = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if json_schema is not None:
            body["format"] = "json"

        try:
            resp = httpx.post(f"{self.host}/api/chat", json=body, timeout=settings.request_timeout_s)
        except httpx.HTTPError as e:
            raise ProviderError(
                f"Ollama fallback unreachable at {self.host} ({e}). Start Ollama or wait out the rate limit."
            ) from e

        if resp.status_code >= 400:
            raise ProviderError(f"Ollama returned {resp.status_code}: {resp.text[:300]}")

        try:
            return resp.json()["message"]["content"]
        except (KeyError, ValueError) as e:
            raise ProviderError(f"unexpected Ollama response shape: {resp.text[:300]}") from e
