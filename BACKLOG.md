# BACKLOG

Was auffällt, aber nicht in den aktuellen Block gehört.

## Vertrag erweitert

Ergänzungen an `src/harness/api.py`, die über den festgelegten Vertrag hinausgehen. Bestehende Signaturen bleiben unverändert.

- `api.set_detectors(detectors | None)` – Detektoren festlegen (Tests mit Fake-Detektor, später weitere Detektoren). `None` = Standard (Regex + GLiNER).
- `api.CloudError` – `send()` wirft sie, wenn Claude nicht erreichbar ist, den Key ablehnt oder die Anfrage ablehnt (`stop_reason: refusal`). Die Meldung ist ein fertiger deutscher Satz und enthält nie Text aus der Anfrage.
- `LeakError.placeholders` – Liste der Platzhalter, deren Originalwert noch im Text steht (nie die Werte selbst). Damit kann die Oberfläche die Stelle markieren.
- Fehlerfälle ohne eigene Ausnahme im Vertrag: unbekannte Sitzung → `KeyError`; unbekannter Typ, leerer Begriff oder unbekannter Platzhalter bei `add_manual`/`remove` → `ValueError` mit deutschem Satz.
- `add_manual` mit einem Begriff, der im Text nicht vorkommt: keine Änderung, Hinweis in `MaskResult.warnings`.
- `remove` akzeptiert den Platzhalter mit oder ohne Klammern (`[PERSON_1]` oder `PERSON_1`).
- `send()` prüft die Freigabe immer vor dem Key. `NoApiKeyError` heißt also: `rel.text` ist gültig freigegeben und darf im Kopier-Modus angezeigt werden.
- `send()` akzeptiert nur Freigaben, die `release()` selbst ausgestellt hat. Jede Änderung (`add_manual`, `remove`) macht alle bisherigen Freigaben der Sitzung ungültig, auch wenn der Text danach wieder gleich aussieht.

## Bekannte Schwächen

- Maskiert wird jedes Vorkommen als Teilzeichenkette, passend zum Leck-Check. Das ergibt manchmal hässliche Stellen wie „[FIRMA_3]skündigung“ (aus „Eigenbedarfskündigung“). Sicher, aber nicht schön. Ein Leck-Check und eine Maskierung an Wortgrenzen bräuchten eine eigene Entscheidung, weil dann „Müllerstraße“ durchrutscht.
- Kurze Originalwerte (z. B. ein ORT „Ems“) maskieren viel mit. Eventuell eine Mindestlänge oder Wortgrenzen nur für kurze Werte.
- GLiNER meldet Rollenwörter („Vermieterin“, „Patientin“) gern als PERSON. Es gibt eine kleine Stoppliste in `detect.py`, keine vollständige Lösung.
- „Möglicherweise verändert“ kann falsch anschlagen, wenn ein Typname mit Zahl normal im Text steht („am Ort 2“). Ist nur eine Warnung, ersetzt wird nichts.
- Freigaben liegen nur im Speicher. Nach einem Neustart des Prozesses sind Sitzungen und Freigaben weg, die Zuordnung in SQLite bleibt. Alte Sitzungen sollten nach einer Frist aus der Datenbank gelöscht werden.
- Der Leck-Check vergleicht ohne Unicode-Normalisierung. NFC- und NFD-„ü“ gelten als verschieden.
- Der stdin-Modus der CLI liest die Prüfbefehle von /dev/tty. Ohne Terminal (CI, Pipe ohne tty) bricht er mit Meldung ab.

## Später

- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person zusammenführen („Max Müller“ = „Herr Müller“). Bis dahin meldet der Leck-Check den Fall als Warnung.
- Verschlüsselung der Datenbank.
- Streaming der Claude-Antwort für lange Texte (aktuell eine Anfrage, max_tokens 16000).
