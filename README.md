# LP7

Pseudonymisierungs-Harness: KI nutzen, ohne personenbezogene Daten aus der Hand zu geben.

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

- Datum ohne Jahr, Monat und Jahr, IBAN in Kleinbuchstaben, Dateirechte der Zuordnung. Nur `detect.py` und `vault.py` (Branch `kern/datum-iban-rechte`, `lxc-ht`).
- Erkennungslücken im Kern (lange Absätze, E-Mails mit Umlaut, Namensvarianten): [PR #8](https://github.com/lxc-ht/LP7/pull/8) wartet auf den Merge (`lxc-ht`).

**Nächste Aufgaben**

Kern (`Phantom-create-1`):

- [ ] Falsche Rückübersetzung ohne Warnung: Meldet das Modell „Muellers Antrag“ als PERSON, wird jedes „Antrag“ zum selben Platzhalter. Aus „stellte den Antrag“ wird „stellte den Muellers Antrag“, der Bericht bleibt leer. Liegt schon auf `main`, PR #8 ändert das nicht.
- [ ] Wünsche aus `web/BACKLOG.md` unter „Wunsch an den Kern“ umsetzen.

Beide:

- [ ] Klären, ob das Projekt in unserem Hackathon-Track eingereicht werden darf.
- [ ] Echtes Senden an Claude mit API-Key in der `.env` testen. Das ist bisher ungetestet.
- [ ] Demo auf dem Vortragsrechner durchspielen und das Modell vorher einmal laden.
- [ ] Pitch vorbereiten, auch für diese Fragen: Warum kein lokales Modell? Was, wenn der Kontext die Person verrät? Was ist mit der DSGVO?

**Erledigt**

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

**Demo starten**

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
