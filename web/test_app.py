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
