from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from callback_ai.api.routes.session import router as session_router

app = FastAPI(title="callback-ai")
app.include_router(session_router, prefix="/api")

WEB_DIR = Path(__file__).parent.parent.parent.parent / "web"
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
