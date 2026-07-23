"""Picks NIM vs Ollama per call, falling back to Ollama on rate-limit (NFR-3)."""
from callback_ai.llm.client import ChatProvider, RateLimitedError
from callback_ai.llm.nim_provider import NimProvider
from callback_ai.llm.ollama_provider import OllamaProvider


class Router:
    def __init__(self, primary: ChatProvider | None = None, fallback: ChatProvider | None = None):
        self.primary = primary or NimProvider()
        self.fallback = fallback or OllamaProvider()

    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        try:
            return self.primary.chat(messages, temperature=temperature, json_schema=json_schema)
        except RateLimitedError:
            return self.fallback.chat(messages, temperature=temperature, json_schema=json_schema)
