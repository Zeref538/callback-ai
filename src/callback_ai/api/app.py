from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from callback_ai.api.routes.session import router as session_router
from callback_ai.config import settings
from callback_ai.llm.client import AuthError, ProviderError
from callback_ai.llm.json_parse import MalformedModelJSON

app = FastAPI(title="callback-ai")


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
