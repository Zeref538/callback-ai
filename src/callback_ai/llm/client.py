"""Provider-agnostic chat interface. Both providers implement this shape."""
from typing import Protocol


class RateLimitedError(Exception):
    """Raised by a provider on 429 so the router can fall back."""


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
