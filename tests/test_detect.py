import re

from harness.detect import Finding, RegexDetector, _chunks, detect_all, merge_findings


def _found(text):
    return {(f.typ, f.text) for f in RegexDetector().detect(text)}


def test_email():
    assert ("EMAIL", "j.weidenfeld@example.org") in _found("Mail: j.weidenfeld@example.org.")


def test_iban_de_with_and_without_spaces():
    assert ("IBAN", "DE89 3704 0044 0532 0130 00") in _found("IBAN DE89 3704 0044 0532 0130 00 bitte")
    assert ("IBAN", "DE89370400440532013000") in _found("IBAN DE89370400440532013000")


def test_iban_foreign_needs_valid_checksum():
    assert ("IBAN", "GB82 WEST 1234 5698 7654 32") in _found("GB82 WEST 1234 5698 7654 32")
    assert not any(t == "IBAN" for t, _ in _found("GB00 WEST 1234 5698 7654 32"))


def test_german_phone_formats():
    for number in ["+49 561 7712093", "0561 4409218", "0171 2398841", "030/12345678", "+49 (0)30 1234567", "0049 89 123456"]:
        assert ("TELEFON", number) in _found(f"Tel. {number}."), number


def test_dates():
    found = _found("geb. 14.03.1979, am 1.4.25, ISO 2026-09-02 und am 5. Juli 1984.")
    assert {("DATUM", "14.03.1979"), ("DATUM", "1.4.25"), ("DATUM", "2026-09-02"), ("DATUM", "5. Juli 1984")} <= found


def _dates(text):
    return [f.text for f in detect_all(text, [RegexDetector()]) if f.typ == "DATUM"]


def test_date_without_year():
    assert _dates("Termin am 14.03. und am 5. Juli bitte.") == ["14.03", "5. Juli"]


def test_month_and_year():
    assert _dates("geboren im März 1979 in Kassel") == ["März 1979"]


def test_date_with_slashes():
    assert _dates("geboren 03/14/1979 in Kassel") == ["03/14/1979"]


def test_full_date_stays_one_finding():
    assert _dates("geboren am 14. März 1979 und am 14.03.1979") == ["14. März 1979", "14.03.1979"]


def test_section_numbers_and_versions_are_not_dates():
    assert _dates("Abschnitt 3.1. und Kapitel 12.4. in Version 10.12.3 von 2019, Mai ohne Jahr") == []


def test_iban_in_lowercase():
    assert ("IBAN", "de89 3704 0044 0532 0130 00") in _found("Konto de89 3704 0044 0532 0130 00 bitte")
    assert ("IBAN", "gb82 west 1234 5698 7654 32") in _found("Konto gb82 west 1234 5698 7654 32 bitte")


def test_lowercase_text_with_invalid_checksum_is_no_iban():
    assert not any(t == "IBAN" for t, _ in _found("Kennung gb00 west 1234 5698 7654 32 bitte"))


def test_postcode_is_not_a_phone():
    assert not any(t == "TELEFON" for t, _ in _found("34127 Kassel"))


def test_merge_regex_wins_structured_overlap():
    text = "an max.mueller@example.org Berlin"
    regex = Finding(3, 26, "max.mueller@example.org", "EMAIL", "regex", 1.0)
    model = Finding(3, 33, text[3:33], "PERSON", "gliner", 0.99)   # länger, trotzdem verliert es
    merged = merge_findings([model, regex], text)
    assert [(f.typ, f.quelle) for f in merged] == [("EMAIL", "regex")]


def test_merge_longer_wins_otherwise():
    text = "Hauptstraße 3, 10115 Berlin"
    whole = Finding(0, len(text), text, "ADRESSE", "gliner", 0.6)
    city = Finding(21, 27, "Berlin", "ORT", "gliner", 0.9)
    assert [f.typ for f in merge_findings([city, whole], text)] == ["ADRESSE"]


def test_merge_trims_punctuation():
    text = "an Max Müller, bitte"
    merged = merge_findings([Finding(3, 14, "Max Müller,", "PERSON", "gliner", 0.8)], text)
    assert merged[0].text == "Max Müller"


def test_ids_without_label():
    for value in ["52 749 130 680", "73105862491", "12 150385 M 123", "A123456789",
                  "3 O 123/26", "VIII ZR 45/24", "https://praxis.example/patient/4711", "www.praxis.example/fall/12"]:
        assert ("KENNUNG", value) in _found(f"siehe {value} bitte"), value


def test_ids_with_label():
    assert ("KENNUNG", "3-O-99") in _found("Az.: 3-O-99 vom Gericht")
    assert ("KENNUNG", "M-4711") in _found("Mandantennummer M-4711 anlegen")
    assert ("KENNUNG", "LG-AB 123") in _found("Kennzeichen LG-AB 123 gemeldet")
    assert not any(t == "KENNUNG" for t, _ in _found("Das Aktenzeichen fehlt noch."))


def test_ids_do_not_hit_ordinary_numbers():
    found = _found("Kaufpreis 6.800 Euro, Rechnung 2025/12, am 01.04.2025, Tel. 0171 2398841, PLZ 34127")
    assert not any(t == "KENNUNG" for t, _ in found), found


def test_steuernummer_beats_phone():
    text = "St.-Nr. 022/815/08150"
    assert [(f.typ, f.text) for f in merge_findings(RegexDetector().detect(text), text)] == [("KENNUNG", "022/815/08150")]


def test_foreign_phones():
    for number in ["+43 660 1234567", "+1 415 555 0100", "+33 1 23 45 67 89", "+44 20 7946 0958"]:
        assert ("TELEFON", number) in _found(f"Tel. {number}."), number


def test_addresses():
    for value in ["Fasanenweg 22, 48149 Münster", "Brunnenstraße 4, 79098 Freiburg im Breisgau", "Am Kirchberg 9, 79227 Schallstadt",
                  "Hamburger Straße 12a", "Karl-Marx-Allee 3", "21335 Lüneburg"]:
        assert ("ADRESSE", value) in _found(f"Wohnhaft: {value}."), value


def test_addresses_do_not_hit_prose():
    found = _found("Im Jahr 2025 kostet es 10000 Euro. Paragraph 5 und Punkt 3 gelten, Anlage 2 auch.")
    assert not any(t == "ADRESSE" for t, _ in found), found


def test_salutation_marks_only_the_name():
    found = _found("Herr Weidenfeld zahlt, Dr. med. Konrad Haslinger schreibt an Frau von Berg.")
    assert {("PERSON", "Weidenfeld"), ("PERSON", "Konrad Haslinger"), ("PERSON", "von Berg")} <= found


def test_salutation_ignores_role_words():
    assert not any(t == "PERSON" for t, _ in _found("Sehr geehrte Frau Kollegin, wie Herr Mandant sagte."))


def test_salutation_does_not_add_second_person():
    class Model:
        name = "fake"

        def detect(self, text):
            start = text.index("Sabine Kettelhut")
            return [Finding(start, start + 16, "Sabine Kettelhut", "PERSON", "fake", 0.9)]

    text = "Sabine Kettelhut kauft. Frau Kettelhut zahlt."
    found = detect_all(text, [RegexDetector(), Model()])
    assert [f.text for f in found if f.typ == "PERSON"] == ["Sabine Kettelhut"]


def test_labeled_id_stops_at_sentence_end():
    for text in ["Az. 3 O 123/26. Rückfragen bitte.", "Az. 3 O 123/26. 2 Termine folgen.", "Az. 3 O 123/26 Rückfragen bitte."]:
        ids = [v for t, v in _found(text) if t == "KENNUNG"]
        assert ids == ["3 O 123/26"], (text, ids)


def test_tax_id_without_label_needs_valid_checksum():
    assert ("KENNUNG", "52 749 130 680") in _found("ID 52 749 130 680 liegt vor")
    for value in ["52 749 130 681", "12345678901"]:
        assert _found(f"Bitte {value} prüfen.") == set(), value


def test_tax_id_with_label_needs_no_checksum():
    for text in ["Steuer-ID: 52 749 130 681", "Steuer-IdNr. 52749130681", "IdNr 52749130681", "Identifikationsnummer 52 749 130 681"]:
        assert [v for t, v in _found(text) if t == "KENNUNG"] == [text.split(maxsplit=1)[1].lstrip(": ")], text


def test_steuernummer_needs_label():
    for text in ["Steuernummer 22/815/08150", "St.-Nr. 93815/08152", "StNr: 123/456/78901", "stnr 12/345/67890"]:
        assert [v for t, v in _found(text) if t == "KENNUNG"] == [text.split()[-1]], text
    for value in ["12/345/67890", "93815/08152"]:
        assert not any(t == "KENNUNG" for t, _ in _found(f"Vorgang {value} erledigt")), value


def test_legal_references_amounts_and_years_stay():
    text = ("Die Kündigung gemäß § 573 Abs. 2 BGB ist unwirksam. Die Werkbank kostete 6.800 Euro, "
            "verarbeitet nach Art. 6 DSGVO. Im Jahr 2025 kamen 12.345,67 EUR hinzu, siehe auch §§ 535, 536 BGB.")
    assert _found(text) == set()


def _masked_names(text):
    return [v for t, v in _found(text) if t == "PERSON"]


def test_salutation_masks_whole_name_in_any_script():
    for name in ["Nguyễn", "Hoàng", "Çelik", "Šimić", "McDonald", "O'Neill", "Müller-Lüdenscheidt", "José García", "Hoàng Trung Loc", "von der Leyen"]:
        for anrede in ["Frau", "Herr", "Herrn", "Dr."]:
            assert _masked_names(f"Laut {anrede} {name} zahlt.") == [name], (anrede, name)


def test_salutation_in_capitals():
    assert _masked_names("HERR MÜLLER zahlt.") == ["MÜLLER"]


def test_salutation_skips_professions():
    assert _masked_names("Sehr geehrter Herr Rechtsanwalt.") == []
    assert _masked_names("Sehr geehrte Frau Doktor, bitte.") == []
    assert _masked_names("Herr Rechtsanwalt Müller zahlt.") == ["Müller"]
    assert _masked_names("Frau von nebenan zahlt.") == []


def test_salutation_stops_at_lowercase_word():
    assert _masked_names("Frau Kettelhut zahlt die Miete.") == ["Kettelhut"]


def test_no_address_in_ordinary_sentences():
    for text in ["Der Bundesgerichtshof 12 entschied.", "Am Arbeitsplatz 3 Personen.", "Im Umfeld 2 Fälle.", "Der Rechtsweg 2 ist offen.",
                 "Es kamen 50000 Menschen und 12000 Kunden.", "Es kamen 50000 Gäste.", "Am Montag 14 Termine.", "Die Straße 5 mal gesperrt."]:
        assert not any(t == "ADRESSE" for t, _ in _found(text)), text


def test_ambiguous_street_with_context_is_an_address():
    for value in ["Am Kirchberg 9", "Am Marktplatz 3", "Zur Mühlenbach 2", "Marktplatz 3, 21335 Lüneburg", "Bahnhof 7 21335 Lüneburg"]:
        assert ("ADRESSE", value) in _found(f"Wohnhaft: {value}."), value


def test_postcode_alone_needs_separator_or_preposition():
    for text in ["Sitz: 21335 Lüneburg", "wohnt in 21335 Lüneburg.", "21335 Lüneburg", "Muster, 21335 Lüneburg"]:
        assert ("ADRESSE", "21335 Lüneburg") in _found(text), text


def test_salutation_does_not_swallow_next_salutation():
    names = _masked_names("Frau Çelik schreibt an Herrn Šimić, Frau O'Neill und Herrn José García.")
    assert {"Çelik", "Šimić", "O'Neill", "José García"} <= set(names), names


def test_model_person_loses_salutation_and_profession():
    text = "Frau Sabine Kettelhut, Herr Rechtsanwalt Brandt, Herr Rechtsanwalt und Frau Doktor."
    model = [Finding(m.start(), m.end(), m.group(), "PERSON", "gliner", 0.9) for m in
             re.finditer(r"Frau Sabine Kettelhut|Herr Rechtsanwalt Brandt|Herr Rechtsanwalt(?= und)|Frau Doktor", text)]
    assert [f.text for f in merge_findings(model, text)] == ["Sabine Kettelhut", "Brandt"]


def test_email_with_umlaut_in_local_part_and_domain():
    assert ("EMAIL", "jürgen.müller@beispiel.de") in _found("Mail an jürgen.müller@beispiel.de bitte")
    assert ("EMAIL", "info@müller-bau.de") in _found("Mail an info@müller-bau.de.")


def test_chunks_stay_within_limit_and_keep_offsets():
    text = "wort " * 1000
    chunks = _chunks(text)
    assert max(len(chunk) for _, chunk in chunks) <= 800
    assert all(text[offset : offset + len(chunk)] == chunk for offset, chunk in chunks)
    assert chunks[-1][0] + len(chunks[-1][1]) == len(text)


def test_chunks_split_text_without_whitespace():
    text = "x" * 2000
    chunks = _chunks(text)
    assert max(len(chunk) for _, chunk in chunks) <= 800
    assert all(text[offset : offset + len(chunk)] == chunk for offset, chunk in chunks)
    assert chunks[-1][0] + len(chunks[-1][1]) == len(text)


def test_chunks_keep_name_on_cut_whole():
    # Der Name wandert über jede mögliche Schnittstelle, in einem Stück muss er immer ganz stehen.
    for padding in range(740, 800, 3):
        text = "x" * padding + " Jonas Weidenfeld " + "wort " * 400
        assert any("Jonas Weidenfeld" in chunk for _, chunk in _chunks(text)), padding


def test_chunks_keep_long_name_whole_without_spaces_around_it():
    for padding in range(250, 280):
        text = "ab;" * padding + "Anna Maria Weidenfeld;" + "ab;" * 400
        assert any("Anna Maria Weidenfeld" in chunk for _, chunk in _chunks(text)), padding


# --- Übernommen aus dem Vergleich mit Presidio --------------------------------

def test_address_without_street_word_with_postcode_or_context():
    assert ("ADRESSE", "Am Sande 12, 21335 Lüneburg") in _found("wohnhaft Am Sande 12, 21335 Lüneburg")
    assert ("ADRESSE", "am Sande 12, 21335 Lüneburg") in _found("wohnhaft am Sande 12, 21335 Lüneburg")
    assert ("ADRESSE", "Am Sande 12\n21335 Lüneburg") in _found("Herrn Max Muster\nAm Sande 12\n21335 Lüneburg")
    for text, value in [("Anschrift: Im Grund 4", "Im Grund 4"), ("Sie wohnt An der Kirche 3 in Lüneburg.", "An der Kirche 3"),
                        ("Die Mandantin wohnt am Alten Markt 3.", "am Alten Markt 3"), ("Zustellanschrift: Zur Linde 2", "Zur Linde 2")]:
        assert ("ADRESSE", value) in _found(text), text


def test_address_without_street_word_does_not_hit_prose():
    for text in ["Am Montag 14 Termine.", "Die Wohnung hat im Durchschnitt 3 Zimmer.", "Das Objekt wurde zur Prüfung 3 Wochen gesperrt.",
                 "Die Mietsache ist am Ende 2 Jahre alt.", "Wohnung: Im Erdgeschoss 2 Zimmer", "Anschrift im Briefkopf 2 mal falsch",
                 "Die Mietsache wurde zur Verfügung 2026 gestellt.", "Objekt Nr. 3, gelegen im Ortsteil Ochtmissen 4 km entfernt",
                 "Am Sande 12 Personen."]:
        assert not any(t == "ADRESSE" for t, _ in _found(text)), text


def test_german_ids_from_presidio():
    for text, value in [("unter HRB 12345 eingetragen", "HRB 12345"), ("HRA 4711 B beim AG", "HRA 4711 B"),
                        ("Unsere USt-IdNr lautet DE 136 695 976.", "DE 136 695 976"), ("USt-IdNr. DE136695976", "DE136695976"),
                        ("Führerschein B072RRE2I55", "B072RRE2I55"), ("Reisepass C01X00T47", "C01X00T47")]:
        assert ("KENNUNG", value) in _found(text), text


def test_vat_id_needs_valid_checksum_without_label():
    assert not any(t == "KENNUNG" for t, _ in _found("Vorgang DE 136 695 977 erledigt"))
    assert not any(t == "KENNUNG" for t, _ in _found("Der Reisepass ist abgelaufen."))


def test_model_load_failure_gives_german_sentence(monkeypatch):
    # Ohne Netz beim ersten Start käme sonst „403 Forbidden“ oder eine englische Meldung in der Oberfläche an.
    import sys
    import types

    import pytest

    from harness import detect

    class Broken:
        @staticmethod
        def from_pretrained(name):
            raise OSError("Connection refused to huggingface.co")

    monkeypatch.setitem(sys.modules, "gliner", types.SimpleNamespace(GLiNER=Broken))
    monkeypatch.setattr(detect, "_gliner_cache", {})
    with pytest.raises(detect.ModelUnavailableError) as e:
        detect.GlinerDetector(model_name="nicht/da").detect("Erika Musterfrau")
    assert str(e.value) == detect.MODEL_UNAVAILABLE and "huggingface" not in str(e.value)
