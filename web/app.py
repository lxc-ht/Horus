"""Lokale Weboberfläche. Start aus dem Repo-Root: uvicorn web.app:app --host 127.0.0.1 --port 8000"""
import io
import re
import zipfile
import logging
import os
import warnings
from dataclasses import asdict
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

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
FILE_TOO_LARGE = "Die Datei ist größer als 20 MB."
DOCX_INVALID = "Das ist keine lesbare Word-Datei (.docx)."
DOCX_OLD = "Diese Word-Datei ist im alten Format (.doc) oder mit einem Passwort geschützt. Speichere sie in Word ohne Passwort als .docx und lade sie erneut."
DOCX_EMPTY = "In dieser Word-Datei steht kein Text."
EML_INVALID = "Das ist keine lesbare E-Mail-Datei (.eml)."
# Entpackt höchstens so viel. Eine kleine ZIP-Datei kann sonst Gigabytes an XML enthalten.
DOCX_MAX_XML = 50 * 1024 * 1024

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


class FileError(Exception):
    def __init__(self, message: str, status: int = 422):
        super().__init__(message)
        self.status = status


async def read_upload(request: Request, too_large: str) -> bytes:
    # Rohe Bytes statt Formular-Upload, so braucht es kein python-multipart.
    # Gezählt wird beim Lesen, denn Content-Length kann fehlen oder falsch sein.
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > PDF_MAX_BYTES:
            raise FileError(too_large, 413)
        chunks.append(chunk)
    return b"".join(chunks)


async def load_file(request: Request, too_large: str, invalid: str, read) -> JSONResponse:
    # Gemeinsamer Ablauf für alle Dateitypen: im Speicher lesen, nur Text zurückgeben.
    try:
        data = await read_upload(request, too_large)
        return JSONResponse(read(data))
    except (FileError, PdfError) as e:
        return JSONResponse({"error": str(e)}, status_code=getattr(e, "status", 422))
    except Exception:
        # Alles fangen, damit kein Traceback mit Inhalt der Datei im Serverlog landet.
        return JSONResponse({"error": invalid}, status_code=422)


def pdf_result(data: bytes) -> dict:
    text, pages = pdf_text(data)
    return {"text": text, "pages": pages}


@app.post("/api/pdf")
async def load_pdf(request: Request) -> JSONResponse:
    return await load_file(request, PDF_TOO_LARGE, PDF_INVALID, pdf_result)


W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
# Kopfzeilen zuerst, wie sie im Brief oben stehen, dann Text, Fußnoten, Fußzeilen.
DOCX_PARTS = re.compile(r"word/(header\d*|document|footnotes|endnotes|footer\d*)\.xml")
DOCX_ORDER = {"header": 0, "document": 1, "footnotes": 2, "endnotes": 3, "footer": 4}


def docx_paragraphs(root) -> list[str]:
    # Absätze in Textfeldern stecken in einem äußeren Absatz. Sie werden eigene Zeilen,
    # sonst stünde ihr Text doppelt da.
    # Eine Tabellenzeile wird eine Zeile, die Zellen durch Tabulator getrennt. So bleibt „IBAN“ neben dem Wert.
    paragraphs = []

    def walk(element, buffer, out):
        for child in element:
            tag = child.tag
            if tag == W + "p":
                inner = []
                walk(child, inner, out)
                out.append("".join(inner))
            elif tag == W + "tr":
                cells = []
                for cell in child:
                    if cell.tag != W + "tc":
                        continue
                    cell_lines = []
                    walk(cell, [], cell_lines)
                    cells.append(" ".join(line.strip() for line in cell_lines if line.strip()))
                out.append("\t".join(cells))
            elif tag == W + "t":
                buffer.append(child.text or "")
            elif tag == W + "tab":
                buffer.append("\t")
            elif tag in (W + "br", W + "cr"):
                buffer.append("\n")
            elif tag == W + "del":
                # Gelöschter Text aus „Änderungen nachverfolgen“ steht nicht mehr im Dokument.
                continue
            else:
                walk(child, buffer, out)

    walk(root, [], paragraphs)
    return paragraphs


def docx_text(data: bytes) -> dict:
    if data[:4] == b"\xd0\xcf\x11\xe0":
        # Altes .doc und verschlüsseltes .docx haben beide dieses Containerformat.
        raise FileError(DOCX_OLD)
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        names = [n for n in archive.namelist() if DOCX_PARTS.fullmatch(n)]
        if "word/document.xml" not in names:
            raise FileError(DOCX_INVALID)
        names.sort(key=lambda n: (DOCX_ORDER[re.sub(r"\d", "", n[5:-4])], n))
        sections, seen = [], set()
        for name in names:
            with archive.open(name) as part:
                xml = part.read(DOCX_MAX_XML + 1)
            if len(xml) > DOCX_MAX_XML:
                raise FileError(DOCX_INVALID)
            # ElementTree lädt keine externen Entitäten, expat begrenzt verschachtelte.
            text = "\n".join(docx_paragraphs(ElementTree.fromstring(xml))).strip()
            # Gleiche Kopfzeile in mehreren Abschnitten nur einmal.
            if text and text not in seen:
                seen.add(text)
                sections.append(text)
    except FileError:
        raise
    except Exception:
        raise FileError(DOCX_INVALID) from None
    text = "\n\n".join(sections)
    if not text.strip():
        raise FileError(DOCX_EMPTY)
    return {"text": text}


@app.post("/api/docx")
async def load_docx(request: Request) -> JSONResponse:
    return await load_file(request, FILE_TOO_LARGE, DOCX_INVALID, docx_text)


class HtmlText(HTMLParser):
    # HTML-Mails nur als Text: Bilder, Skripte und Links werden nie geladen.
    BLOCKS = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "table"}

    def __init__(self):
        super().__init__()
        self.parts, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head"):
            self.skip += 1
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

    def text(self) -> str:
        lines = [" ".join(line.split()) for line in "".join(self.parts).splitlines()]
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


EML_HEADERS = [("From", "Von"), ("To", "An"), ("Cc", "Cc"), ("Date", "Datum"), ("Subject", "Betreff")]


def eml_text(data: bytes) -> dict:
    try:
        message = BytesParser(policy=policy.default).parsebytes(data)
        # Kopfzeilen gehören dazu: Absender und Empfänger sind oft die sensibelsten Angaben.
        head = [f"{label}: {message[key]}" for key, label in EML_HEADERS if message[key]]
        body = message.get_body(preferencelist=("plain", "html"))
        text = ""
        if body is not None:
            content = body.get_content()
            if body.get_content_subtype() == "html":
                parser = HtmlText()
                parser.feed(content)
                text = parser.text()
            else:
                text = content.strip()
    except Exception:
        raise FileError(EML_INVALID) from None
    # Ohne Absender, Empfänger, Betreff und Text ist es keine E-Mail, auch wenn der Parser alles annimmt.
    if not head or not (text or message["Subject"]):
        raise FileError(EML_INVALID)
    return {"text": "\n".join(head) + ("\n\n" + text if text else "")}


@app.post("/api/eml")
async def load_eml(request: Request) -> JSONResponse:
    return await load_file(request, FILE_TOO_LARGE, EML_INVALID, eml_text)
