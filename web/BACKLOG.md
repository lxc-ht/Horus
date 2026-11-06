# Backlog Weboberfläche

## Wunsch an den Kern

Erledigt und deshalb entfernt (geprüft am 05.11.): unbekannte Sitzung meldet einen fertigen Satz, `replacements` enthält jedes Vorkommen, „Am Sande 12“ wird seit PR #28 ersetzt.

- `RestoreResult.warnings` wiederholt, was schon in `unknown`, `changed` und `missing` steht. Die Oberfläche filtert das heraus. Bitte dort nur zusätzliche Hinweise liefern.
- Die Oberfläche markiert Text nur zwischen zwei Platzhaltern. `add_manual` sollte ablehnen, wenn der Begriff im maskierten Text nicht vorkommt. Stand 05.11.: Der Kern lehnt nicht ab, liefert aber den Hinweis „… kommt im Text nicht vor, es wurde nichts maskiert.“ in `warnings`.

## Für später

- Englischer Modus (Umschalter DE / EN): Deutsch bleiben noch alle Texte aus dem Kern und vom Server. Das sind die Hinweise in `warnings` (etwa Namensteil-Warnungen, „kommt im Text nicht vor“, beim Testmodus „Die Attrappe erkennt nur E-Mails …“), die Begründungen unsicherer Stellen im Tooltip, Fehlermeldungen der API (Leck, Freigabe passt nicht, Sitzung unbekannt, Dateifehler bei PDF, Word und E-Mail, Modell lädt nicht) und die Typ-Namen in Platzhaltern und im Typ-Menü (PERSON, FIRMA, ADRESSE …). Lösung später: der Kern liefert Schlüssel statt fertiger Sätze, oder die Oberfläche übersetzt bekannte Sätze.
- Deutscher Zähler sagt bei einer Ersetzung „1 Angaben ersetzt“. Im Umschalter-PR bewusst unverändert gelassen, damit die deutsche Seite gleich bleibt; Englisch sagt schon „1 detail replaced“.

- Der Zähler "0 davon verlassen den Rechner" gilt nur für erkannte Angaben. Eine übersehene Angabe geht nach der Freigabe mit raus. Vorschlag: "{n} sensible Angaben ersetzt · Versand nur nach deiner Freigabe". Der Text steht wörtlich im Auftrag, deshalb ist er noch nicht geändert.
- Datei laden kann PDF, .docx und .eml. PDF- und Word-Anhänge einer E-Mail werden mitgelesen. Offen: Scans (OCR), Outlook .msg (bräuchte eine zusätzliche Bibliothek), E-Mails als Anhang, alte .doc-Dateien.
- Markieren per Tastatur, bisher geht es nur mit der Maus.
- Freigaben liegen im Speicher des Servers und werden nie aufgeräumt. Für die Demo reicht das.
- `web/README.md` beschreibt unter „Arbeitsoberfläche“ noch das Glasmotiv zwischen „Klar. Lokal.“ und „Unter deiner Kontrolle.“, und der Screenshot `assets/arbeitsoberflaeche-material-c.png` zeigt die alte Kopfzeile. Nach dem Merge der Überschrift „Ask Anything, Reveal Nothing“ Text und Bild nachziehen.
- `web/test_ui.py` könnte die Höhe der Kopfzeile auf 1440 × 900 und 1280 × 800 mitprüfen (höchstens 130 px, kein senkrechtes Scrollen). Bisher nur von Hand gemessen.
