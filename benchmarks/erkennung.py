"""Reproduzierbare Stichprobe mit erfundenen, annotierten Texten."""

import os
import re
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from harness import api
from harness.detect import TYPES
from harness.mask import canonical

# Layouts wie nach dem Kopieren oder Import. Der Benchmark beginnt beim extrahierten Text.
DOCUMENTS = {
    "kanzlei": """Betreff: Rückfrage zum Mietvertrag
Mandantin: [[PERSON|Yara Albrecht]]
Anschrift: [[ADRESSE|Kranichweg 27, 23552 Lübeck]]
Aktenzeichen: [[KENNUNG|24 C 173/26]]
Bitte legen Sie den unterschriebenen Vertrag zur Akte.""",
    "arztpraxis": """Kurzbrief zum Kontrolltermin
Patientin: [[PERSON|Nora Valenti]]
Geburtsdatum: [[DATUM|03.02.1982]]
Patientennummer: [[KENNUNG|P-73451]]
Der Befund ist stabil. Nächste Kontrolle in drei Monaten.""",
    "steuerbuero": """Rückfrage zu Buchungsbelegen
Mandant: [[FIRMA|Fjordbogen Technik GmbH]]
Steuernummer: [[KENNUNG|21/815/60422]]
Kontakt: [[EMAIL|abrechnung.fjordbogen@example.org]]
Bitte prüfen, ob die Reisekosten bereits gebucht wurden.""",
    "tabelle": """Name\tKundenkonto\tKontakt
[[PERSON|Linh Nguyen]]\t[[KENNUNG|88213-44]]\t[[EMAIL|linh.nguyen@example.org]]
[[PERSON|Ruben Milani]]\t[[KENNUNG|99302-18]]\t[[EMAIL|r.milani@example.org]]""",
    "pdf_layout": """ÜBERWEISUNGSAUFTRAG
Empfänger: [[PERSON|Alina Teichmann]]
IBAN: [[IBAN|DE89 3704 0044 0532 0130 00]]
Verwendungszweck: Rückerstattung, 125,00 EUR
Datum: [[DATUM|18.04.2026]]""",
    "e_mail": """Von: [[PERSON|Amira Özdemir]] <[[EMAIL|amira.oezdemir@example.org]]>
An: [[PERSON|Malte Henning]] <[[EMAIL|malte.henning@example.org]]>
Hallo [[PERSON|Malte]],
ruf mich bei Rückfragen unter [[TELEFON|040 5550162]] an.""",
    "kurze_namen": """[[PERSON|Mai Le]] und [[PERSON|Minh Wu]] nahmen teil.
Frau [[PERSON|Le]] reicht die fehlenden Unterlagen ein. Herr [[PERSON|Wu]] prüft die Frist.""",
    "wortgleichheit": """[[PERSON|Rosa Winter]] beantragt eine Terminverschiebung.
Im Winter steht der Besprechungsraum nicht zur Verfügung.""",
    "ort_im_satz": """Das Gespräch findet nach Abstimmung mit dem Team in [[ORT|Essen]] statt.
Der Besprechungsraum ist im zweiten Stock.""",
    "english": """Dear [[PERSON|Oliver Finch]],
We received your request on [[DATUM|2 October 2026]]. Your client number is [[KENNUNG|C-26-0815]].
Please confirm your address at [[ADRESSE|14 Elm Street, Cambridge CB2 1TN]].""",
    "emoji": """📄 Für [[PERSON|Sofia Morante]] ist eine Kopie hinterlegt.
Rückfragen bitte an [[EMAIL|sofia.morante@example.org]].""",
    "kontrolle": """Rechnung für Bürobedarf, 125,00 EUR.
Der Termin fällt aus. Bitte Abschnitt 3.1 der Anleitung prüfen.""",
}
LABEL = re.compile(r"\[\[([A-Z]+)\|([^\]]+)\]\]")


def annotated(source):
    source = canonical(source)
    expected, parts = [], []
    previous, offset = 0, 0
    for match in LABEL.finditer(source):
        typ, value = match.groups()
        assert typ in TYPES
        plain = source[previous:match.start()]
        parts.extend((plain, value))
        start = offset + len(plain)
        offset = start + len(value)
        expected.append((typ, start, offset))
        previous = match.end()
    parts.append(source[previous:])
    return "".join(parts), expected


def replacement_spans(result):
    shift = 0
    for replacement in result.replacements:
        start = replacement.start - shift
        end = start + len(replacement.original)
        assert result.original_text[start:end] == replacement.original
        yield replacement.typ, start, end
        shift += len(replacement.placeholder) - len(replacement.original)


def main():
    totals, full, partial, false = (Counter() for _ in range(4))
    with TemporaryDirectory() as directory:
        os.environ["HARNESS_DB"] = str(Path(directory) / "vault.sqlite")
        for name, source in DOCUMENTS.items():
            text, expected = annotated(source)
            result = api.analyze(text)
            try:
                actual = list(replacement_spans(result))
                covered = {i for _, start, end in actual for i in range(start, end)}
                for typ, start, end in expected:
                    totals[typ] += 1
                    masked = sum(i in covered for i in range(start, end))
                    if masked == end - start:
                        full[typ] += 1
                    else:
                        partial[typ] += bool(masked)
                        status = "teilweise" if masked else "übersehen"
                        print(f"{name}: {status} · {typ} · {text[start:end]}")
                for typ, start, end in actual:
                    if not any(start < b and a < end for _, a, b in expected):
                        false[typ] += 1
                        print(f"{name}: Falschtreffer · {typ} · {text[start:end]}")
            finally:
                api.forget(result.session_id)

    print(f"\n{len(DOCUMENTS)} Dokumente")
    print("Typ        Soll  Vollständig  Teilweise  Übersehen  Falschtreffer")
    for typ in [*TYPES, "Gesamt"]:
        total, masked, partly, extra = (
            counts.total() if typ == "Gesamt" else counts[typ]
            for counts in (totals, full, partial, false)
        )
        print(f"{typ:10} {total:4} {masked:12} {partly:10} {total - masked - partly:10} {extra:14}")


if __name__ == "__main__":
    main()
