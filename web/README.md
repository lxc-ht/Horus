# Weboberfläche

Alle Befehle aus dem Repo-Root:

    pip install -r web/requirements.txt

Mit Attrappe:

    HARNESS_FAKE=1 uvicorn web.app:app --host 127.0.0.1 --port 8000

Mit echtem Kern (Paket `harness` muss installiert sein):

    uvicorn web.app:app --host 127.0.0.1 --port 8000

Danach http://127.0.0.1:8000 öffnen.
