# LP7 – KI nutzen. Daten behalten.

LP7 ersetzt Namen, Adressen, IBANs und andere sensible Angaben in einem Text durch Platzhalter wie `[PERSON_1]`, bevor er an eine KI geht. Die Antwort setzt LP7 danach wieder mit den echten Angaben zusammen. Alles läuft auf dem eigenen Rechner, und nichts geht raus, was ein Mensch nicht vorher geprüft und freigegeben hat.

Gedacht für Kanzleien, Arztpraxen und Steuerbüros, die Claude oder einen anderen Chatbot nutzen wollen, aber keine Mandanten- oder Patientendaten auf fremde Server geben dürfen.

![LP7: Analysieren, Vorschau und Ausgabe. Klar. Lokal. Unter deiner Kontrolle.](web/assets/lp7-banner.png)

## So funktioniert es

1. **Text einfügen.** Einen Brief, eine E-Mail oder einen Sachverhalt.
2. **Analysieren.** LP7 erkennt Personen, Firmen, Adressen, Orte, E-Mail, Telefon, IBAN, Datum und Kennungen wie Aktenzeichen oder Steuer-ID und ersetzt sie durch Platzhalter. Die Zuordnung bleibt lokal.
3. **Prüfen und freigeben.** Du siehst genau den Text, der rausgehen würde. Unsichere Stellen sind gelb markiert, Übersehenes markierst du selbst, falsche Treffer nimmst du mit × zurück.
4. **Kopieren und fragen.** Den freigegebenen Text kopierst du selbst in Claude oder einen anderen Chatbot. LP7 sendet nichts automatisch und braucht keinen API-Schlüssel.
5. **Zurückübersetzen.** Die Antwort fügst du wieder ein. LP7 setzt die echten Angaben ein und meldet alles, was es nicht eindeutig zuordnen kann, statt zu raten.

![Die Arbeitsoberfläche von LP7](web/assets/arbeitsoberflaeche-material-c.png)

## Installation

Getestet auf macOS. Beim ersten Start lädt LP7 Python-Pakete und das Erkennungsmodell aus dem Internet. Python und Pakete belegen danach 5,8 GB, das Laden dauerte 7 Minuten (gemessen auf Linux in der Cloud, dort mit Grafikkarten-Paketen für torch; auf macOS nicht gemessen). Größe und Ladezeit des Erkennungsmodells sind nicht gemessen.

**1. uv installieren** (einmalig, im Terminal):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**2. LP7 herunterladen:** oben auf dieser Seite „Code“ → „Download ZIP“ und entpacken. Oder mit Git:

```bash
git clone https://github.com/lxc-ht/LP7.git
```

**3. Starten:** Doppelklick auf `LP7 starten.command`. Der Browser öffnet sich mit http://127.0.0.1:8000. Das Terminalfenster bleibt offen, solange LP7 läuft. Zum Beenden ctrl+C drücken oder das Fenster schließen.

Blockiert macOS das Öffnen, weil die Datei aus dem Internet kommt: Systemeinstellungen → Datenschutz & Sicherheit → „Trotzdem öffnen“.

**Ohne Doppelklick**, zum Beispiel auf Windows oder Linux (dort nicht getestet), im LP7-Ordner:

```bash
uv sync
uv run --with-requirements web/requirements.txt uvicorn web.app:app --host 127.0.0.1 --port 8000
```

Die Oberfläche ist nur auf diesem Rechner erreichbar (127.0.0.1), nicht im Netzwerk.

## Was LP7 nicht ist

- **Pseudonymisierung ist keine Anonymisierung.** Auch ohne Namen kann der Zusammenhang eine Person verraten („die einzige Kinderärztin in Ort X“, eine seltene Diagnose, ein bekannter Rechtsstreit). Deshalb ist die menschliche Prüfung vor jeder Freigabe Pflicht.
- Die Erkennung ist nicht vollständig. Ein Modell übersieht Namen, Regex-Muster decken nicht jedes Format ab. Der Leck-Check fängt nur Werte, die der Harness schon kennt.
- Das Werkzeug macht einen Prozess nicht automatisch DSGVO-konform. Es ist ein technischer Baustein, der die Prüfung durch einen Menschen unterstützt.
- Keine Rechtsberatung. Ob und wie ihr KI mit Mandanten- oder Patientendaten nutzen dürft, klärt ihr mit eurer Datenschutzberatung.

## Bekannte Eigenheiten

- **Nachnamen und Vornamen allein werden mitmaskiert.** Ist „Erika Musterfrau“ als `[PERSON_1]` erkannt, wird aus „Frau Musterfrau“ „Frau [PERSON_1]“. Das gilt für Namensteile ab 3 Zeichen, nur als ganzes Wort („Musterfrauenverband“ bleibt stehen) und nur, wenn der Teil zu genau einer Person der Sitzung gehört. Teilen sich zwei Personen einen Nachnamen („Max Mustermann“, „Erika Mustermann“), bleibt „Mustermann“ allein stehen und der Harness warnt mit beiden Platzhaltern.
- **Die Rückübersetzung setzt immer den vollen Namen ein.** Aus „Frau [PERSON_1]“ in der Antwort wird „Frau Erika Musterfrau“, nicht „Frau Musterfrau“. Das ist so gewollt: Der Platzhalter steht für die Person, nicht für die Schreibweise, und ein voller Name ist in der lokalen Antwort unschädlich.

## Getestet

- Rückweg mit echtem Claude (claude.ai, Kopiermodus, 05.11.2026): 16 von 16 Platzhaltern, die Claude in seinen Antworten benutzt hat, kamen heil zurück, in 2 erfundenen Testtexten. Keine Person wurde verwechselt. Zwei Texte sind eine Stichprobe, kein Beweis.
- Installation frisch durchgespielt (05.11.2026, Linux in der Cloud, leerer Klon und leere Caches): Pakete laden, Server starten und 213 Tests liefen durch. Das Erkennungsmodell ließ sich dort nicht laden, weil die Umgebung Hugging Face sperrt; dieser Schritt ist nicht geprüft.
- Die Erkennung ist mit erfundenen Texten geprüft, nicht mit echten Akten. Eine Erkennungsrate für echte Dokumente gibt es noch nicht.

## Für Entwicklerinnen und Entwickler

```bash
uv sync
uv run pytest              # ohne Netz, ohne Modell-Download
uv run pytest -m slow      # zusätzlich mit dem GLiNER-Modell
uv run python -m harness run examples/kanzlei.txt   # Kommandozeile
```

Ohne API-Key (siehe `.env.example`) läuft die Kommandozeile im Kopiermodus: Der freigegebene Text landet in der Zwischenablage, die Antwort fügt man von Hand wieder ein. Die Weboberfläche und ihr Testmodus sind in [`web/README.md`](web/README.md) beschrieben, Icons und Komponenten im [UI Kit](web/ui-kit/README.md).

**Aufbau**

- `src/harness/api.py` – der Vertrag, gegen den die Weboberfläche (`web/`) programmiert.
- `detect.py` (Regex + GLiNER), `vault.py` (SQLite), `mask.py`, `gate.py` (Freigabe und Leck-Check), `cloud.py` (Claude), `restore.py`, `cli.py`.
- `examples/` – vollständig erfundene Beispieltexte.

Die Regeln für Beiträge und Agenten stehen in [`CLAUDE.md`](CLAUDE.md), der Arbeitsstand des Teams in [`PROJEKTSTAND.md`](PROJEKTSTAND.md).

## Entstehung

Gebaut beim Leuphana AI Hackathon 2026 von [lxc-ht](https://github.com/lxc-ht) und [Phantom-create-1](https://github.com/Phantom-create-1).

### Danksagung

Einige deutsche Erkennungsmuster (Handelsregister, USt-IdNr mit Prüfziffer, Bezeichner für Reisepass und Führerschein) und die Idee, unsichere Muster über Kontextwörter abzusichern, stammen aus [Microsoft Presidio](https://github.com/data-privacy-stack/presidio), MIT-Lizenz, Copyright (c) Presidio Contributors.

## Lizenz

[MIT](LICENSE): Du darfst LP7 nutzen, verändern und weitergeben, auch kommerziell, solange der Lizenzhinweis erhalten bleibt. Ohne Gewähr. Die aus Microsoft Presidio übernommenen Muster stehen ebenfalls unter MIT (siehe Danksagung).
