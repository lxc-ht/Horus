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

- Neuer Typ `KENNUNG` in `TYPES`: Steuer-ID, Steuernummer, SV-Nummer, Versichertennummer, Aktenzeichen, Mandanten- und Patientennummer, URL.
- `send()`: Stoppt Claude wegen `max_tokens`, liefert es den Teil plus `cloud.TRUNCATED_NOTE` am Ende. Die Signatur bleibt ein String.

## Bekannte Schwächen

- Maskiert wird jedes Vorkommen als Teilzeichenkette, passend zum Leck-Check. Das ergibt manchmal hässliche Stellen wie „[FIRMA_3]skündigung“ (aus „Eigenbedarfskündigung“). Sicher, aber nicht schön. Ein Leck-Check und eine Maskierung an Wortgrenzen bräuchten eine eigene Entscheidung, weil dann „Müllerstraße“ durchrutscht.
- Kurze Originalwerte (z. B. ein ORT „Ems“) maskieren viel mit. Eventuell eine Mindestlänge oder Wortgrenzen nur für kurze Werte.
- GLiNER meldet Rollenwörter („Vermieterin“, „Patientin“) gern als PERSON. Es gibt eine kleine Stoppliste in `detect.py`, keine vollständige Lösung.
- „Möglicherweise verändert“ kann falsch anschlagen, wenn ein Typname mit Zahl normal im Text steht („am Ort 2“). Ist nur eine Warnung, ersetzt wird nichts.
- Freigaben liegen nur im Speicher. Nach einem Neustart des Prozesses sind Sitzungen und Freigaben weg, die Zuordnung in SQLite bleibt. Bei Ctrl+C, SIGTERM und geschlossenem Terminal löscht der Prozess seine Sitzungen, nach einem Absturz oder SIGKILL fallen sie weg, sobald nach 24 Stunden ein neuer Text kommt.
- Der Leck-Check vergleicht ohne Unicode-Normalisierung. NFC- und NFD-„ü“ gelten als verschieden.
- Der stdin-Modus der CLI liest die Prüfbefehle von /dev/tty. Ohne Terminal (CI, Pipe ohne tty) bricht er mit Meldung ab.
- Namensteile, die auch gewöhnliche Wörter sind, werden mitmaskiert: Bei einer Person „Anna Berg“ wird aus „am Berg“ „am [PERSON_1]“, zurückübersetzt „am Anna Berg“. Sicher, verfälscht aber die Antwort. Eventuell eine Liste häufiger Wörter oder Großschreibung als Bedingung.
- Für die Eindeutigkeit eines Namensteils zählen nur Personen. Steckt derselbe Teil in einer Firma („Kettelhut & Brenner Tischlerei GmbH“), wird ein allein stehendes „Kettelhut“ trotzdem der Person zugeordnet, auch wenn die Firma gemeint ist.
- Der Bindestrich gilt als Wortgrenze: Aus „Musterfrau-Stiftung“ wird „[PERSON_1]-Stiftung“.
- Erkennt der Detektor einen Nachnamen allein als eigene Person („Weidenfeld“ neben „Jonas Weidenfeld“), gibt es zwei Platzhalter für dieselbe Person. Der Teil ist dann mehrdeutig und wird nicht dem vollen Namen zugeordnet. Gleiches gilt, wenn der Mensch den Nachnamen per `add_manual` als PERSON ergänzt.
- Die Regex für ADRESSE, KENNUNG und PERSON hinter einer Anrede sucht bewusst breit und kann Falschtreffer liefern („Frau Kettelhut Unterlagen“). Sie lassen sich in der Prüfung zurücknehmen.
- Das Modell meldet auch Falschtreffer, die die Regex nicht verursacht: „Der Bundesgerichtshof 12“ wird zu FIRMA.
- Mehrdeutige Straßenendungen wie „Reeperbahn 12“ erkennt die Regex nur mit „Am …“ davor oder PLZ dahinter, sonst bleibt nur das Modell.
- Eine nackte Zahl wird nie zur KENNUNG: Eine elfstellige Zahl zählt ohne Bezeichner nur mit gültiger Prüfziffer der Steuer-ID (ISO 7064 MOD 11,10), eine Steuernummer nur nach „Steuernummer“, „St.-Nr.“ oder „StNr“. Eine Steuernummer ohne Bezeichner mit führender 0 („022/815/08150“) wird trotzdem maskiert, aber als TELEFON.
- KENNUNG kennt als Bezeichner bisher nur Mandanten- und Patientennummer. Es fehlen Kunden-, Fall-, Vertrags-, Versicherungs-, Rechnungs- und Policennummer sowie „Unser Zeichen“ / „Ihr Zeichen“.
- Reisepassnummern werden nicht erkannt, Kfz-Kennzeichen und Personalausweisnummern nur mit Bezeichner davor.
- „34127 Kassel“ wird als ADRESSE maskiert, „Kassel“ allein im Fließtext findet nur das Modell.
- Nicht erkannt: IP-Adressen, Datum ohne Jahr („am 14.03.“), Monat und Jahr („im März 1979“), IBAN in Kleinbuchstaben (nur der Ziffernteil wird als TELEFON maskiert).

## Später

- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person mit Tippfehlern, Genitiv („Musterfraus“) oder Spitznamen erkennen. Einzelne Namensteile als ganzes Wort werden schon mitmaskiert, alles andere meldet höchstens die Warnung.
- Verschlüsselung der Datenbank.
- Streaming der Claude-Antwort für lange Texte (aktuell eine Anfrage, max_tokens 16000).
