"""FR-8: append-only JSONL transcript + decision log. One line per event so
it's replayable (NFR-5) and diffable."""
import json
import time
import uuid
from pathlib import Path

SESSIONS_DIR = Path("data/sessions")


class SessionLogger:
    def __init__(self, session_id: str | None = None, sessions_dir: Path = SESSIONS_DIR):
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.path = sessions_dir / f"{self.session_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._events: list[dict] = []

    def log(self, event_type: str, **fields) -> None:
        event = {"type": event_type, "timestamp": time.time(), **fields}
        self._events.append(event)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")

    @property
    def events(self) -> list[dict]:
        return list(self._events)


def read_session(session_id: str, sessions_dir: Path = SESSIONS_DIR) -> list[dict]:
    path = sessions_dir / f"{session_id}.jsonl"
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
