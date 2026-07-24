"""NVIDIA NIM provider, OpenAI-compatible chat completions API."""
import httpx

from callback_ai.config import settings
from callback_ai.llm.client import AuthError, ProviderError, RateLimitedError


class NimProvider:
    def __init__(self):
        self.base_url = settings.nim_base_url.rstrip("/")
        self.model = settings.nim_model
        self.api_key = settings.nim_api_key

    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        if not self.api_key:
            raise AuthError(
                "NIM_API_KEY is not set. Copy .env.example to .env and add a key from "
                "build.nvidia.com, or set CALLBACK_AI_PROVIDER=mock to run the demo without a key."
            )

        body = {"model": self.model, "messages": messages, "temperature": temperature}
        if json_schema is not None:
            body["response_format"] = {"type": "json_schema", "json_schema": json_schema}

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=body,
                timeout=settings.request_timeout_s,
            )
        except httpx.TimeoutException as e:
            raise ProviderError(f"NIM request timed out after {settings.request_timeout_s}s") from e
        except httpx.HTTPError as e:
            raise ProviderError(f"could not reach NIM at {self.base_url}: {e}") from e

        if resp.status_code == 429:
            raise RateLimitedError(resp.text)
        if resp.status_code in (401, 403):
            raise AuthError("NIM rejected the API key (401/403). Check NIM_API_KEY in your .env.")
        if resp.status_code == 404:
            raise ProviderError(
                f"NIM has no model {self.model!r} (404). Set NIM_MODEL to a model id listed at build.nvidia.com."
            )
        if resp.status_code >= 400:
            raise ProviderError(f"NIM returned {resp.status_code}: {resp.text[:300]}")

        try:
            return resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as e:
            raise ProviderError(f"unexpected NIM response shape: {resp.text[:300]}") from e
