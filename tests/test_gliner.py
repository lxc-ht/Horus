"""GLiNER-Test: lädt das Modell (Netz beim ersten Mal). Läuft nur mit `pytest -m slow`."""

from pathlib import Path

import pytest

from harness.detect import GlinerDetector, RegexDetector, detect_all

pytestmark = pytest.mark.slow


def test_gliner_finds_names_in_kanzlei_example():
    text = (Path(__file__).parent.parent / "examples" / "kanzlei.txt").read_text(encoding="utf-8")
    found = detect_all(text, [RegexDetector(), GlinerDetector()])
    persons = {f.text for f in found if f.typ == "PERSON"}
    assert "Jonas Weidenfeld" in persons
    assert "Theresa Kolbinger" in persons
    assert any(f.typ == "IBAN" and f.quelle == "regex" for f in found)
    for f in found:
        assert text[f.start : f.end] == f.text


def test_gliner_finds_name_late_in_long_paragraph_without_sentence_end():
    clause = "die Parteien haben sich im Rahmen der Besprechung ausführlich über den weiteren Ablauf ausgetauscht"
    text = ", und ".join([clause] * 30) + ", und der Mandant Jonas Weidenfeld erschien."
    found = detect_all(text, [GlinerDetector()])
    assert "Jonas Weidenfeld" in {f.text for f in found if f.typ == "PERSON"}
    for f in found:
        assert text[f.start : f.end] == f.text


@pytest.mark.slow
def test_gliner_finds_name_behind_many_short_tokens():
    """Das Modell liest nur 384 Wörter. Eine Tabelle mit kurzen Zellen darf den Namen dahinter nicht verstecken."""
    text = "\n".join(f"{i};x;y;z" for i in range(60)) + "\nJonas Weidenfeld;x;y"
    assert any("Weidenfeld" in f.text for f in GlinerDetector().detect(text))
