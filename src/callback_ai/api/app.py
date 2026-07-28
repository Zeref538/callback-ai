import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from callback_ai.api.routes.session import router as session_router
from callback_ai.config import settings
from callback_ai.llm.client import AuthError, ProviderError
from callback_ai.llm.json_parse import MalformedModelJSON

app = FastAPI(title="callback-ai")

# ---- rate limiting ----
# In-process per-IP sliding window. The app is single-worker by design (sessions
# live in memory), so an in-process limiter is consistent -- no Redis needed. A
# full session is ~27 POSTs over ~10 min, so 90/min is generous for real use and
# only trips on abuse loops. ponytail: swap for a shared limiter if we ever scale
# past one worker.
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "90"))
_hits: dict[str, deque] = defaultdict(deque)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.method == "POST" and request.url.path.startswith("/api/"):
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        dq = _hits[ip]
        while dq and now - dq[0] > 60:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_PER_MIN:
            return JSONResponse(status_code=429, content={"detail": "Too many requests — give it a moment and try again."})
        dq.append(now)
        # Opportunistically drop idle IPs so the dict can't grow unbounded.
        if len(_hits) > 2000:
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 60]:
                _hits.pop(k, None)
    return await call_next(request)


@app.exception_handler(AuthError)
def _auth_error(request: Request, exc: AuthError) -> JSONResponse:
    # 502, not 401: the caller's request was fine, our upstream credential isn't.
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.exception_handler(ProviderError)
def _provider_error(request: Request, exc: ProviderError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": f"Model provider error: {exc}"})


@app.exception_handler(MalformedModelJSON)
def _bad_model_json(request: Request, exc: MalformedModelJSON) -> JSONResponse:
    return JSONResponse(
        status_code=502,
        content={"detail": "The model returned something we couldn't parse. Try again, or switch NIM_MODEL."},
    )


@app.get("/api/health")
def health() -> dict:
    """Deploy check: is the app up, and is it wired to a real model or the mock?"""
    return {
        "status": "ok",
        "provider": settings.provider,
        "model": settings.nim_model if settings.provider == "nim" else "mock",
        "api_key_configured": bool(settings.nim_api_key) or settings.provider == "mock",
    }


app.include_router(session_router, prefix="/api")

# Mounted last: StaticFiles at "/" swallows every unmatched path, so it must
# not shadow the API routes above.
WEB_DIR = Path(__file__).parent.parent.parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
