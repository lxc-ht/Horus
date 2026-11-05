# Weboberfläche

Alle Befehle aus dem Repo-Root, einmal vorher `uv sync` (siehe README im Root).

Mit echtem Kern:

    uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000

Mit Attrappe:

    HARNESS_FAKE=1 uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000

Danach http://127.0.0.1:8000 öffnen. Das erste Analysieren lädt das Modell und dauert länger, also vor der Demo einmal auslösen.

## UI prüfen

Die Oberfläche lädt keine externen Fonts, Skripte oder Bilder. Die drei Arbeitsschritte passen sich an Desktop und Handy an. Die Freigabe bleibt vor Versand oder Kopieren zwingend.

Server bewusst mit der Attrappe starten:

    HARNESS_FAKE=1 uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000

In einem zweiten Terminal die Browserprüfung ausführen. Playwright ist nur für diese Prüfung nötig, nicht für die App:

    uv run --no-project --with playwright playwright install chromium --only-shell
    uv run --no-project --with playwright python -m web.test_ui

Die Prüfung nutzt erfundene Daten. Der API-Versand wird im Browser simuliert, es geht keine Anfrage an Claude. Sie prüft Sperrzustände, Kopieren, Rückübersetzung, Freigabeverlust nach einer Änderung und vier Bildschirmbreiten. Für einen anderen lokalen Port kann die URL als Argument übergeben werden.

## UI Kit

Das [vollständige UI Kit](ui-kit/README.md) liegt direkt in diesem Repository unter `web/ui-kit/`: 18 SVG Icons, drei Looks, Komponentendemos, interaktive Beispieldurchläufe, Banner und Dashboard Vorschauen. Für den gezeigten farbigen Entwurf oben **Lime Soda** auswählen.

Aus dem Repository starten:

    python3 -m http.server 8013 --bind 127.0.0.1 --directory web/ui-kit

Danach [UI Kit öffnen](http://127.0.0.1:8013). Es läuft unabhängig vom Kern und benötigt keinen API Schlüssel. Einstieg und Bearbeitungshinweise für die gemeinsame Weiterentwicklung stehen in der [Kit Anleitung](ui-kit/README.md#gemeinsam-weiterarbeiten).
