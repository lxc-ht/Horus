from harness.detect import Finding, RegexDetector, merge_findings


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
