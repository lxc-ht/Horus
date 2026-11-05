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
