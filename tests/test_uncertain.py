"""Unsichere Stellen: Sie werden dem Menschen gezeigt und ändern nichts am Text."""

from harness import api
from harness.detect import Finding, GlinerDetector, RegexDetector

from conftest import FakeDetector


class HintDetector(FakeDetector):
    """Findet feste Begriffe sicher, weitere nur knapp unter der Schwelle."""

    def __init__(self, terms, hints):
        super().__init__(terms)
        self.hints = hints

    def uncertain(self, text):
        return [
            Finding(text.index(h), text.index(h) + len(h), h, typ, self.name, 0.3)
            for h, typ in self.hints.items() if h in text
        ]


def _analyze(text, terms=None, hints=None):
    api.set_detectors([RegexDetector(), HintDetector(terms or {}, hints or {})])
    return api.analyze(text)


def _plain(result):
    return [u for u in result.uncertain if not u.masked]


def test_hint_stays_in_text_and_is_reported_at_its_position():
    result = _analyze("Der Kollege Ronny kommt.", hints={"Ronny": "PERSON"})
    assert "Ronny" in result.masked_text
    hint = _plain(result)[0]
    assert (hint.text, hint.typ) == ("Ronny", "PERSON")
    assert result.masked_text[hint.start : hint.end] == "Ronny"


def test_hint_is_only_a_whole_word():
    result = _analyze("Ronnys Rad und Ronny.", hints={"Ronny": "PERSON"})
    assert [u.start for u in _plain(result)] == [result.masked_text.rindex("Ronny")]


def test_hint_disappears_after_masking_and_positions_follow():
    result = _analyze("Anna Link und der Kollege Ronny.", {"Anna Link": "PERSON"}, {"Ronny": "PERSON"})
    hint = _plain(result)[0]
    assert result.masked_text[hint.start : hint.end] == "Ronny"
    assert _plain(api.add_manual(result.session_id, "Ronny", "PERSON")) == []


def test_hint_comes_back_when_masking_is_taken_back():
    result = _analyze("Der Kollege Ronny kommt.", hints={"Ronny": "PERSON"})
    masked = api.add_manual(result.session_id, "Ronny", "PERSON")
    placeholder = masked.replacements[0].placeholder
    assert [u.text for u in _plain(api.remove(result.session_id, placeholder))] == ["Ronny"]


def test_uncertain_never_changes_the_released_text():
    result = _analyze("Der Kollege Ronny kommt, Vorgang 4471-B.", hints={"Ronny": "PERSON"})
    assert result.uncertain
    assert api.release(result.session_id).text == result.masked_text


def test_unmasked_numbers_are_reported_without_noise():
    text = "Vorgang 4471-B, Akte 123/26. Im Jahr 2026 kostet es 3.200,00 Euro, nach § 123 BGB, und 19 % sind 7 Tage."
    assert [u.text for u in _plain(_analyze(text))] == ["4471-B", "123/26"]


def test_number_with_sentence_end_keeps_its_end_position():
    result = _analyze("Das betrifft die Akte 987/26.")
    number = _plain(result)[0]
    assert number.text == "987/26"
    assert result.masked_text[number.end] == "."


def test_placeholder_numbers_are_not_reported():
    result = _analyze("".join(f"Person{i} " for i in range(3)), {f"Person{i}": "PERSON" for i in range(3)})
    assert _plain(result) == []


def test_name_part_without_salutation_is_flagged_with_salutation_not():
    text = "Jonas Weidenfeld schrieb. Weidenfeld antwortete. Herr Weidenfeld kam."
    result = _analyze(text, {"Jonas Weidenfeld": "PERSON"})
    flagged = [u for u in result.uncertain if u.masked]
    assert len(flagged) == 1
    assert flagged[0].text == "Weidenfeld"
    assert "Jonas Weidenfeld" in flagged[0].reason
    assert result.masked_text[: flagged[0].start].endswith("schrieb. ")


def test_low_score_match_is_flagged_only_for_the_model():
    class Low(FakeDetector):
        name = GlinerDetector.name

        def detect(self, text):
            return [Finding(0, 4, "Rolf", "PERSON", self.name, 0.6)]

    api.set_detectors([Low({})])
    result = api.analyze("Rolf kommt.")
    assert [(u.text, u.masked) for u in result.uncertain] == [("Rolf", True)]


def test_context_that_reveals_a_person_is_shown():
    text = "Sie ist die einzige Kinderärztin im Ort. Der Bürgermeister von Hasenwinkel hat unterschrieben."
    result = _analyze(text)
    found = {u.text: u for u in _plain(result)}
    assert set(found) == {"die einzige Kinderärztin im Ort", "Bürgermeister von Hasenwinkel"}
    for u in found.values():
        assert u.typ == "PERSON" and "ohne Namen" in u.reason
        assert result.masked_text[u.start : u.end] == u.text
    assert result.masked_text == text   # nur ein Hinweis, der Text bleibt


def test_context_hint_skips_masked_places_and_things():
    result = _analyze("Der Bürgermeister von Hasenwinkel sagt, das sei der einzige Weg.", terms={"Hasenwinkel": "ORT"})
    assert "[ORT_1]" in result.masked_text
    assert [u for u in _plain(result) if "ohne Namen" in u.reason] == []
