"""Lokale Weboberfläche. Start aus dem Repo-Root: uvicorn web.app:app --host 127.0.0.1 --port 8000"""
import io
import logging
import os
import warnings
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from pypdf import PdfReader

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

# pypdf meldet kaputte Stellen über logging. Ohne eigenen Handler schreibt Python das ins
# Serverlog, und solche Meldungen können Bruchstücke der Datei enthalten.
logging.getLogger("pypdf").addHandler(logging.NullHandler())
logging.getLogger("pypdf").propagate = False

PDF_MAX_BYTES = 20 * 1024 * 1024
# Weniger auslesbarer Text als das (ohne Leerraum) heißt fast immer: eingescannte Seiten.
PDF_MIN_CHARS = 20
PDF_TOO_LARGE = "Die PDF ist größer als 20 MB."
PDF_SCAN = "In dieser PDF steht kein auslesbarer Text, vermutlich ist sie ein Scan. Scans kann LP7 noch nicht lesen."
PDF_PASSWORD = "Diese PDF ist mit einem Passwort geschützt. Entferne den Schutz und lade sie erneut."
PDF_INVALID = "Das ist keine lesbare PDF-Datei."

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


class PdfError(Exception):
    pass


def pdf_text(data: bytes) -> tuple[str, int]:
    # Nur im Speicher lesen: Die PDF darf nirgends auf der Platte landen.
    try:
        with warnings.catch_warnings():
            # Auch Warnungen von pypdf könnten Inhalt nennen und gehören nicht ins Log.
            warnings.simplefilter("ignore")
            return _read_pdf(data)
    except PdfError:
        raise
    except Exception:
        # Bewusst ohne Ursache: Die Meldung von pypdf kann Inhalt der Datei enthalten.
        raise PdfError(PDF_INVALID) from None


def _read_pdf(data: bytes) -> tuple[str, int]:
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        # Viele „geschützte“ PDFs sperren nur Rechte und öffnen mit leerem Passwort.
        try:
            opened = reader.decrypt("")
        except Exception:
            opened = 0
        if not opened:
            raise PdfError(PDF_PASSWORD)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    text = "\n\n".join(pages)
    if len("".join(text.split())) < PDF_MIN_CHARS:
        raise PdfError(PDF_SCAN)
    return text, len(pages)


@app.post("/api/pdf")
async def load_pdf(request: Request) -> JSONResponse:
    # Rohe Bytes statt Formular-Upload, so braucht es kein python-multipart.
    # Gezählt wird beim Lesen, denn Content-Length kann fehlen oder falsch sein.
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > PDF_MAX_BYTES:
            return JSONResponse({"error": PDF_TOO_LARGE}, status_code=413)
        chunks.append(chunk)
    try:
        text, pages = pdf_text(b"".join(chunks))
    except PdfError as e:
        return JSONResponse({"error": str(e)}, status_code=422)
    except Exception:
        # Alles fangen, damit kein Traceback mit Inhalt der PDF im Serverlog landet.
        return JSONResponse({"error": PDF_INVALID}, status_code=422)
    return JSONResponse({"text": text, "pages": pages})
