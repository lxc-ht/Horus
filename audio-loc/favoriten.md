# Favoriten Sound – Horus-Pitch-Video

Stand 06.11.2026. Alle Quellen und Lizenzen stehen in `quellen-audio.csv`.

**Vorweg, ehrlich:** Pixabay, Mixkit und Freesound ließen sich von unserem Arbeitsrechner aus nicht herunterladen (Netz gesperrt), nur die Seiten lesen. Die Musik von Pixabay ist deshalb **noch nicht im Ordner**. Die fünf Links stehen in der CSV mit dem Dateinamen, unter dem sie abgelegt werden sollen. Ausgewählt habe ich sie nach Beschreibung, Tags, Länge und Downloadzahl, **nicht nach Gehör**. Bitte vor dem Schnitt reinhören.

Alle Soundeffekte und zwei Ersatz-Musikstücke habe ich selbst synthetisiert (Dateien mit `gen-`, Python + numpy + ffmpeg, Skripte in `gen-skripte/`). Damit gibt es keine Lizenzfrage. Geprüft habe ich, dass jede Datei lädt, Ton enthält und 48 kHz / 24 bit WAV ist, und die Spektren angesehen. Angehört habe ich sie nicht.

## Musik

| Kategorie | Favorit | Warum |
|---|---|---|
| Spannung | `musik-spannung-1.mp3` – „Trailer Pulse Teaser“ (BurtySounds, Pixabay, 0:44) | Laut Beschreibung genau das Gewünschte: pulsierende Synths, tickende Percussion, Bass-Hits, als Trailer gebaut; mit 2.561 Downloads die meistgeladene der Kandidaten. Nachteil: 44 s statt 50 s. |
| Auflösung | `musik-aufloesung-1.mp3` – „Soft Hopeful Piano“ (PaulYudin, Pixabay, 1:57) | Solo-Klavier, „gentle, hopeful, warm“, stark genutzt (9.655 Downloads). Die passende 10–15-s-Stelle muss jemand beim Anhören aussuchen. |
| Notnagel, falls nichts geladen werden kann | `gen-musik-spannung-1.wav` | Liegt schon im Ordner: exakt 110 BPM, baut sich über 52 s in Stufen auf (Kick ab 8,7 s, Snare ab 26,2 s, Arpeggio ab 34,9 s, Wirbel ab 48 s) und endet hart. Klingt aber schlicht synthetisch, nicht wie ein produzierter Trailer-Track. |

Alle drei Pixabay-Spannungs-Kandidaten und beide Klavier-Stücke sind laut Seite bei YouTube Content ID registriert. Für den Live-Pitch ist das egal; wird das Video später auf YouTube hochgeladen, kann ein Claim kommen (Lizenz bleibt gültig, der Claim lässt sich mit dem Pixabay-Nachweis anfechten). Ohne Content ID, falls das wichtig wird: „Blackout Protocol“ (cinematicacoustica, 2:54) https://pixabay.com/music/main-title-blackout-protocol-tech-thriller-modern-cyberpunk-intensity-366258/ und „Dark Electronic Pulse Background“ (Databend, 1:45) https://pixabay.com/music/electronic-dark-electronic-pulse-background-546935/ – beide kaum geladen (14 bzw. 264), also noch weniger einschätzbar.

## Soundeffekte (alle selbst synthetisiert)

| Kategorie | Favorit | Warum |
|---|---|---|
| hit | `gen-sfx-hit-1.wav` | 0,7 s, trocken, ohne Hall: passt am besten zu harten Schnitten im schnellen Takt. |
| whoosh | `gen-sfx-whoosh-2.wav` | 0,6 s kurz: bei vielen Schlagzeilen hintereinander nervt der lange Whoosh schneller. |
| riser | `gen-sfx-riser-2.wav` | 4 s, Tremolo wird schneller und Filter öffnet sich: mehr Sog vor der Stille als riser-1. |
| boom | `gen-sfx-boom-2.wav` | Einschlag plus Sub-Drop und Hallfahne, wirkt im Schwarz länger nach. Achtung: viel unter 60 Hz, auf Laptop-Lautsprechern kaum hörbar, im Saal über PA gut. |
| tippen | `gen-sfx-tippen-1.wav` | Ruhigeres Tippen mit Wortpausen, Einfügen und Klick am Ende bei ca. 4,9 s. Ehrlich: synthetisches Tippen klingt nie ganz echt; wer Zeit hat, nimmt 10 s echtes Tippen mit dem Handy auf. |
| senden | `gen-sfx-senden-1.wav` | 0,7 s, kurz und hell, wandert nach rechts raus. |
| glitch | `gen-sfx-glitch-2.wav` | Modem-artige Datentöne lesen sich sofort als „Daten unterwegs“, glitch-1 ist eher allgemeines Stottern. |
| puls | `gen-sfx-puls-1.wav` | Herzschlag 72 BPM, nahtlos loopbar, eindeutiger als der reine Sub-Puls. |
| tick | `gen-sfx-tick-1.wav` | Heller, kurzer Klick setzt sich besser gegen Musik und Stimme durch als der Holzklick. |
| ping | `gen-sfx-ping-1.wav` | Zwei Töne aufwärts wie eine Nachricht, aber erkennbar kein Apple- oder WhatsApp-Ton. |
| logo | `gen-sfx-logo-1.wav` | Klangschale mit Schwebung: ein einzelner warmer Ton, passt zu „ein einzelner Ton“ und zum Auge. logo-2 (Pad) ist die Wahl, falls es weicher sein soll. |

Bei den Effekten war nichts dabei, was ich als mittelmäßig aussortieren musste, aber auch keiner ist Studioqualität. Am schwächsten ist vermutlich `tippen`.
