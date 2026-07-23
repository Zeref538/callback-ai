import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class FakeChat:
    """Returns canned responses in order, one per .chat() call. Test double for ChatProvider."""

    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls = []

    def chat(self, messages, *, temperature: float = 0.0, json_schema=None) -> str:
        self.calls.append(messages)
        return self._responses.pop(0)
