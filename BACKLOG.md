# BACKLOG

Was auffällt, aber nicht in den aktuellen Block gehört.

## Vertrag erweitert

Ergänzungen an `src/harness/api.py`, die über den festgelegten Vertrag hinausgehen. Bestehende Signaturen bleiben unverändert.

- `api.set_detectors(detectors | None)` – Detektoren festlegen (Tests mit Fake-Detektor, später weitere Detektoren). `None` = Standard (Regex + GLiNER).
- `api.CloudError` – `send()` wirft sie, wenn Claude nicht erreichbar ist, den Key ablehnt oder die Anfrage ablehnt (`stop_reason: refusal`). Die Meldung ist ein fertiger deutscher Satz und enthält nie Text aus der Anfrage.
- `analyze` vereinheitlicht den Text mit `mask.canonical` (NFKC, ohne unsichtbare Formatzeichen). `original_text` ist diese Fassung, nicht die eingegebene Zeichenfolge. `add_manual` behandelt den Begriff genauso.
- `vault.placeholder_for` kennt `reserved`: Platzhalter, die wörtlich im Text stehen, werden nicht vergeben. Bei der Rückübersetzung bleiben sie stehen und kommen in `unknown`.
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

- Umgehungstest gegen die Demo, noch offen: zweibuchstabige Nachnamen allein („Wu“, name_parts beginnt bei 3 Zeichen), Aktenzeichen in Kleinschreibung („az 3 o 123/26“), kyrillische Doppelgänger in IBANs („DЕ89“ mit kyrillischem Е, nur der Rest wird maskiert), Quasi-Identifikatoren aus dem Kontext („der Bürgermeister von …“).
- Bezeichner ohne Nummernwort wie „Konto 532013000“ werden nicht ersetzt, sondern nur als unsichere Stelle gezeigt.
- Sehr lange Texte (200 KB) blockieren die Analyse über eine Minute und halten dabei die globale Sperre. Nichts wird gesendet, die Demo hängt aber. Eventuell eine Längengrenze.
- Die Weboberfläche setzt keinen Frame-Schutz (X-Frame-Options) und prüft den Origin nicht. Fremde Seiten können sie einbetten, Antworten aber nicht lesen, Text und JSON lehnt die Preflight-Regel ab.
- Wegen canonical() fallen auch Formatzeichen in Emojis weg (Zero-Width-Joiner) und „m²“ wird zu „m2“. Sicher, ändert aber minimal den gesendeten Text.
- Maskiert wird jedes Vorkommen als Teilzeichenkette, passend zum Leck-Check. Das ergibt manchmal hässliche Stellen wie „[FIRMA_3]skündigung“ (aus „Eigenbedarfskündigung“). Sicher, aber nicht schön. Ein Leck-Check und eine Maskierung an Wortgrenzen bräuchten eine eigene Entscheidung, weil dann „Müllerstraße“ durchrutscht.
- Kurze Originalwerte (z. B. ein ORT „Ems“) maskieren viel mit. Eventuell eine Mindestlänge oder Wortgrenzen nur für kurze Werte.
- GLiNER meldet Rollenwörter („Vermieterin“, „Patientin“) gern als PERSON. Es gibt eine kleine Stoppliste in `detect.py`, keine vollständige Lösung.
- „Möglicherweise verändert“ kann falsch anschlagen, wenn ein Typname mit Zahl normal im Text steht („am Ort 2“). Ist nur eine Warnung, ersetzt wird nichts.
- Freigaben liegen nur im Speicher. Nach einem Neustart des Prozesses sind Sitzungen und Freigaben weg, die Zuordnung in SQLite bleibt. Bei Ctrl+C, SIGTERM und geschlossenem Terminal löscht der Prozess seine Sitzungen, nach einem Absturz oder SIGKILL fallen sie weg, sobald nach 24 Stunden ein neuer Text kommt.
- Der stdin-Modus der CLI liest die Prüfbefehle von /dev/tty. Ohne Terminal (CI, Pipe ohne tty) bricht er mit Meldung ab.
- Namensteile, die auch gewöhnliche Wörter sind, werden mitmaskiert: Bei einer Person „Anna Berg“ wird aus „am Berg“ „am [PERSON_1]“, zurückübersetzt „am Anna Berg“. Sicher, verfälscht aber die Antwort. Eventuell eine Liste häufiger Wörter oder Großschreibung als Bedingung.
- Für die Eindeutigkeit eines Namensteils zählen nur Personen. Steckt derselbe Teil in einer Firma („Kettelhut & Brenner Tischlerei GmbH“), wird ein allein stehendes „Kettelhut“ trotzdem der Person zugeordnet, auch wenn die Firma gemeint ist.
- Der Bindestrich gilt als Wortgrenze: Aus „Musterfrau-Stiftung“ wird „[PERSON_1]-Stiftung“.
- Erkennt der Detektor einen Nachnamen allein als eigene Person („Weidenfeld“ neben „Jonas Weidenfeld“), gibt es zwei Platzhalter für dieselbe Person. Der Teil ist dann mehrdeutig und wird nicht dem vollen Namen zugeordnet. Gleiches gilt, wenn der Mensch den Nachnamen per `add_manual` als PERSON ergänzt.
- Die Regex für ADRESSE, KENNUNG und PERSON hinter einer Anrede sucht bewusst breit und kann Falschtreffer liefern („Frau Kettelhut Unterlagen“). Sie lassen sich in der Prüfung zurücknehmen.
- Das Modell meldet auch Falschtreffer, die die Regex nicht verursacht: „Der Bundesgerichtshof 12“ wird zu FIRMA.
- Mehrdeutige Straßenendungen wie „Reeperbahn 12“ erkennt die Regex nur mit „Am …“ davor oder PLZ dahinter, sonst bleibt nur das Modell.
- Eine nackte Zahl wird nie zur KENNUNG: Eine elfstellige Zahl zählt ohne Bezeichner nur mit gültiger Prüfziffer der Steuer-ID (ISO 7064 MOD 11,10), eine Steuernummer nur nach „Steuernummer“, „St.-Nr.“ oder „StNr“. Eine Steuernummer ohne Bezeichner mit führender 0 („022/815/08150“) wird trotzdem maskiert, aber als TELEFON.
- „34127 Kassel“ wird als ADRESSE maskiert, „Kassel“ allein im Fließtext findet nur das Modell.
- Nicht erkannt: IP-Adressen und einstellige Daten ohne Jahr („am 1.3.“), weil sie von Gliederungen wie „3.1.“ nicht zu unterscheiden sind. Zweistellige Gliederungen wie „12.10.“ gelten dagegen als Datum.
- Schreibweisen und Genitiv-s gelten nur für großgeschriebene ganze Wörter. Am Satzanfang wird bei „Anna Link“ auch „Links“ maskiert, bei Herrn Koenig auch „Der König“. Sicher, verfälscht aber die Antwort.
- Kleingeschriebene Schreibweisen („weiß“ bei „Hans Weiss“) bleiben im Text, die Warnung nennt sie. Der Leck-Check prüft bewusst nur die exakte Schreibweise, sonst könnte „ich weiß es“ jede Freigabe blockieren.

## Später

- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person mit Tippfehlern, Spitznamen oder ohne Umlaut („Muller“) erkennen. Genitiv-s und die Schreibweisen ä/ae, ö/oe, ü/ue, ß/ss werden schon mitmaskiert.
- Verschlüsselung der Datenbank.
- Streaming der Claude-Antwort für lange Texte (aktuell eine Anfrage, max_tokens 16000).
