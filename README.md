# LP7

Datenverschlüsselung

## Ziel

Daten sollen zwischen KIs verschlüsselt ausgetauscht werden, damit eine KI keinen Zugriff auf die öffentlichen Rohdaten hat.

## Status

Das Repo ist zunächst privat und soll später öffentlich werden.

Vor dem Veröffentlichen gilt:

- Keine Schlüssel, Passwörter oder `.env` Dateien committen. Die `.gitignore` deckt die üblichen Fälle ab.
- Den Git Verlauf auf versehentlich committete Geheimnisse prüfen, denn gelöschte Dateien bleiben in der Historie sichtbar.

## Pseudonymisierungs-Harness

Kanzleien, Arztpraxen und Steuerbüros wollen KI wie Claude nutzen, dürfen aber keine personenbezogenen Daten auf fremde Server geben. Der Harness läuft lokal:

1. Er erkennt sensible Angaben in einem Text (Namen, Firmen, Adressen, Orte, E-Mail, Telefon, IBAN, Datum) und ersetzt sie durch konsistente Platzhalter wie `[PERSON_1]` oder `[FIRMA_1]`.
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

- `src/harness/api.py` – der Vertrag, gegen den die Weboberfläche (`web/`, eigener Branch) programmiert.
- `detect.py` (Regex + GLiNER), `vault.py` (SQLite), `mask.py`, `gate.py` (Freigabe und Leck-Check), `cloud.py` (Claude), `restore.py`, `cli.py`.
- `examples/` – vollständig erfundene Beispieltexte.
