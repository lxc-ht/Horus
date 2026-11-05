# LP7

Pseudonymisierungs-Harness: KI nutzen, ohne personenbezogene Daten aus der Hand zu geben.

![LP7: Analysieren, Vorschau und Ausgabe. Klar. Lokal. Unter deiner Kontrolle.](web/assets/lp7-banner.png)

**UI Kit:** [Icons, Komponenten und drei klickbare Design Demos](web/ui-kit/README.md). Der vollständige Quellcode liegt unter `web/ui-kit/` und kann gemeinsam weiterentwickelt werden.

## Projektstand

Hier stimmen sich alle ab, Menschen und Agenten. Agenten können nicht direkt miteinander sprechen und sehen nur, was gepusht ist.

**So nutzen wir diesen Abschnitt**

1. Vor der Arbeit: `git pull`, dann diesen Abschnitt lesen.
2. Vor dem Start: Aufgabe mit deinem Namen unter „In Arbeit“ eintragen und pushen, damit niemand dasselbe baut.
3. Nach der Arbeit: Aufgabe nach „Erledigt“ verschieben, neue Aufgaben ergänzen und pushen.
4. Jede Aufgabe steht in einer eigenen Zeile. Das hält Merge-Konflikte klein.

**Ziel**

Eine Demo für die Jury beim Leuphana AI Hackathon: Team-Pitch am Freitag, 6. November 2026. Sie zeigt, dass eine Kanzlei Claude nutzen kann und nur der geprüfte, maskierte Text den Rechner verlässt.

**In Arbeit**



**Nächste Aufgaben**

Kern (`Phantom-create-1`):

- [ ] Falsche Rückübersetzung verhindern, nicht nur melden: Stand ein Platzhalter nur für einen Namensteil wie „Antrag“, warnt der Bericht seit PR #16, der falsche Text bleibt aber. Nach Herr, Frau, Dr. oder Prof. kommt bewusst keine Warnung.
- [ ] Wünsche aus `web/BACKLOG.md` unter „Wunsch an den Kern“ umsetzen.

Oberfläche (`lxc-ht`, `web/static/index.html`):

- [ ] Die aktualisierte echte Arbeitsoberfläche mit Paul am Vortragsrechner durchspielen.


Beide:

- [ ] Demo auf dem Vortragsrechner durchspielen und das Modell vorher einmal laden.
- [ ] Pitch vorbereiten, auch für diese Fragen: Warum kein lokales Modell? Was, wenn der Kontext die Person verrät? Was ist mit der DSGVO?
  - DSGVO, Vorschlag: „LP7 macht niemanden automatisch DSGVO-konform. Aber es sorgt dafür, dass nur der geprüfte, maskierte Text den Rechner verlässt und die Zuordnung lokal bleibt. Das senkt das Risiko deutlich und ist der technische Baustein. Vertrag mit dem Anbieter und Prüfung durch den Menschen bleiben Pflicht.“
  - Falls jemand nach Anonymisierung fragt, zum Beispiel wie bei Bildern: „Bilder lassen sich durch künstliche Gesichter weitgehend entschärfen, bei Text bleibt der Zusammenhang. Deshalb versprechen wir keine Anonymität. Wir zeigen dem Menschen genau, was rausgeht.“
  - Nicht versprechen: „DSGVO-konform“ oder „anonym“. Rechtlich ist das noch nicht geprüft.
  - Messung für den Pitch (Stand `a4e1dbe`, Regex und GLiNER): 87 von 89 Angaben in 22 kurzen, erfundenen Texten vollständig ersetzt, nur mit Regex 37 von 89. Die Texte hat der Agent selbst geschrieben, der den Code kannte. Das ist also kein Beleg für echte Akten und keine Erkennungsrate. Nicht als „98 % Schutz“ zeigen.
  - Bekannte Grenzen aus derselben Prüfung: Stadt „Essen“ blieb in einem längeren Satz stehen, „Kundenkonto 88213-44“ und „Ausweis L01X00T47“ ebenso, „im Winter“ wurde bei einer Person „Rosa Winter“ zum Namen. „Die einzige Kinderärztin im Ort“ findet keine Erkennung.

**Erledigt**

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

**Demo starten**

Auf dem Mac: Doppelklick auf `LP7 starten.command`. Der Browser öffnet sich, das Terminalfenster bleibt offen, solange LP7 läuft.

Oder im Terminal:

```bash
uv sync
uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Danach http://127.0.0.1:8000 öffnen.

## Vor dem Veröffentlichen

Das Repo ist zunächst privat und soll später öffentlich werden. Dann gilt:

- Keine Schlüssel, Passwörter oder `.env` Dateien committen. Die `.gitignore` deckt die üblichen Fälle ab.
- Den Git Verlauf auf versehentlich committete Geheimnisse prüfen, denn gelöschte Dateien bleiben in der Historie sichtbar.

## Pseudonymisierungs-Harness

Kanzleien, Arztpraxen und Steuerbüros wollen KI wie Claude nutzen, dürfen aber keine personenbezogenen Daten auf fremde Server geben. Der Harness läuft lokal:

1. Er erkennt sensible Angaben in einem Text (Namen, Firmen, Adressen, Orte, E-Mail, Telefon, IBAN, Datum, Kennungen wie Steuer-ID oder Aktenzeichen) und ersetzt sie durch konsistente Platzhalter wie `[PERSON_1]` oder `[FIRMA_1]`.
2. Die Zuordnung Platzhalter → Original speichert er in einer lokalen SQLite-Datenbank, gültig nur für diese eine Sitzung.
3. Der Mensch prüft den maskierten Text, maskiert bei Bedarf nach oder nimmt Ersetzungen zurück und gibt ihn ausdrücklich frei.
4. Erst genau diese freigegebene Fassung geht an Claude. Ändert sich danach etwas, ist die Freigabe ungültig.
5. Die Antwort wird lokal zurückübersetzt. Was sich nicht eindeutig zuordnen lässt, wird gemeldet, nicht geraten.

### Was das Werkzeug nicht ist

- **Pseudonymisierung ist keine Anonymisierung.** Auch ohne Namen kann der Zusammenhang eine Person verraten („die einzige Kinderärztin in Ort X“, eine seltene Diagnose, ein bekannter Rechtsstreit). Deshalb ist die menschliche Prüfung vor jeder Freigabe Pflicht.
- Die Erkennung ist nicht vollständig. Ein Modell übersieht Namen, Regex-Muster decken nicht jedes Format ab. Der Leck-Check fängt nur Werte, die der Harness schon kennt.
- Das Werkzeug macht einen Prozess nicht automatisch DSGVO-konform. Es ist ein technischer Baustein, der die Prüfung durch einen Menschen unterstützt.

### Bekannte Eigenheiten

- **Nachnamen und Vornamen allein werden mitmaskiert.** Ist „Erika Musterfrau“ als `[PERSON_1]` erkannt, wird aus „Frau Musterfrau“ „Frau [PERSON_1]“. Das gilt für Namensteile ab 3 Zeichen, nur als ganzes Wort („Musterfrauenverband“ bleibt stehen) und nur, wenn der Teil zu genau einer Person der Sitzung gehört. Teilen sich zwei Personen einen Nachnamen („Max Mustermann“, „Erika Mustermann“), bleibt „Mustermann“ allein stehen und der Harness warnt mit beiden Platzhaltern.
- **Die Rückübersetzung setzt immer den vollen Namen ein.** Aus „Frau [PERSON_1]“ in der Antwort wird „Frau Erika Musterfrau“, nicht „Frau Musterfrau“. Das ist so gewollt: Der Platzhalter steht für die Person, nicht für die Schreibweise, und ein voller Name ist in der lokalen Antwort unschädlich.

### Schnellstart

```bash
brew install uv
uv sync
uv run pytest
uv run python -m harness run examples/kanzlei.txt
```

Ohne API-Key (siehe `.env.example`) läuft die CLI im Kopier-Modus: Der freigegebene Text landet in der Zwischenablage, die Antwort fügt man von Hand wieder ein.

### Aufbau

- `src/harness/api.py` – der Vertrag, gegen den die Weboberfläche (`web/`) programmiert.
- `detect.py` (Regex + GLiNER), `vault.py` (SQLite), `mask.py`, `gate.py` (Freigabe und Leck-Check), `cloud.py` (Claude), `restore.py`, `cli.py`.
- `examples/` – vollständig erfundene Beispieltexte.
