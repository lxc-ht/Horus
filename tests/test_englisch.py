"""Englische Anreden wie „Mr“ und „Mrs“ verhalten sich genau wie „Herr“ und „Frau“.

Ohne Netz und ohne GLiNER: Der FakeDetector meldet die Stellen so, wie das echte Modell
sie auf diesem Text gemeldet hat, also mit Anrede im Wert („Mr Mark Dunmore“).
Alle Namen sind erfunden.
"""

from __future__ import annotations

import re

import pytest

from harness import api
from harness.detect import Finding, RegexDetector, merge_findings
from harness.mask import name_parts

from conftest import FakeDetector

TEXT = (
    "The driver was Mr Mark Dunmore. Mr Whitaker fell and broke his wrist.\n"
    "The witness is Mrs Ingrid Kettle. Mrs Kettle saw the accident."
)

# So meldet das Modell die Personen: Anrede im Wert, dazu einmal eine Anrede allein.
MODEL_TERMS = {
    "Mr Mark Dunmore": "PERSON",
    "Mr Whitaker": "PERSON",
    "Mrs Ingrid Kettle": "PERSON",
    "Mrs": "PERSON",
}


@pytest.fixture
def english():
    api.set_detectors([RegexDetector(), FakeDetector(MODEL_TERMS)])


def _placeholder_for(result, name: str) -> set[str]:
    return {r.placeholder for r in result.replacements if name in r.original}


def test_salutation_stays_in_text_and_is_never_a_name(english):
    result = api.analyze(TEXT)
    masked = result.masked_text
    # Kein Platzhalter direkt hinter einem anderen, also nie „[PERSON_2] [PERSON_1] fell“.
    assert not re.search(r"\][ \t]*\[", masked), masked
    assert masked.count("Mr ") == 2
    assert masked.count("Mrs ") == 2
    for name in ("Whitaker", "Dunmore", "Kettle"):
        assert name not in masked
        assert len(_placeholder_for(result, name)) == 1, name
    # Gespeichert wird der Name ohne Anrede.
    assert {r.original for r in result.replacements} == {"Ingrid Kettle", "Kettle", "Mark Dunmore", "Whitaker"}


def test_surname_alone_keeps_salutation(english):
    masked = api.analyze(TEXT).masked_text
    kettle = re.search(r"Mrs (\[PERSON_\d+\]) saw", masked)
    assert kettle is not None, masked
    assert masked.count(kettle.group(1)) == 2   # „Mrs Ingrid Kettle“ und „Mrs Kettle“: dieselbe Person


def test_restore_does_not_double_salutation(english):
    result = api.analyze(TEXT)
    (dunmore,) = _placeholder_for(result, "Dunmore")
    assert api.restore(result.session_id, f"Mr {dunmore}").text == "Mr Mark Dunmore"


@pytest.mark.parametrize("salutation", ["Mr", "Mr.", "Mrs", "Mrs.", "Ms", "Ms.", "Miss", "Mx", "Sir", "MR", "mrs"])
def test_every_english_salutation_is_cut_off(salutation):
    text = f"{salutation} Ada Quillfeather"
    merged = merge_findings([Finding(0, len(text), text, "PERSON", "gliner", 0.9)], text)
    assert [f.text for f in merged] == ["Ada Quillfeather"]


@pytest.mark.parametrize("salutation", ["Mr", "Mr.", "Mrs.", "Ms", "Miss", "Sir"])
def test_salutation_alone_is_dropped(salutation):
    text = f"{salutation} spoke."
    assert merge_findings([Finding(0, len(salutation), salutation, "PERSON", "gliner", 0.9)], text) == []


def test_salutation_is_no_name_part():
    assert name_parts("Mrs Ingrid Kettle") == ["ingrid", "kettle"]
    assert name_parts("Sir Mx. Miss Quillfeather") == ["quillfeather"]


def test_regex_finds_name_after_english_salutation():
    # Ohne Modell: „Mr Whitaker“ ist wie „Herr Whitaker“ ein Personen-Hinweis, die Anrede bleibt draußen.
    found = [f.text for f in RegexDetector().detect("Yesterday Mr. Whitaker and Ms Kettle met Sir Ada Quill.") if f.typ == "PERSON"]
    assert found == ["Whitaker", "Kettle", "Ada Quill"]


def test_lowercase_miss_and_sir_are_ordinary_words():
    found = [f for f in RegexDetector().detect("You will miss Paris, sir Lancelot.") if f.typ == "PERSON"]
    assert found == []
