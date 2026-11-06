# Backlog Weboberfläche

## Wunsch an den Kern

- Abweichung vom Vertrag: Bei unbekannter Sitzung kommt ein `KeyError`, die Oberfläche zeigt dann `'Unbekannte Sitzung: nope'` mit Anführungszeichen. Das passiert zum Beispiel, wenn die Seite nach einem Serverneustart offen bleibt. Bitte einen fertigen deutschen Satz liefern, auch bei leerem Begriff oder unbekanntem Platzhalter.
- Abweichung vom Vertrag: Der Text von `NoApiKeyError` ist für die CLI geschrieben ("Der freigegebene Text liegt in der Zwischenablage ... beende mit einer Zeile, auf der nur END steht"). Im Web stimmt das nicht. Die Oberfläche zeigt ihn nur, wenn der Key nach dem Seitenaufruf wegfällt. Bitte neutral formulieren und den CLI-Hinweis in die CLI verlegen.
- `RestoreResult.warnings` wiederholt, was schon in `unknown`, `changed` und `missing` steht. Die Oberfläche filtert das heraus. Bitte dort nur zusätzliche Hinweise liefern.
- Die Oberfläche markiert Text nur zwischen zwei Platzhaltern. `add_manual` sollte ablehnen, wenn der Begriff im maskierten Text nicht vorkommt.
- `replacements` sollte jedes einzelne Vorkommen enthalten, denn daraus entstehen die Chips und der Zähler.
- Adresse ohne Straßenwort bleibt stehen: In „wohnhaft Am Sande 12, 21335 Lüneburg“ wird nur „21335 Lüneburg“ ersetzt, „Am Sande 12“ geht mit raus (Stand `dcf069b`, gefunden von Paul/Claudian am 05.11.). Gleiches Muster: Am Markt, An der Kirche, Im Grund.

## Für später

- Englischer Modus (Umschalter DE / EN): Deutsch bleiben noch alle Texte aus dem Kern und vom Server. Das sind die Hinweise in `warnings` (etwa Namensteil-Warnungen, „kommt im Text nicht vor“, beim Testmodus „Die Attrappe erkennt nur E-Mails …“), die Begründungen unsicherer Stellen im Tooltip, Fehlermeldungen der API (Leck, Freigabe passt nicht, Sitzung unbekannt, Dateifehler bei PDF, Word und E-Mail, Modell lädt nicht) und die Typ-Namen in Platzhaltern und im Typ-Menü (PERSON, FIRMA, ADRESSE …). Lösung später: der Kern liefert Schlüssel statt fertiger Sätze, oder die Oberfläche übersetzt bekannte Sätze.
- Deutscher Zähler sagt bei einer Ersetzung „1 Angaben ersetzt“. Im Umschalter-PR bewusst unverändert gelassen, damit die deutsche Seite gleich bleibt; Englisch sagt schon „1 detail replaced“.

- Der Zähler "0 davon verlassen den Rechner" gilt nur für erkannte Angaben. Eine übersehene Angabe geht nach der Freigabe mit raus. Vorschlag: "{n} sensible Angaben ersetzt · Versand nur nach deiner Freigabe". Der Text steht wörtlich im Auftrag, deshalb ist er noch nicht geändert.
- Datei laden kann PDF, .docx und .eml. Offen: Scans (OCR), Outlook .msg (bräuchte eine zusätzliche Bibliothek), Anhänge einer E-Mail, alte .doc-Dateien.
- Word-Tabellen: Jede Zelle wird eine eigene Zeile. Zellen einer Zeile mit Tabulator verbinden, dann bleibt „IBAN“ neben dem Wert.
- Markieren per Tastatur, bisher geht es nur mit der Maus.
- Freigaben liegen im Speicher des Servers und werden nie aufgeräumt. Für die Demo reicht das.
- `web/test_ui.py` könnte die Höhe der Kopfzeile auf 1440 × 900 und 1280 × 800 mitprüfen (höchstens 130 px, kein senkrechtes Scrollen). Bisher nur von Hand gemessen.
