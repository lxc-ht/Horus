"""Prüft die Freigabe-Regel und den Abbruch ohne Kern. Start aus dem Repo-Root: python -m web.test_app"""
import asyncio
import importlib.util
import io
import json
import os
import zipfile
from email.message import EmailMessage
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


W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def docx(body: str, **parts: str) -> bytes:
    # Kleinste Word-Datei von Hand: ZIP mit word/document.xml, weitere Teile wie header1 optional.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", f"<w:document {W_NS}><w:body>{body}</w:body></w:document>")
        for name, xml in parts.items():
            archive.writestr(f"word/{name}.xml", f"<w:hdr {W_NS}>{xml}</w:hdr>")
    return buffer.getvalue()


def para(*runs: str) -> str:
    return "<w:p>" + "".join(f"<w:r>{r}</w:r>" for r in runs) + "</w:p>"


def check_docx() -> None:
    body = (
        para("<w:t>Erika Musterfrau</w:t>", "<w:t xml:space=\"preserve\"> wohnt in Lüneburg.</w:t>")
        + para("<w:t>Az.</w:t><w:tab/><w:t>123/26</w:t>")
        + "<w:p><w:del><w:r><w:delText>Gestrichen</w:delText></w:r></w:del><w:r><w:t>Max Mustermann</w:t></w:r></w:p>"
        + "<w:tbl><w:tr><w:tc>" + para("<w:t>Zelle eins</w:t>") + "</w:tc></w:tr></w:tbl>"
        + para("<w:t>Außen</w:t>", "<w:pict><w:txbxContent>" + para("<w:t>Im Textfeld</w:t>") + "</w:txbxContent></w:pict>")
    )
    status, data = post("/api/docx", docx(body, header1=para("<w:t>Kanzlei Sommerfeld</w:t>"), header2=para("<w:t>Kanzlei Sommerfeld</w:t>")))
    assert status == 200, data
    assert data["text"] == (
        "Kanzlei Sommerfeld\n\n"
        "Erika Musterfrau wohnt in Lüneburg.\nAz.\t123/26\nMax Mustermann\nZelle eins\nIm Textfeld\nAußen"
    ), data["text"]

    # Zellen einer Tabellenzeile bleiben in einer Zeile, getrennt durch Tabulator.
    cell = lambda *texts: "<w:tc>" + "".join(para(f"<w:t>{t}</w:t>") for t in texts) + "</w:tc>"
    table = "<w:tbl><w:tr>" + cell("IBAN") + cell("DE00 1234", "5678") + "</w:tr><w:tr>" + cell("Name") + cell("Erika Musterfrau") + "</w:tr></w:tbl>"
    status, data = post("/api/docx", docx(table))
    assert status == 200 and data["text"] == "IBAN\tDE00 1234 5678\nName\tErika Musterfrau", data

    assert post("/api/docx", docx(para("<w:t> </w:t>"))) == (422, {"error": server.DOCX_EMPTY})
    assert post("/api/docx", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"0" * 100) == (422, {"error": server.DOCX_OLD})
    assert post("/api/docx", b"Das ist keine Word-Datei.") == (422, {"error": server.DOCX_INVALID})
    other_zip = io.BytesIO()
    with zipfile.ZipFile(other_zip, "w") as archive:
        archive.writestr("notiz.txt", "Erika Musterfrau")
    assert post("/api/docx", other_zip.getvalue()) == (422, {"error": server.DOCX_INVALID})
    broken = docx("<w:p><w:r><w:t>offen")
    assert post("/api/docx", broken) == (422, {"error": server.DOCX_INVALID})
    # Externe Entitäten werden nicht aufgelöst, die Datei gilt als unlesbar.
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", '<!DOCTYPE d [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
                         f'<w:document {W_NS}><w:body><w:p><w:r><w:t>&e;</w:t></w:r></w:p></w:body></w:document>')
    status, data = post("/api/docx", buffer.getvalue())
    assert status == 422 and "root" not in json.dumps(data)
    assert post("/api/docx", b"PK" + b"0" * server.PDF_MAX_BYTES) == (413, {"error": server.FILE_TOO_LARGE})
    assert post("/api/docx", docx(para("<w:t>Erika Musterfrau</w:t>")), host="angreifer.example")[0] == 403


def eml(html: bool = False) -> bytes:
    message = EmailMessage()
    message["From"] = "Erika Musterfrau <erika@example.org>"
    message["To"] = "Kanzlei Sommerfeld <post@kanzlei.example>"
    message["Subject"] = "Kündigung durch Nordlicht Bau"
    message["Date"] = "Thu, 05 Nov 2026 10:00:00 +0100"
    message.set_content("Guten Tag,\nmir wurde am 14.03.2026 gekündigt.\n")
    if html:
        message.add_alternative(
            "<html><head><style>p{}</style></head><body><p>Guten Tag,</p><p>mir wurde <b>gekündigt</b>.</p>"
            "<script>alert(1)</script></body></html>", subtype="html")
        message.make_mixed()
        message.add_attachment(b"%PDF-1.4", maintype="application", subtype="pdf", filename="anhang.pdf")
    return message.as_bytes()


def check_eml() -> None:
    status, data = post("/api/eml", eml())
    assert status == 200, data
    assert data["text"].startswith("Von: Erika Musterfrau <erika@example.org>\nAn: Kanzlei Sommerfeld <post@kanzlei.example>\n")
    assert "Betreff: Kündigung durch Nordlicht Bau" in data["text"]
    assert data["text"].endswith("\n\nGuten Tag,\nmir wurde am 14.03.2026 gekündigt.")

    # Bei Text und HTML gewinnt der Text, Anhänge bleiben draußen.
    status, data = post("/api/eml", eml(html=True))
    assert status == 200 and "14.03.2026" in data["text"] and "PDF" not in data["text"]

    only_html = EmailMessage()
    only_html["From"] = "erika@example.org"
    only_html["Subject"] = "Nur HTML"
    only_html.set_content("<p>Guten Tag,</p><p>mir wurde <b>gek&uuml;ndigt</b>.</p><script>alert(1)</script>", subtype="html")
    status, data = post("/api/eml", only_html.as_bytes())
    assert status == 200, data
    assert data["text"].endswith("\n\nGuten Tag,\n\nmir wurde gekündigt.") and "alert" not in data["text"], data["text"]

    assert post("/api/eml", b"Das ist nur ein Text, keine E-Mail.") == (422, {"error": server.EML_INVALID})
    assert post("/api/eml", b"") == (422, {"error": server.EML_INVALID})
    assert post("/api/eml", b"0" * (server.PDF_MAX_BYTES + 1)) == (413, {"error": server.FILE_TOO_LARGE})
    assert post("/api/eml", eml(), host="angreifer.example")[0] == 403


def main() -> None:
    check_pdf()
    check_docx()
    check_eml()

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

    # Zu lange Texte lehnt der Server ab, bevor der Kern sie sieht.
    too_long = rejected(server.analyze, server.AnalyzeBody(text="a" * (server.TEXT_MAX_CHARS + 1)))
    assert "100.001 Zeichen" in too_long["error"]
    assert server.analyze(server.AnalyzeBody(text="a" * server.TEXT_MAX_CHARS))["masked_text"]

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
