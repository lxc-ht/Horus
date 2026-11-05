# BACKLOG

Was auffällt, aber nicht in den aktuellen Block gehört.

## Vertrag erweitert

Ergänzungen an `src/harness/api.py`, die über den festgelegten Vertrag hinausgehen. Bestehende Signaturen bleiben unverändert.

- `api.set_detectors(detectors | None)` – Detektoren festlegen (Tests mit Fake-Detektor, später weitere Detektoren). `None` = Standard (Regex + GLiNER).
- `api.CloudError` – `send()` wirft sie, wenn Claude nicht erreichbar ist, den Key ablehnt oder die Anfrage ablehnt (`stop_reason: refusal`). Die Meldung ist ein fertiger deutscher Satz und enthält nie Text aus der Anfrage.
- `LeakError.placeholders` – Liste der Platzhalter, deren Originalwert noch im Text steht (nie die Werte selbst). Damit kann die Oberfläche die Stelle markieren.
- Fehlerfälle ohne eigene Ausnahme im Vertrag: unbekannte Sitzung → `KeyError`; unbekannter Typ, leerer Begriff oder unbekannter Platzhalter bei `add_manual`/`remove` → `ValueError` mit deutschem Satz.
- `add_manual` mit einem Begriff, der im Text nicht vorkommt: keine Änderung, Hinweis in `MaskResult.warnings`.
- `RestoreResult.warnings` nennt zusätzlich Platzhalter, die auch nur für einen Namensteil standen und ohne Anrede davor. Der Originalwert steht dann im Hinweis, er bleibt wie der Rest der Rückübersetzung lokal.
- `remove` akzeptiert den Platzhalter mit oder ohne Klammern (`[PERSON_1]` oder `PERSON_1`).
- `send()` prüft die Freigabe immer vor dem Key. `NoApiKeyError` heißt also: `rel.text` ist gültig freigegeben und darf im Kopier-Modus angezeigt werden.
- `send()` akzeptiert nur Freigaben, die `release()` selbst ausgestellt hat. Jede Änderung (`add_manual`, `remove`) macht alle bisherigen Freigaben der Sitzung ungültig, auch wenn der Text danach wieder gleich aussieht.

- Neuer Typ `KENNUNG` in `TYPES`: Steuer-ID, Steuernummer, SV-Nummer, Versichertennummer, Aktenzeichen, Mandanten- und Patientennummer, URL.
- `send()`: Stoppt Claude wegen `max_tokens`, liefert es den Teil plus `cloud.TRUNCATED_NOTE` am Ende. Die Signatur bleibt ein String.

- `MaskResult.uncertain` – Liste von `Uncertain` (Text, Typ, Position im maskierten Text, `masked`, Grund als fertiger deutscher Satz). Stellen, die der Mensch ansehen soll: Modell unter der Schwelle, nicht ersetzte Nummern, knappe Modelltreffer, Namensteile ohne Anrede. Der Text ändert sich dadurch nicht. Bestehende Felder bleiben.

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
- Nicht erkannt: IP-Adressen und einstellige Daten ohne Jahr („am 1.3.“), weil sie von Gliederungen wie „3.1.“ nicht zu unterscheiden sind. Zweistellige Gliederungen wie „12.10.“ gelten dagegen als Datum.
- Steht ein Platzhalter schon wörtlich im Originaltext („[PERSON_1]“), wird er in der Rückübersetzung durch die echte Person ersetzt. Fix: `api.py` reicht die im Text vorkommenden Nummern an `vault.placeholder_for` weiter, damit sie nicht vergeben werden.
- Schreibweisen und Genitiv-s gelten nur für großgeschriebene ganze Wörter. Am Satzanfang wird bei „Anna Link“ auch „Links“ maskiert, bei Herrn Koenig auch „Der König“. Sicher, verfälscht aber die Antwort.
- Kleingeschriebene Schreibweisen („weiß“ bei „Hans Weiss“) bleiben im Text, die Warnung nennt sie. Der Leck-Check prüft bewusst nur die exakte Schreibweise, sonst könnte „ich weiß es“ jede Freigabe blockieren.
- Text in NFD-Form wird schlechter erkannt: Von „jürgen@beispiel.de“ bleibt „jü“ stehen, „Anna Müller“ wird nur teilweise maskiert. Vor dem Erkennen auf NFC normalisieren.

## Später

- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person mit Tippfehlern, Spitznamen oder ohne Umlaut („Muller“) erkennen. Genitiv-s und die Schreibweisen ä/ae, ö/oe, ü/ue, ß/ss werden schon mitmaskiert.
- Verschlüsselung der Datenbank.
- Streaming der Claude-Antwort für lange Texte (aktuell eine Anfrage, max_tokens 16000).
