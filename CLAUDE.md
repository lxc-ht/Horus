# CLAUDE.md – Pseudonymisierungs-Harness

Lokaler Harness: erkennt sensible Angaben in einem Text, ersetzt sie durch Platzhalter wie `[PERSON_1]`, sendet nur nach ausdrücklicher Freigabe an Claude und setzt die Originaldaten danach lokal wieder ein.

## Die eine Regel, die alles andere überstimmt

Nichts verlässt den Rechner, was der Mensch nicht genau so freigegeben hat, und kein Originalwert aus der Zuordnung verlässt ihn überhaupt.

Daraus folgt, im Code verankert:

1. `send()` nimmt nur ein `Release` an. Vor dem Senden prüft es, ob der SHA-256 von `release.text` noch stimmt UND ob der aktuelle maskierte Text der Sitzung noch genau `release.text` ist. Ist eins davon falsch: `ReleaseMismatchError`, nichts wird gesendet. Jede Änderung nach der Freigabe macht sie ungültig.
2. `release()` lässt einen Leck-Check laufen. Steht ein Originalwert der Sitzung noch im Text (ohne Groß-/Kleinschreibung), wird blockiert (`LeakError`). Bei Personen werden zusätzlich die Namensteile ab 3 Zeichen geprüft – solche Treffer sind nur eine Warnung in `MaskResult.warnings`.
3. Zuordnungstabelle, Originaltexte und `.env` gehören nie in Git, nie in Logs und nie in den API-Aufruf. Logs enthalten nur Platzhalter, Typen und Zählungen.
4. Die Rückübersetzung rät nie. Was sie nicht eindeutig zuordnen kann, meldet sie.

## Aufteilung

- `web/` gehört dem Web-Teil (Branch `web`). Hier nichts anlegen oder ändern.
- `src/harness/api.py` ist der Vertrag. Die Weboberfläche importiert nur dieses Modul. Signaturen, Feldnamen und Ausnahmen nicht ändern; Ergänzungen nur zusätzlich und in `BACKLOG.md` unter „Vertrag erweitert“ eintragen.

## Konventionen

- Kommentare und Texte für Nutzer auf Deutsch, Bezeichner auf Englisch.
- Beispieldaten immer synthetisch – das Repo soll öffentlich werden können.
- API-Funktionen geben nichts auf stdout aus. Ausgabe macht nur die CLI.
- Ideen außerhalb des aktuellen Auftrags kommen nach `BACKLOG.md`.

## Umgebung, Tests, CLI

Python 3.12 mit uv (torch/GLiNER laufen auf 3.14 nicht verlässlich):

```bash
brew install uv      # falls nötig
uv sync              # legt .venv mit Python 3.12 an
uv run pytest        # ohne Netz, ohne GLiNER-Download
uv run pytest -m slow   # zusätzlich der GLiNER-Test (lädt das Modell)
uv run python -m harness run examples/kanzlei.txt
cat brief.txt | uv run python -m harness run    # Text über stdin
```

Ohne `ANTHROPIC_API_KEY` (in `.env`, siehe `.env.example`) läuft die CLI im Kopier-Modus. Die SQLite-Datei liegt unter `data/vault.sqlite`, überschreibbar mit `HARNESS_DB`. Modell: `CLAUDE_MODEL`, Standard `claude-sonnet-5-5`.
