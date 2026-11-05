# Projektstand

Hier stimmen sich alle ab, Menschen und Agenten. Agenten können nicht direkt miteinander sprechen und sehen nur, was gepusht ist.

**So nutzen wir diese Datei**

1. Vor der Arbeit: `git pull`, dann diese Datei lesen.
2. Vor dem Start: Aufgabe mit deinem Namen unter „In Arbeit“ eintragen und pushen, damit niemand dasselbe baut.
3. Nach der Arbeit: Aufgabe nach „Erledigt“ verschieben, neue Aufgaben ergänzen und pushen.
4. Jede Aufgabe steht in einer eigenen Zeile. Das hält Merge-Konflikte klein.

**Ziel**

Eine Demo für die Jury beim Leuphana AI Hackathon: Team-Pitch am Freitag, 6. November 2026. Sie zeigt, dass eine Kanzlei Claude nutzen kann und nur der geprüfte, maskierte Text den Rechner verlässt.

**Ab 05.11. abends: Code-Stopp für `main`.** Neue Arbeit nur noch als PR, niemand merged bis zur Prüfung am 06.11. morgens (Claudian für Paul). Die Demo bleibt auf dem Stand `9913645`.

**In Arbeit**




**Nächste Aufgaben**

Kern (`Phantom-create-1`):

- [ ] Falsche Rückübersetzung verhindern, nicht nur melden: Stand ein Platzhalter nur für einen Namensteil wie „Antrag“, warnt der Bericht seit PR #16, der falsche Text bleibt aber. Nach Herr, Frau, Dr. oder Prof. kommt bewusst keine Warnung.
- [ ] Wünsche aus `web/BACKLOG.md` unter „Wunsch an den Kern“ umsetzen.

Oberfläche (`lxc-ht`, `web/static/index.html`):

- [ ] Die aktualisierte echte Arbeitsoberfläche mit Paul am Vortragsrechner durchspielen.
- [ ] Prüfen, ob es seit PR #26 noch so ist: Nach dem Zurückübersetzen blieb für die Antwort wenig Platz, weil Hinweis und Eingabefeld oben stehen bleiben (Stand vor PR #26, Screenshot bei Paul). Vorschlag: beides nach dem Zurückübersetzen einklappen.


Beide:

- [ ] Demo auf dem Vortragsrechner durchspielen und das Modell vorher einmal laden.
- [ ] Pitch vorbereiten, auch für diese Fragen: Warum kein lokales Modell? Was, wenn der Kontext die Person verrät? Was ist mit der DSGVO?
  - DSGVO, Vorschlag: „LP7 macht niemanden automatisch DSGVO-konform. Aber es sorgt dafür, dass nur der geprüfte, maskierte Text den Rechner verlässt und die Zuordnung lokal bleibt. Das senkt das Risiko deutlich und ist der technische Baustein. Vertrag mit dem Anbieter und Prüfung durch den Menschen bleiben Pflicht.“
  - Falls jemand nach Anonymisierung fragt, zum Beispiel wie bei Bildern: „Bilder lassen sich durch künstliche Gesichter weitgehend entschärfen, bei Text bleibt der Zusammenhang. Deshalb versprechen wir keine Anonymität. Wir zeigen dem Menschen genau, was rausgeht.“
  - Nicht versprechen: „DSGVO-konform“ oder „anonym“. Rechtlich ist das noch nicht geprüft.
  - Messung für den Pitch (Stand `a4e1dbe`, Regex und GLiNER): 87 von 89 Angaben in 22 kurzen, erfundenen Texten vollständig ersetzt, nur mit Regex 37 von 89. Die Texte hat der Agent selbst geschrieben, der den Code kannte. Das ist also kein Beleg für echte Akten und keine Erkennungsrate. Nicht als „98 % Schutz“ zeigen.
  - Bekannte Grenzen aus derselben Prüfung: Stadt „Essen“ blieb in einem längeren Satz stehen, „Kundenkonto 88213-44“ und „Ausweis L01X00T47“ ebenso, „im Winter“ wurde bei einer Person „Rosa Winter“ zum Namen. „Die einzige Kinderärztin im Ort“ findet keine Erkennung (mit #42 erscheint sie als unsichere Stelle).

**Erledigt**

- [x] Sieben kleine PRs, alle offen, Prüfung durch Paul (`lxc-ht`, Claude, 05.11. abends): Aufgaben-Vorlagen unter „Dein Original“ ([#39](https://github.com/lxc-ht/LP7/pull/39)), „Kopieren und Claude öffnen“ ([#40](https://github.com/lxc-ht/LP7/pull/40), in Safari einmal klicken), „Zuordnung jetzt löschen“ mit neuem `api.forget` ([#41](https://github.com/lxc-ht/LP7/pull/41)), Hinweis bei verräterischem Zusammenhang wie „die einzige Kinderärztin im Ort“ ([#42](https://github.com/lxc-ht/LP7/pull/42)), Texte über 100.000 Zeichen abgelehnt ([#43](https://github.com/lxc-ht/LP7/pull/43)), Antwortfeld klappt nach dem Zurückübersetzen ein ([#44](https://github.com/lxc-ht/LP7/pull/44)), Word-Tabellen als Zeilen ([#45](https://github.com/lxc-ht/LP7/pull/45)). #39, #40, #41 und #44 haben untereinander kleine Konflikte in `index.html` (beides behalten). Alle sieben zusammen liegen fertig zusammengeführt und geprüft auf `claude/alle-verbesserungen` (216 Tests, `web.test_app`, Browserprüfung grün), ohne #36 bis #38.
- [x] Modell lädt beim Serverstart im Hintergrund, der erste Klick auf „Text analysieren“ wartet nicht mehr; neu im Vertrag `api.warm_up()` ([PR #37](https://github.com/lxc-ht/LP7/pull/37), `lxc-ht`, Claude). Offen, wartet auf Pauls Prüfung. Echtes Vorladen von GLiNER nur auf dem Mac prüfbar: starten, kurz warten, analysieren.
- [x] Freigabe-Nachweis: nach der Freigabe Prüfsumme sichtbar, Knopf „Nachweis speichern“ lädt Zeit, SHA-256, Anzahl je Typ und freigegebenen Text herunter, ohne Originale ([PR #38](https://github.com/lxc-ht/LP7/pull/38), `lxc-ht`, Claude). Offen, wartet auf Pauls Prüfung.
- [x] Überschrift „Your Data Is Yours“ mit Horus-Auge (SVG inline) in Systemserifen auf Papierton, nur Kopfzeile und Seitenhintergrund ([PR #36](https://github.com/lxc-ht/LP7/pull/36), `lxc-ht`, Claude). Offen, wartet auf Pauls Prüfung, nicht gemergt. Kopfzeile 121 px auf 1440 × 900 und 109 px auf 1280 × 800, Schrift dort 49 bzw. 43 px statt 64 (sonst über 130 px). Alle Tests und Browserprüfung grün. Auf dem Vortragsrechner einmal mit Hoefler Text ansehen.
- [x] Installation frisch gemessen (Linux in der Cloud, leere Caches): Python und Pakete 5,8 GB, 7 Minuten, 213 Tests grün, Startdatei bleibt im ZIP ausführbar. Modell und Offline-Betrieb nicht prüfbar, weil die Umgebung Hugging Face sperrt; auf einem Mac nachmessen ([PR #35](https://github.com/lxc-ht/LP7/pull/35), offen, Prüfung durch Paul, `lxc-ht`, Claude).
- [x] „Beispiel laden“ und Eintippen setzen Analyse und Freigabe zurück, Fehler beim Datei laden stehen unter „Dein Original“ ([PR #33](https://github.com/lxc-ht/LP7/pull/33), `lxc-ht`, Claude). Gemergt am 05.11.
- [x] Word (.docx) und E-Mail (.eml) laden wie PDF, ohne neue Abhängigkeit; Knopf heißt jetzt „Datei laden“ ([PR #32](https://github.com/lxc-ht/LP7/pull/32), baut auf #30 auf, `lxc-ht`, Claude). Gemergt am 05.11. Demo einmal mit einer Word-Datei und einer E-Mail durchspielen.
- [x] Gewählte Kopfvariante B2 ohne Rahmen eingebaut: „Klar. Lokal.“ links, „Unter deiner Kontrolle.“ rechts vom Motiv. Mittlere Spalte auf Locs Wunsch allgemein „Vorschau für LLM“. Bestehende Browserprüfung bestanden, Desktop und Mobil visuell geprüft. Nur Oberfläche, Freigabeablauf unverändert; Branch `codex/slogan-ohne-rahmen` (`lxc-ht`, Codex UI).

- [x] PDF laden: Text aus digitalen PDFs lokal im Speicher auslesen und ins Textfeld setzen, per Knopf oder Ziehen; Scans werden gemeldet, nicht gelesen ([PR #30](https://github.com/lxc-ht/LP7/pull/30), `lxc-ht`, Claude). Gemergt am 05.11. Vortragsrechner einmal mit Netz starten, damit uv `pypdf` lädt.
- [x] Layout A umgesetzt: drei flexible Arbeitsbereiche per Hover, Klick und Tastatur; stabil beim Schreiben und Markieren. Äußere Kopfzeile, Schrittleiste und Footer entfernt, kleines Glasmotiv mittig. Browserprüfung mit fünf Breiten, Touch und reduzierter Bewegung sowie Durchlauf mit echtem Kern bestanden. Bestehende Formular-IDs und Freigabeablauf erhalten; IDs der ausdrücklich entfernten Leisten entfallen. Branch `codex/flexible-arbeitsbereiche` (`lxc-ht`, Codex UI).

- [x] Aus Presidio übernommen: Adressen ohne Straßenwort („Am Sande 12“) mit PLZ oder Kontextwort, HRB/HRA, USt-IdNr mit Prüfziffer, Reisepass und Führerschein ([PR #28](https://github.com/lxc-ht/LP7/pull/28)). Demo einmal mit „wohnhaft Am Sande 12, 21335 Lüneburg“ durchspielen.
- [x] Rückweg mit echtem Claude gemessen (claude.ai, Kopiermodus, Stand `2d3e971`, je ein neuer Chat, Aufgabe: „Fass den Fall in fünf Sätzen zusammen und entwirf eine kurze Antwort an die betroffene Person.“): **16 von 16 Platzhaltern, die Claude benutzt hat, kamen heil zurück, in 2 Testtexten** (Kündigung: 7 von 11 benutzt, Unfall mit drei Personen: 9 von 13). Keine unbekannten, keine veränderten Platzhalter, keine Verwechslung der Personen. Nicht benutzte Platzhalter zählen nicht als Fehler. Claude schrieb eigene Lücken wie `[NAME]` und `[KANZLEI]`, LP7 lässt sie richtig stehen. Ein allein stehender Nachname kommt als ganzer Name zurück („Herr Oberdorf“ wird zu „Herr Jannik Oberdorf“, gewollte Folge von 722c4ff). Texte von Claudian, vorher nur auf Erkennung geprüft (`Phantom-create-1`).
- [x] Übermaskierung aus PR #22 behoben (`EU-VO 2016`, `+100.000 Euro`), letzte Lecks geschlossen: kurze Nachnamen, Aktenzeichen klein, Ausweis, Kundenkonto ([PR #27](https://github.com/lxc-ht/LP7/pull/27)).
- [x] Material C in der echten Pseudonymisierungsoberfläche umgesetzt: helle Karten, Farbrand am aktuellen Bereich, größere Texte und Icons, Kopiermodus Texte und Unsicher Legende. Element-IDs erhalten. Webtests, Browserprüfung mit fünf Breiten und echter Durchlauf mit lokalem GLiNER (Analyse, Freigabe, Kopieren, Rückübersetzung, erneute Sperre) bestanden; kein Claude Versand. Branch `codex/arbeitsoberflaeche-material-c` (`lxc-ht`, Codex UI).

- [x] Weitere Umgehungen geschlossen: Werte über Zeilenumbrüche, Passwörter, API-Keys, Handles ([PR #24](https://github.com/lxc-ht/LP7/pull/24)).
- [x] Dashboard poliert: lesbare Platzhalter, Legende zeigt alle erkannten Typen mit Anzahl, erledigte Schritte mit Haken, Verlauf bei abgeschnittenem Text. Element-IDs unverändert, keine externen Quellen, 173 Tests und Browserprüfung grün (PR #23, `Phantom-create-1`).
- [x] Start per Doppelklick mit `LP7 starten.command` umgesetzt und geprüft, Browser öffnet sich automatisch, Server bleibt auf diesem Rechner (PR #20, `Phantom-create-1`). Doppelklick im Finder am 05.11. getestet, bei laufender Demo kommt „LP7 läuft schon“.
- [x] Repo angelegt, beide haben Schreibrechte.
- [x] Kern gebaut: Erkennung, Maskierung, Freigabe, Senden, Rückübersetzung, CLI.
- [x] Weboberfläche gebaut und auf `main` gemergt.
- [x] Oberfläche im Browser gegen den echten Kern geprüft: Analysieren, Markieren, Zurücknehmen, Freigeben, Rückübersetzen.
- [x] Nachnamen allein werden mitmaskiert, wenn sie eindeutig zu einer Person gehören (722c4ff).
- [x] Pitch-Deck (9 Folien) liegt bei Paul, Folie 8 wartet noch auf die Messung.
- [x] „Kopieren“ gegen den echten Kern geklickt: In der Zwischenablage stehen nur Platzhalter.
- [x] Regex-Erkennung für Kennungen, Adressen und Anreden, Löschen der Zuordnung (PR #4, `lxc-ht`).
- [x] KENNUNG strenger: Steuer-ID ohne Bezeichner nur mit gültiger Prüfziffer, Steuernummer nur nach Bezeichner. Paragrafen, Beträge und Jahreszahlen bleiben stehen (`Phantom-create-1`).
- [x] Neues Design und Zählertext „Versand nur nach deiner Freigabe“ gemergt (PR #3), Abläufe gegen den echten Kern geprüft.
- [x] Layout passt auf dem Laptop ohne Scrollen auf den Bildschirm (PR #5). Auf einem echten Beamer noch nicht geprüft.
- [x] Namen in jeder Schrift vollständig maskiert, weniger Falschtreffer bei ADRESSE und Anrede, abgeschnittene Antworten gekennzeichnet (PR #6).
- [x] Erfundene Kennungen in allen drei Beispieltexten (Aktenzeichen, Mandanten-, Versicherten-, Patientennummer, Steuer-ID, Steuernummer). Durchlauf mit GLiNER: alle maskiert, Rückübersetzung löst alle Platzhalter auf (`Phantom-create-1`).
- [x] `KENNUNG` in der Oberfläche: Chip-Farbe und Markier-Menü (PR #7, `lxc-ht`), gemergt.
- [x] Zuordnung wird auch bei SIGTERM und geschlossenem Terminal gelöscht, Warnung bei teilweiser Überlappung (PR #9).
- [x] Erkennungslücken geschlossen: lange Absätze, E-Mails mit Umlaut, Namensvarianten (PR #8).
- [x] Review-Fix zu PR #8: Namensteile mehrdeutig, Schreibweisen nur als großgeschriebenes Wort (PR #11).
- [x] Rückübersetzung warnt bei Platzhaltern, die nur für einen Namensteil standen, unbekannte Sitzung meldet einen fertigen Satz (PR #16).
- [x] Entscheidung: ohne API-Key. Weitergabe nur durch Kopieren, unsichere Stellen werden in der Prüfung markiert (PR #17).
- [x] Hackathon-Track geklärt: Einreichen geht klar.
- [x] Dashboard im Lime-Soda-Stil des UI-Kits (PR #19, `Phantom-create-1`), gemergt.
- [x] Start per Doppelklick mit `LP7 starten.command` (PR #20, `Phantom-create-1`), gemergt. Echter Doppelklick im Finder steht noch aus.
- [x] Datum ohne Jahr, IBAN in Kleinbuchstaben, Dateirechte der Zuordnung (PR #12), Banner im README (PR #10).
- [x] Umgehungen des Kerns geschlossen: Token-Grenze des Modells, Unicode, Platzhalter-Kollision, Formate (PR #22, `lxc-ht`), gemergt. 176 Tests mit echtem Modell und `web.test_app` bestanden. Noch offen: siehe `BACKLOG.md`.

## Vor dem Veröffentlichen

Das Repo ist zunächst privat und soll später öffentlich werden. Dann gilt:

- Keine Schlüssel, Passwörter oder `.env` Dateien committen. Die `.gitignore` deckt die üblichen Fälle ab.
- Den Git Verlauf auf versehentlich committete Geheimnisse prüfen, denn gelöschte Dateien bleiben in der Historie sichtbar.
- Stand 05.11. (Claudian): Verlauf durchsucht. Kein echter Schlüssel gefunden, nur ein erfundener Testwert in `tests/test_umgehungen.py`. Nie committet: `.env`, `data/`, SQLite-Dateien. Im Verlauf stehen die Commit-Mailadressen beider Autoren, das ist bei öffentlichen Repos normal.
- [x] Lizenz: MIT, von beiden am 05.11. beschlossen, liegt als `LICENSE` im Repo. Der Presidio-Hinweis in der README muss bleiben.
- [ ] Erst am 06.11., nicht vorher: Repo öffentlich schalten (nur `lxc-ht` als Owner): Settings → General → Danger Zone → Change visibility. Dabei die Beschreibung „Datenverschlüsselung“ ersetzen, zum Beispiel durch „Pseudonymisierung: KI nutzen, Daten behalten.“
