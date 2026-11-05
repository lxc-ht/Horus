# Backlog Weboberfläche

## Wunsch an den Kern

Erledigt und deshalb entfernt (geprüft am 05.11.): unbekannte Sitzung meldet einen fertigen Satz, `replacements` enthält jedes Vorkommen, „Am Sande 12“ wird seit PR #28 ersetzt.

- Abweichung vom Vertrag: Der Text von `NoApiKeyError` ist für die CLI geschrieben ("Der freigegebene Text liegt in der Zwischenablage ... beende mit einer Zeile, auf der nur END steht"). Im Web stimmt das nicht. Die Oberfläche zeigt ihn nur, wenn der Key nach dem Seitenaufruf wegfällt. Bitte neutral formulieren und den CLI-Hinweis in die CLI verlegen.
- `RestoreResult.warnings` wiederholt, was schon in `unknown`, `changed` und `missing` steht. Die Oberfläche filtert das heraus. Bitte dort nur zusätzliche Hinweise liefern.
- Die Oberfläche markiert Text nur zwischen zwei Platzhaltern. `add_manual` sollte ablehnen, wenn der Begriff im maskierten Text nicht vorkommt. Stand 05.11.: Der Kern lehnt nicht ab, liefert aber den Hinweis „… kommt im Text nicht vor, es wurde nichts maskiert.“ in `warnings`.

## Für später

- Der Zähler "0 davon verlassen den Rechner" gilt nur für erkannte Angaben. Eine übersehene Angabe geht nach der Freigabe mit raus. Vorschlag: "{n} sensible Angaben ersetzt · Versand nur nach deiner Freigabe". Der Text steht wörtlich im Auftrag, deshalb ist er noch nicht geändert.
- Datei laden kann PDF, .docx und .eml. Offen: Scans (OCR), Outlook .msg (bräuchte eine zusätzliche Bibliothek), Anhänge einer E-Mail, alte .doc-Dateien.
- Word-Tabellen: Jede Zelle wird eine eigene Zeile. Zellen einer Zeile mit Tabulator verbinden, dann bleibt „IBAN“ neben dem Wert.
- Markieren per Tastatur, bisher geht es nur mit der Maus.
- Freigaben liegen im Speicher des Servers und werden nie aufgeräumt. Für die Demo reicht das.
