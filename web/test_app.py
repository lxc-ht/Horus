"""Prüft die Freigabe-Regel und den Abbruch ohne Kern. Start aus dem Repo-Root: python -m web.test_app"""
import importlib.util
import os
import subprocess
import sys

os.environ["HARNESS_FAKE"] = "1"

from web import app as server  # noqa: E402
from web import fake_core as core  # noqa: E402

TEXT = "Erika Musterfrau (erika@example.org) schreibt an Nordlicht Bau."


def rejected(fn, *args) -> dict:
    try:
        fn(*args)
    except server.CoreError as e:
        return e.payload
    raise AssertionError("Eine Ablehnung wurde erwartet")


def main() -> None:
    result = server.analyze(server.AnalyzeBody(text=TEXT))
    sid = result["session_id"]
    session = server.SessionBody(session_id=sid)
    assert "Erika" not in result["masked_text"]
    assert [r["placeholder"] for r in result["replacements"]] == ["[PERSON_1]", "[EMAIL_1]"]
    for r in result["replacements"]:
        assert result["masked_text"][r["start"]:r["end"]] == r["placeholder"]

    # Ohne Freigabe kein Versand.
    assert "error" in rejected(server.send, session)

    # Gesendet wird nur das gespeicherte Release.
    sent = []
    core.send = lambda rel: sent.append(rel) or "ok"
    released = server.release(session)
    assert server.send(session) == {"answer": "ok"}
    assert sent[0].text == released["text"]

    # Jede Änderung verwirft die Freigabe, auch eine fehlgeschlagene.
    server.mask_add(server.AddBody(session_id=sid, term="Nordlicht Bau", typ="FIRMA"))
    assert "error" in rejected(server.send, session)
    server.release(session)
    server.mask_remove(server.RemoveBody(session_id=sid, placeholder="[FIRMA_1]"))
    assert "error" in rejected(server.send, session)
    server.release(session)
    rejected(server.mask_remove, server.RemoveBody(session_id=sid, placeholder="[PERSON_99]"))
    assert "error" in rejected(server.send, session)

    # Scheitert eine neue Freigabe, bleibt keine alte gültig.
    server.release(session)

    def leak(_):
        raise core.LeakError("Leck gefunden.")

    original_release = core.release
    core.release = leak
    assert rejected(server.release, session) == {"error": "Leck gefunden."}
    core.release = original_release
    assert "error" in rejected(server.send, session)

    # NoApiKeyError schaltet in den Kopier-Modus.
    def no_key(_):
        raise core.NoApiKeyError("Kein Key.")

    core.send = no_key
    server.release(session)
    assert rejected(server.send, session) == {"error": "Kein Key.", "copy_mode": True}

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
