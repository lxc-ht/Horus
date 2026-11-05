"""Prüft die Freigabe-Regel und den Abbruch ohne Kern. Start aus dem Repo-Root: python -m web.test_app"""
import asyncio
import importlib.util
import io
import json
import os
import subprocess
import sys

os.environ["HARNESS_FAKE"] = "1"

from web import app as server  # noqa: E402
from web import fake_core as core  # noqa: E402
from pypdf import PdfWriter  # noqa: E402

TEXT = "Erika Musterfrau (erika@example.org) schreibt an Nordlicht Bau."


def rejected(fn, *args) -> dict:
    try:
        fn(*args)
    except server.CoreError as e:
        return e.payload
    raise AssertionError("Eine Ablehnung wurde erwartet")


def text_pdf(*lines: str) -> bytes:
    # Kleinste Text-PDF von Hand: eine Seite, Helvetica, ein Textobjekt. So liegt keine PDF im Repo.
    ops = "BT /F1 12 Tf 72 720 Td 14 TL " + " ".join(f"({line}) '" for line in lines) + " ET"
    stream = ops.encode("cp1252")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


def blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def post(path: str, body: bytes, host: str = "127.0.0.1:8000") -> tuple[int, dict]:
    # Direkt über ASGI, ohne Testclient-Abhängigkeit, und mit genau dem Host, den local_only prüft.
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "POST",
        "scheme": "http", "path": path, "raw_path": path.encode(), "root_path": "", "query_string": b"",
        "headers": [(b"host", host.encode()), (b"content-type", b"application/pdf")],
        "client": ("127.0.0.1", 50000), "server": ("127.0.0.1", 8000),
    }
    # In Stücken senden, wie ein Browser es tun kann.
    pieces = [body[i:i + 1024 * 1024] for i in range(0, len(body), 1024 * 1024)] or [b""]
    incoming = [{"type": "http.request", "body": p, "more_body": i < len(pieces) - 1} for i, p in enumerate(pieces)]
    sent = []

    async def receive():
        return incoming.pop(0) if incoming else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    asyncio.run(server.app(scope, receive, send))
    status = next(m["status"] for m in sent if m["type"] == "http.response.start")
    payload = b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    return status, json.loads(payload)


def check_pdf() -> None:
    status, data = post("/api/pdf", text_pdf("Erika Musterfrau wohnt in L\xfcneburg.", "Akte 123/26"))
    assert status == 200, data
    assert data["pages"] == 1
    assert "Erika Musterfrau wohnt in Lüneburg." in data["text"]
    assert data["text"] == data["text"].strip()

    # Mehrere Seiten werden mit einer Leerzeile getrennt.
    two = PdfWriter()
    for _ in range(2):
        two.append(io.BytesIO(text_pdf("Max Mustermann schreibt an Nordlicht Bau.")))
    buffer = io.BytesIO()
    two.write(buffer)
    status, data = post("/api/pdf", buffer.getvalue())
    assert status == 200 and data["pages"] == 2
    assert data["text"].count("Max Mustermann") == 2 and "\n\n" in data["text"]

    assert post("/api/pdf", blank_pdf()) == (422, {"error": server.PDF_SCAN})
    assert post("/api/pdf", b"Das ist nur ein Text, keine PDF.") == (422, {"error": server.PDF_INVALID})
    assert post("/api/pdf", b"%PDF-1.4\n kaputt") == (422, {"error": server.PDF_INVALID})
    assert post("/api/pdf", b"") == (422, {"error": server.PDF_INVALID})

    # Echtes Passwort: Das leere Passwort reicht nicht.
    locked = PdfWriter(clone_from=io.BytesIO(text_pdf("Erika Musterfrau wohnt in Lueneburg.")))
    locked.encrypt(user_password="geheim", owner_password="geheim")
    buffer = io.BytesIO()
    locked.write(buffer)
    assert post("/api/pdf", buffer.getvalue()) == (422, {"error": server.PDF_PASSWORD})

    # Nur Rechte gesperrt, leeres Benutzerpasswort: wird gelesen.
    rights = PdfWriter(clone_from=io.BytesIO(text_pdf("Erika Musterfrau wohnt in Lueneburg.")))
    rights.encrypt(user_password="", owner_password="eigentuemer")
    buffer = io.BytesIO()
    rights.write(buffer)
    status, data = post("/api/pdf", buffer.getvalue())
    assert status == 200 and "Erika Musterfrau" in data["text"]

    too_large = b"%PDF-1.4\n" + b"0" * server.PDF_MAX_BYTES
    assert post("/api/pdf", too_large) == (413, {"error": server.PDF_TOO_LARGE})
    # Genau 20 MB sind noch erlaubt und scheitern erst beim Lesen.
    assert post("/api/pdf", b"0" * server.PDF_MAX_BYTES)[0] == 422

    # Auch der neue Endpunkt ist nur lokal erreichbar.
    status, data = post("/api/pdf", text_pdf("Erika Musterfrau wohnt in Lueneburg."), host="angreifer.example")
    assert status == 403 and "text" not in data


def main() -> None:
    check_pdf()

    result = server.analyze(server.AnalyzeBody(text=TEXT))
    sid = result["session_id"]
    session = server.SessionBody(session_id=sid)
    assert "Erika" not in result["masked_text"]
    assert [r["placeholder"] for r in result["replacements"]] == ["[PERSON_1]", "[EMAIL_1]"]
    for r in result["replacements"]:
        assert result["masked_text"][r["start"]:r["end"]] == r["placeholder"]

    # Die Oberfläche kann nichts senden: Weitergeben kann nur der Mensch durch Kopieren.
    assert not hasattr(server, "send")
    assert "/api/send" not in [route.path for route in server.app.routes]

    # Freigegeben wird genau der aktuelle maskierte Text.
    assert server.release(session)["text"] == result["masked_text"]

    # Scheitert die Freigabe, kommt die Meldung unverändert an.
    def leak(_):
        raise core.LeakError("Leck gefunden.")

    original_release = core.release
    core.release = leak
    assert rejected(server.release, session) == {"error": "Leck gefunden."}
    core.release = original_release

    # Unsichere Stellen kommen mit Position im maskierten Text an.
    marked = server.analyze(server.AnalyzeBody(text="Bitte an Nordlicht Bau schreiben."))
    hint = marked["uncertain"][0]
    assert marked["masked_text"][hint["start"]:hint["end"]] == "Nordlicht"

    # Rückübersetzung meldet Unbekanntes und Fehlendes.
    restored = server.restore(server.RestoreBody(session_id=sid, answer="[PERSON_1] und [PERSON_9]"))
    assert restored["text"] == "Erika Musterfrau und [PERSON_9]"
    assert restored["unknown"] == ["[PERSON_9]"]
    assert restored["missing"] == ["[EMAIL_1]"]

    # Ohne HARNESS_FAKE und ohne Kern bricht der Start ab, statt die Attrappe zu nehmen.
    env = {k: v for k, v in os.environ.items() if k != "HARNESS_FAKE"}
    start = subprocess.run([sys.executable, "-c", "import web.app"], env=env, capture_output=True, text=True)
    if importlib.util.find_spec("harness") is None:
        assert start.returncode != 0 and "HARNESS_FAKE=1" in start.stderr

    print("Alle Prüfungen bestanden.")


if __name__ == "__main__":
    main()
