"""NVIDIA NIM provider, OpenAI-compatible chat completions API."""
import httpx

from callback_ai.config import settings
from callback_ai.llm.client import RateLimitedError


class NimProvider:
    def __init__(self):
        self.base_url = settings.nim_base_url
        self.model = settings.nim_model
        self.api_key = settings.nim_api_key

    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        resp = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=body,
            timeout=settings.request_timeout_s,
        )
        if resp.status_code == 429:
            raise RateLimitedError(resp.text)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
