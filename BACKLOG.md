# BACKLOG

Was auffällt, aber nicht in den aktuellen Block gehört.

## Vertrag erweitert

Ergänzungen an `src/harness/api.py`, die über den festgelegten Vertrag hinausgehen. Bestehende Signaturen bleiben unverändert.

- `api.set_detectors(detectors | None)` – Detektoren festlegen (Tests mit Fake-Detektor, später weitere Detektoren). `None` = Standard (Regex + GLiNER).
- `api.forget(session_id)` – Sitzung samt Zuordnung sofort löschen (Knopf „Zuordnung jetzt löschen“). Danach gilt keine Freigabe der Sitzung mehr, `restore` wirft `KeyError`. Unbekannte Sitzung → `KeyError` mit fertigem Satz.
- `api.warmup()` – lädt die Erkennung vorab mit einem erfundenen Satz, ohne Sitzung und ohne Zuordnung. Die Weboberfläche ruft sie beim Start im Hintergrund auf (abschaltbar mit `LP7_NO_WARMUP=1`). Lädt das Modell nicht, wirft sie `ModelUnavailableError` mit deutschem Satz.
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

- `MaskResult.uncertain` meldet zusätzlich Zusammenhang, der eine Person ohne Namen verrät (Typ-Vorschlag PERSON, Text bleibt unverändert).
- `MaskResult.uncertain` – Liste von `Uncertain` (Text, Typ, Position im maskierten Text, `masked`, Grund als fertiger deutscher Satz). Stellen, die der Mensch ansehen soll: Modell unter der Schwelle, nicht ersetzte Nummern, knappe Modelltreffer, Namensteile ohne Anrede. Der Text ändert sich dadurch nicht. Bestehende Felder bleiben.

## Bekannte Schwächen

- Kyrillische und griechische Doppelgänger werden nur bei der IBAN-Suche wie lateinische Buchstaben behandelt („DЕ89“ mit kyrillischem Е). In E-Mails, Kennungen oder Namen gilt das nicht.
- Umgehungstest gegen die Demo, noch offen: Quasi-Identifikatoren aus dem Kontext („der Bürgermeister von …“): Eine kurze Regel zeigt „die einzige Kinderärztin im Ort“ und Ämter wie „Bürgermeister von Hasenwinkel“ als unsichere Stelle, ersetzt aber nichts. Alles andere („die Nachbarin mit dem roten Porsche“) bleibt Sache der Prüfung.
- Eine Antwort von Claude kann Links oder Markdown-Bilder enthalten, in denen nach der Rückübersetzung echte Werte stehen („![x](https://…?a=[IBAN_1])“). Die Oberfläche zeigt das nur als Text. Riskant wird es erst, wenn jemand den Text in ein Programm kopiert, das Markdown oder HTML darstellt.
- Zweibuchstabige Namensteile („Wu“, „Do“) werden in genau dieser Schreibweise mitmaskiert. Bei einer Person „Tran Do“ wird auch die Abkürzung „Do“ für Donnerstag zum Namen. Die Prüfung zeigt solche Stellen als unsicher.
- Die Ausnahmen beim Kfz-Kennzeichen sind eine kurze Liste (EU, VO, DIN, ISO, VDE, VW, BMW). Andere Normen wie „ABC-DE 12“ werden maskiert, echte Kennzeichen aus Dinslaken („DIN-AB 123“) nicht.
- Kurze Bezeichner ohne Nummernwort (Konto, Kto., Depot, Vertrag, Police, Rechnung) zählen mit einem Wert ab drei Ziffern, Jahre und Zeiträume ausgenommen. Andere Wörter wie „Vorgang 4471-B“ werden weiter nur als unsichere Stelle gezeigt.
- Sehr lange Texte (200 KB) blockieren die Analyse über eine Minute und halten dabei die globale Sperre. Nichts wird gesendet, die Demo hängt aber. Die Weboberfläche lehnt deshalb Texte über 100.000 Zeichen mit einem Hinweis ab; der Kern und die CLI haben keine Grenze.
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
- Adressen ohne Straßenwort („Am Sande 12“, „An der Kirche 3“) zählen nur mit PLZ dahinter oder einem Kontextwort wie „wohnhaft“ oder „Anschrift:“ kurz davor, und nur, wenn nach der Hausnummer der Satz oder die Zeile endet. „Wir treffen uns Am Sande 12.“ bleibt deshalb stehen.
- Eine nackte Zahl wird nie zur KENNUNG: Eine elfstellige Zahl zählt ohne Bezeichner nur mit gültiger Prüfziffer der Steuer-ID (ISO 7064 MOD 11,10), eine Steuernummer nur nach „Steuernummer“, „St.-Nr.“ oder „StNr“. Eine Steuernummer ohne Bezeichner mit führender 0 („022/815/08150“) wird trotzdem maskiert, aber als TELEFON.
- „34127 Kassel“ wird als ADRESSE maskiert, „Kassel“ allein im Fließtext findet nur das Modell.
- Nicht erkannt: IP-Adressen und einstellige Daten ohne Jahr („am 1.3.“), weil sie von Gliederungen wie „3.1.“ nicht zu unterscheiden sind. Zweistellige Gliederungen wie „12.10.“ gelten dagegen als Datum.
- Schreibweisen und Genitiv-s gelten nur für großgeschriebene ganze Wörter. Am Satzanfang wird bei „Anna Link“ auch „Links“ maskiert, bei Herrn Koenig auch „Der König“. Sicher, verfälscht aber die Antwort.
- Kleingeschriebene Schreibweisen („weiß“ bei „Hans Weiss“) bleiben im Text, die Warnung nennt sie. Der Leck-Check prüft bewusst nur die exakte Schreibweise, sonst könnte „ich weiß es“ jede Freigabe blockieren.

- Englische Texte, aus dem Block „Englische Anreden“ (06.11.) bewusst herausgelassen:
  - Kennungen mit englischem Bezeichner wie „client number C-26-0815“ werden nur als unsicher markiert, nicht ersetzt. Eigener Auftrag: Bezeichner der Kennungen um englische Wörter erweitern.
  - Straßen ohne Hausnummer wie „Mill Road“ werden nicht erkannt, im Deutschen genauso („Bardowicker Straße“).
  - Datum: „14 September 2026“ wird ersetzt, „2 October 2026“ nicht. Englische Monatsnamen fehlen in `_DATE`, „September“ passt nur, weil er deutsch gleich heißt.
  - `api.py` kennt die englischen Anreden noch nicht (`_AFTER_SALUTATION`, `_SALUTATION_BEFORE`, Vertrag, deshalb nicht angefasst). Folge: „Mrs [PERSON_3]“ wird als „Nur ein Namensteil“ unsicher markiert, und die Rückübersetzung warnt bei „Mr [PERSON_2]“, wenn der Platzhalter sonst auch allein für den Nachnamen stand. Bei „Frau“ und „Herr“ unterbleibt das. Nur zusätzliche Hinweise, kein Leck; beide Ausdrücke um Mr, Mrs, Ms, Miss, Mx, Sir erweitern.
  - Der Regex-Detektor findet „Mr X“ und „Ms X“ in jeder Schreibweise, „Miss“ und „Sir“ nur großgeschrieben (sonst wäre „you miss Paris“ ein Name). Englische Berufswörter vor dem Namen („Mr Justice Whitaker“, „Doctor“) kennt er nicht.

## Später

- Aus dem Vergleich mit Presidio (MIT-Lizenz), noch nicht übernommen: Positivliste für Begriffe, die nie maskiert werden sollen (z. B. „Landgericht Lüneburg“), Prüfziffern für Personalausweis und Reisepass ohne Bezeichner (ICAO 9303), MAC-Adressen, UUIDs, Krypto-Adressen, und eine Erklärung je Fundstelle, welches Muster und welches Kontextwort gegriffen hat.
- PDF, Word, OCR als Eingabe (Achtung: Lecks über Metadaten).
- Zweiter Detektor, z. B. lokales LLM über Ollama – die Detektor-Schnittstelle in `detect.py` ist dafür vorbereitet.
- Varianten derselben Person mit Tippfehlern, Spitznamen oder ohne Umlaut („Muller“) erkennen. Genitiv-s und die Schreibweisen ä/ae, ö/oe, ü/ue, ß/ss werden schon mitmaskiert.
- Verschlüsselung der Datenbank.
- Streaming der Claude-Antwort für lange Texte (aktuell eine Anfrage, max_tokens 16000).
