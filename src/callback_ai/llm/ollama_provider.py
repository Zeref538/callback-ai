"""Local Ollama fallback, used when NIM is rate-limited (NFR-3)."""
import httpx

from callback_ai.config import settings


class OllamaProvider:
    def __init__(self):
        self.host = settings.ollama_host
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

        resp = httpx.post(f"{self.host}/api/chat", json=body, timeout=settings.request_timeout_s)
        resp.raise_for_status()
        return resp.json()["message"]["content"]
