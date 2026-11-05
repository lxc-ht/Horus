"""Lokale Weboberfläche. Start aus dem Repo-Root: uvicorn web.app:app --host 127.0.0.1 --port 8000"""
import os
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

FAKE = os.environ.get("HARNESS_FAKE") == "1"

if FAKE:
    from web import fake_core as core
else:
    try:
        from harness import api as core
    except ImportError as e:
        # Kein stilles Zurückfallen: Die Demo darf nie unbemerkt gegen die Attrappe laufen.
        raise SystemExit(
            f"Der Kern (harness.api) lässt sich nicht laden: {e}\n"
            "Installiere den Kern oder starte bewusst die Attrappe mit HARNESS_FAKE=1."
        )

INDEX = Path(__file__).parent / "static" / "index.html"

app = FastAPI()


class AnalyzeBody(BaseModel):
    text: str


class AddBody(BaseModel):
    session_id: str
    term: str
    typ: str


class RemoveBody(BaseModel):
    session_id: str
    placeholder: str


class SessionBody(BaseModel):
    session_id: str


class RestoreBody(BaseModel):
    session_id: str
    answer: str


class CoreError(Exception):
    def __init__(self, payload: dict):
        self.payload = payload


@app.exception_handler(CoreError)
def core_error(_: Request, e: CoreError) -> JSONResponse:
    return JSONResponse(e.payload, status_code=409)


@app.middleware("http")
async def local_only(request: Request, call_next):
    # Host-Prüfung gegen DNS-Rebinding: Sonst könnte eine fremde Webseite die Originaldaten auslesen.
    host = request.headers.get("host", "").split(":")[0]
    client = request.client.host if request.client else ""
    if client != "127.0.0.1" or host not in ("127.0.0.1", "localhost"):
        return JSONResponse({"error": "Diese Oberfläche ist nur lokal erreichbar."}, status_code=403)
    return await call_next(request)


def call(fn, *args):
    # Alles fangen, damit kein Traceback mit Originaldaten im Serverlog landet.
    try:
        return fn(*args)
    except Exception as e:
        raise CoreError({"error": str(e)}) from None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(INDEX, headers={"Cache-Control": "no-store"})


@app.get("/api/status")
def status() -> dict:
    return {"fake": FAKE}


@app.post("/api/analyze")
def analyze(body: AnalyzeBody) -> dict:
    return asdict(call(core.analyze, body.text))


@app.post("/api/mask/add")
def mask_add(body: AddBody) -> dict:
    return asdict(call(core.add_manual, body.session_id, body.term, body.typ))


@app.post("/api/mask/remove")
def mask_remove(body: RemoveBody) -> dict:
    return asdict(call(core.remove, body.session_id, body.placeholder))


@app.post("/api/release")
def release(body: SessionBody) -> dict:
    rel = call(core.release, body.session_id)
    return {"sha256": rel.sha256, "text": rel.text}


@app.post("/api/restore")
def restore(body: RestoreBody) -> dict:
    return asdict(call(core.restore, body.session_id, body.answer))
