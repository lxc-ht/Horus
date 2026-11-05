from harness.detect import Finding, RegexDetector, detect_all, merge_findings


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
