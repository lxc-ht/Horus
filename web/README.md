# Weboberfläche

Alle Befehle aus dem Repo-Root, einmal vorher `uv sync` (siehe README im Root).

Mit echtem Kern:

    uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000

Mit Attrappe:

    HARNESS_FAKE=1 uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000

Danach http://127.0.0.1:8000 öffnen. Das erste Analysieren lädt das Modell und dauert länger, also vor der Demo einmal auslösen.
