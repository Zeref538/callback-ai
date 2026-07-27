"""Production entrypoint: `callback-ai-serve`, or `python -m callback_ai.server`.

Binds 0.0.0.0 and honours $PORT so a PaaS (Render/Railway/Fly/etc.) can run it
as-is. Local dev can keep using `uvicorn ... --reload`; this is the deploy path.
"""
import os

import uvicorn


def main() -> None:
    # Default to a single worker on purpose: sessions live in an in-process dict
    # (api/routes/session.py), so a second worker can't see a session the first
    # one started -- the answer request would 404. Only raise WEB_CONCURRENCY
    # once sessions move to shared storage.
    uvicorn.run(
        "callback_ai.api.app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("WEB_CONCURRENCY", "1")),
    )


if __name__ == "__main__":
    main()
