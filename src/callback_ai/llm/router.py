"""Picks a provider per call, falling back to Ollama on rate-limit (NFR-3)."""
from callback_ai.config import settings
from callback_ai.llm.client import ChatProvider, ProviderError, RateLimitedError


class Router:
    def __init__(self, primary: ChatProvider | None = None, fallback: ChatProvider | None = None):
        if primary is None or fallback is None:
            # Imported lazily so the mock provider works with no httpx config at all.
            from callback_ai.llm.nim_provider import NimProvider
            from callback_ai.llm.ollama_provider import OllamaProvider

            primary = primary or NimProvider()
            fallback = fallback or OllamaProvider()
        self.primary = primary
        self.fallback = fallback

    def chat(self, messages: list[dict], *, temperature: float = 0.0, json_schema: dict | None = None) -> str:
        try:
            return self.primary.chat(messages, temperature=temperature, json_schema=json_schema)
        except RateLimitedError as rate_limit:
            try:
                return self.fallback.chat(messages, temperature=temperature, json_schema=json_schema)
            except ProviderError as fallback_error:
                # Report both: "Ollama is down" alone hides why we were there.
                raise ProviderError(
                    f"NIM rate-limited and the local fallback failed. NIM: {rate_limit}. Fallback: {fallback_error}"
                ) from fallback_error


def build_chat() -> ChatProvider:
    """Single place the app asks for a provider, so CALLBACK_AI_PROVIDER=mock
    swaps in the offline demo model everywhere at once."""
    if settings.provider == "mock":
        from callback_ai.llm.mock_provider import MockProvider

        return MockProvider()
    return Router()
