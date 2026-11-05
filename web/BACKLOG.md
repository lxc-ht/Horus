# Backlog Weboberfläche

## Wunsch an den Kern

- `add_manual`, `remove` und `get` haben im Vertrag keine eigene Ausnahme. Die Oberfläche zeigt `str(e)` unverändert an. Bitte auch bei unbekannter Sitzung, leerem Begriff oder unbekanntem Platzhalter einen fertigen deutschen Satz liefern, kein `KeyError`.
- Die Oberfläche markiert Text nur zwischen zwei Platzhaltern. `add_manual` sollte ablehnen, wenn der Begriff im maskierten Text nicht vorkommt.
- `replacements` sollte jedes einzelne Vorkommen enthalten, denn daraus entstehen die Chips und der Zähler.

## Für später

- Der Zähler "0 davon verlassen den Rechner" gilt nur für erkannte Angaben. Eine übersehene Angabe geht nach der Freigabe mit raus. Vorschlag: "{n} sensible Angaben ersetzt · Versand nur nach deiner Freigabe". Der Text steht wörtlich im Auftrag, deshalb ist er noch nicht geändert.
- PDF und Word Upload.
- Markieren per Tastatur, bisher geht es nur mit der Maus.
- Freigaben liegen im Speicher des Servers und werden nie aufgeräumt. Für die Demo reicht das.
