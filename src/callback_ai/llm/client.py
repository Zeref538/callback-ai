"""Provider-agnostic chat interface. Both providers implement this shape."""
from typing import Protocol


class ProviderError(Exception):
    """Any provider failure that should surface to the user as a readable
    message rather than an httpx traceback."""


class RateLimitedError(ProviderError):
    """Raised by a provider on 429 so the router can fall back."""


class AuthError(ProviderError):
    """Missing/invalid API key -- falling back to a local model won't help."""


class ChatProvider(Protocol):
    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.0,
        json_schema: dict | None = None,
    ) -> str:
        """Return the model's raw text response (JSON string when json_schema is set)."""
        ...
