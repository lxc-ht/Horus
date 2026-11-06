# Erkennung messen

```bash
uv run --locked python -m benchmarks.erkennung
```

Beim ersten Lauf braucht GLiNER sein Modell. Mit gefülltem Modellcache funktioniert die Messung auch mit `HF_HUB_OFFLINE=1`. Sie nutzt eine temporäre Zuordnungsdatenbank und wertet das automatische Ergebnis vor manueller Prüfung aus.

Die 12 erfundenen Texte decken unter anderem Brief, E-Mail, Tabellenlayout und englische Formulierungen ab. Der Test startet beim extrahierten Text. Die Dateiextraktion ist separat in `web/test_app.py` geprüft.

Für jede markierte Angabe wird nach Zeichenposition geprüft, ob sie vollständig, teilweise oder gar nicht ersetzt wurde. Die Kategorie in dieser Tabelle ist die erwartete Kategorie. Ein Falschtreffer ist eine Ersetzung außerhalb aller markierten Angaben. Die Tabelle bewertet die Abdeckung des Originaltexts, keine korrekte Einordnung des Platzhaltertyps.

| Typ | Markiert | Vollständig ersetzt | Teilweise ersetzt | Übersehen | Falschtreffer |
| --- | ---: | ---: | ---: | ---: | ---: |
| Person | 15 | 15 | 0 | 0 | 1 |
| Firma | 1 | 1 | 0 | 0 | 3 |
| Adresse | 2 | 2 | 0 | 0 | 1 |
| Ort | 1 | 1 | 0 | 0 | 0 |
| E-Mail | 6 | 6 | 0 | 0 | 0 |
| Telefon | 1 | 1 | 0 | 0 | 0 |
| IBAN | 1 | 1 | 0 | 0 | 0 |
| Datum | 3 | 2 | 0 | 1 | 0 |
| Kennung | 6 | 3 | 0 | 3 | 0 |
| **Gesamt** | **36** | **32** | **0** | **4** | **5** |

Gemessen am 6. November 2026 auf macOS mit Regex und lokal zwischengespeichertem GLiNER. Zwei Kontonummern in der Tabelle, eine englische Kundennummer und ein englisches Datum blieben stehen. Unter den Falschtreffern waren „Winter“ als Jahreszeit und „Bürobedarf“. Die Stichprobe dient dem Vergleich von Änderungen an der Erkennung. Für echte Dokumente gibt sie keine belastbare Erfolgsquote an.
