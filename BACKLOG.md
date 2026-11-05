# BACKLOG

Was auffällt, aber nicht in den aktuellen Block gehört.

## Vertrag erweitert

Ergänzungen an `src/harness/api.py`, die über den festgelegten Vertrag hinausgehen. Bestehende Signaturen bleiben unverändert.

## Später

- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person zusammenführen („Max Müller“ = „Herr Müller“). Bis dahin meldet der Leck-Check den Fall als Warnung.
- Verschlüsselung der Datenbank.
