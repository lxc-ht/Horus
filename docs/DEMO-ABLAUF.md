# Demo-Ablauf für den Pitch

Drehbuch für die Live-Demo am Vortragsrechner, etwa drei Minuten. Alle Texte sind erfunden.

## Am Abend vorher, mit Netz

1. `git pull`, dann einmal `LP7 starten.command` per Doppelklick. uv lädt dabei fehlende Pakete (seit PR #30 auch `pypdf`).
2. Einmal „Beispiel laden“ → „Text analysieren“. Damit liegt das Erkennungsmodell im Cache. Erst danach funktioniert die Demo ohne Netz.
3. LP7 beenden (ctrl+C), WLAN ausschalten, erneut starten und noch einmal analysieren. Klappt das, ist der Rechner bereit.
4. In Claude (claude.ai) angemeldet bleiben, einen leeren Chat offen lassen.

## Direkt vor dem Auftritt

- LP7 starten und **einmal analysieren**, auch wenn das Modell vorgeladen wird. Der erste Lauf ist der langsamste.
- Browser auf Vollbild, Zoom 100 %, keine anderen Tabs mit echten Daten.
- Benachrichtigungen aus (Fokus-Modus), damit kein Pop-up über die Oberfläche fährt.
- Prüfen, dass oben **kein** gelbes Band „Testmodus: Attrappe aktiv“ steht.

## Ablauf

| Schritt | Klick | Was wir sagen |
|---|---|---|
| 1 | „Beispiel laden“ | „Ein typischer Fall aus einer Kanzlei: Kündigung, Name, Adresse, IBAN, Aktenzeichen. Alles erfunden.“ |
| 2 | „Text analysieren“ | „Das läuft komplett auf diesem Laptop. Kein Byte geht bisher raus.“ |
| 3 | In der Mitte auf einen Platzhalter zeigen | „Aus Erika Musterfrau wird `[PERSON_1]`. Die Zuordnung bleibt lokal in einer Datei, die nur dieser Benutzer lesen darf.“ |
| 4 | Auf die gelbe Stelle „Vorgang 4471-B“ zeigen | „Wo LP7 unsicher ist, markiert es gelb. Der Mensch entscheidet.“ Dann „4471-B“ markieren → Typ KENNUNG. |
| 5 | „Vorschau freigeben“ | „Erst jetzt darf etwas raus, und zwar genau dieser Text. Ändert sich ein Zeichen, ist die Freigabe ungültig.“ |
| 6 | „Kopieren“, in Claude einfügen, senden | „Claude sieht nur Platzhalter.“ |
| 7 | Antwort kopieren, in „Deine Antwort“ einfügen, „Lokal zurückübersetzen“ | „Die echten Namen kommen erst hier zurück, auf unserem Rechner. Grün heißt: sicher zugeordnet.“ |

Kernsatz zum Schluss: **„Presidio erkennt. LP7 kontrolliert, was rausgeht.“**

## Wenn etwas schiefgeht

- **Claude antwortet nicht oder kein Netz:** Schritt 6 überspringen und eine vorbereitete Antwort einfügen, zum Beispiel:
  `Sehr geehrter Herr [PERSON_2], im Namen von [PERSON_1] widersprechen wir der Kündigung vom [DATUM_1].`
  Die Nummern vorher in der echten Vorschau prüfen, sie hängen von der Erkennung ab.
- **Analyse dauert sehr lange:** Das Modell lädt noch. Weiterreden („Das Modell läuft lokal, deshalb braucht der erste Lauf einen Moment“) und warten, nicht neu klicken.
- **„LP7 läuft schon“ beim Doppelklick:** Ist in Ordnung, der Browser zeigt die laufende Instanz.
- **Seite zeigt „Diese Sitzung ist nicht mehr bekannt“:** Der Server wurde neu gestartet. Einmal „Text analysieren“ klicken.
- **Notfall ohne Modell:** `HARNESS_FAKE=1` startet die Attrappe. Sie erkennt nur E-Mails und eine feste Namensliste und zeigt das gelbe Testmodus-Band. Nur verwenden, wenn gar nichts anderes geht, und es offen sagen.

## Fragen, auf die wir vorbereitet sind

- **Warum kein lokales Modell für die Antwort?** Steht im Jury-Fragen-Dokument. Kurz: Die starken Modelle laufen nicht auf einem Kanzlei-Laptop; LP7 trennt deshalb, was lokal bleiben muss (Namen, Zuordnung), von dem, was ein starkes Modell braucht (den Fall).
- **Was, wenn der Kontext die Person verrät?** „Pseudonymisierung ist keine Anonymisierung. Deshalb gibt es die Prüfung vor jeder Freigabe, und LP7 zeigt typische verräterische Stellen an.“
- **DSGVO?** „LP7 macht niemanden automatisch DSGVO-konform. Es sorgt dafür, dass nur der geprüfte, maskierte Text den Rechner verlässt.“ Nie „konform“ oder „anonym“ versprechen.
- **Zahlen:** Nur die aus dem Projektstand, mit ihrer Einschränkung (selbst geschriebene Testtexte, kein Beleg für echte Akten).
