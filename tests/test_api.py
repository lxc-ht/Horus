import logging

import pytest

from harness import api, cloud, gate
from harness.detect import RegexDetector
from harness.vault import Mapping

from conftest import SAMPLE, FakeDetector

ORIGINALS = [
    "Jonas Weidenfeld", "Theresa Kolbinger", "Grauberg Wohnbau GmbH",
    "j.weidenfeld@example.org", "+49 561 7712093", "DE89 3704 0044 0532 0130 00", "14.03.1979",
]


def _placeholder(result, original):
    return next(r.placeholder for r in result.replacements if r.original == original)


# --- Maskieren -----------------------------------------------------------------

def test_all_sensitive_values_are_masked():
    result = api.analyze(SAMPLE)
    for value in ORIGINALS:
        assert value not in result.masked_text
    assert result.replacements == sorted(result.replacements, key=lambda r: r.start)
    for r in result.replacements:
        assert result.masked_text[r.start : r.end] == r.placeholder


def test_same_name_twice_same_placeholder():
    result = api.analyze(SAMPLE)
    hits = [r for r in result.replacements if r.original == "Jonas Weidenfeld"]
    assert len(hits) == 2
    assert hits[0].placeholder == hits[1].placeholder == "[PERSON_1]"
    assert result.masked_text.count("[PERSON_1]") == 2


def test_numbering_per_type():
    result = api.analyze(SAMPLE)
    placeholders = {r.placeholder for r in result.replacements}
    assert {"[PERSON_1]", "[PERSON_2]", "[FIRMA_1]", "[EMAIL_1]", "[TELEFON_1]", "[IBAN_1]", "[DATUM_1]"} <= placeholders


def test_missed_occurrence_is_propagated():
    # Das „Modell“ findet nur die erste Stelle, die zweite (anders geschrieben) wird trotzdem maskiert.
    api.set_detectors([RegexDetector(), FakeDetector({"Jonas Weidenfeld": "PERSON"}, first_only=True)])
    result = api.analyze("Jonas Weidenfeld schreibt. Später: JONAS  WEIDENFELD unterschreibt.")
    assert result.masked_text == "[PERSON_1] schreibt. Später: [PERSON_1] unterschreibt."


def test_last_name_alone_gives_warning():
    result = api.analyze(SAMPLE)
    assert "Herr Weidenfeld" in result.masked_text
    assert "Achtung: „Weidenfeld“ steht noch im Text und gehört vermutlich zu [PERSON_1]." in result.warnings


def test_add_manual_masks_every_occurrence():
    result = api.analyze(SAMPLE)
    result = api.add_manual(result.session_id, "Kündigung", "FIRMA")
    assert "Kündigung" not in result.masked_text
    assert "[FIRMA_2]" in result.masked_text


def test_add_manual_last_name_removes_warning():
    result = api.analyze(SAMPLE)
    result = api.add_manual(result.session_id, "Weidenfeld", "person")
    assert "Herr [PERSON_3]" in result.masked_text
    assert not any("Weidenfeld" in w for w in result.warnings)


def test_add_manual_unknown_type():
    result = api.analyze(SAMPLE)
    with pytest.raises(ValueError):
        api.add_manual(result.session_id, "Kündigung", "GEHEIM")


def test_add_manual_term_not_in_text():
    result = api.analyze(SAMPLE)
    result = api.add_manual(result.session_id, "Nirgendwo", "ORT")
    assert any("kommt im Text nicht vor" in w for w in result.warnings)


def test_remove_restores_text_and_number_is_not_reused():
    result = api.analyze(SAMPLE)
    result = api.remove(result.session_id, "[PERSON_2]")
    assert "Theresa Kolbinger" in result.masked_text
    api.release(result.session_id)   # zurückgenommen = bewusst, kein Leck
    result = api.add_manual(result.session_id, "Kündigung", "PERSON")
    assert "[PERSON_3]" in result.masked_text


def test_remove_without_brackets_and_unknown():
    result = api.analyze(SAMPLE)
    result = api.remove(result.session_id, "FIRMA_1")
    assert "Grauberg Wohnbau GmbH" in result.masked_text
    with pytest.raises(ValueError):
        api.remove(result.session_id, "[FIRMA_1]")


def test_get_returns_current_state():
    result = api.analyze(SAMPLE)
    api.add_manual(result.session_id, "Kündigung", "FIRMA")
    assert "Kündigung" not in api.get(result.session_id).masked_text


def test_unknown_session():
    with pytest.raises(KeyError):
        api.get("gibt-es-nicht")


# --- Freigabe und Senden -------------------------------------------------------

def test_release_matches_masked_text():
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    assert rel.text == result.masked_text
    assert rel.sha256 == gate.sha256(rel.text)
    assert "T" in rel.created_at


def test_release_blocks_on_leak():
    result = api.analyze(SAMPLE)
    # Simuliert einen Fehler beim Maskieren: Stellen gehen verloren, die Zuordnung bleibt.
    api._sessions[result.session_id].spans = []
    with pytest.raises(api.LeakError) as e:
        api.release(result.session_id)
    assert str(e.value).startswith("Gestoppt: Ein Originalwert steht noch im Text.")
    assert "[PERSON_1]" in e.value.placeholders
    assert "Weidenfeld" not in str(e.value)


def test_leak_check_ignores_case_and_whitespace():
    mappings = [Mapping("[PERSON_1]", "Max  Müller", "PERSON", True)]
    with pytest.raises(api.LeakError):
        gate.make_release("s", "Gruß an MAX MÜLLER", mappings)
    # Zurückgenommene Werte zählen nicht.
    gate.make_release("s", "Gruß an Max Müller", [Mapping("[PERSON_1]", "Max Müller", "PERSON", False)])


def test_send_refuses_after_add_manual_following_release(monkeypatch):
    monkeypatch.setattr(cloud, "ask", lambda text: pytest.fail("darf nicht senden"))
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    api.add_manual(result.session_id, "Kündigung", "FIRMA")
    with pytest.raises(api.ReleaseMismatchError) as e:
        api.send(rel)
    assert str(e.value) == "Gestoppt: Der Text wurde nach der Freigabe geändert. Bitte erneut prüfen und freigeben."


def test_send_refuses_after_remove_following_release(monkeypatch):
    monkeypatch.setattr(cloud, "ask", lambda text: pytest.fail("darf nicht senden"))
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    api.remove(result.session_id, "[PERSON_2]")
    with pytest.raises(api.ReleaseMismatchError):
        api.send(rel)


def test_send_refuses_old_release_even_if_text_is_equal_again(monkeypatch):
    monkeypatch.setattr(cloud, "ask", lambda text: pytest.fail("darf nicht senden"))
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    api.remove(result.session_id, "[FIRMA_1]")
    api.add_manual(result.session_id, "Grauberg Wohnbau GmbH", "FIRMA")   # gleicher Text wie vorher
    assert api.get(result.session_id).masked_text == rel.text
    with pytest.raises(api.ReleaseMismatchError):
        api.send(rel)


def test_send_refuses_tampered_release(monkeypatch):
    monkeypatch.setattr(cloud, "ask", lambda text: pytest.fail("darf nicht senden"))
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    forged = api.Release(rel.session_id, rel.text + " Jonas Weidenfeld", rel.sha256, rel.created_at)
    with pytest.raises(api.ReleaseMismatchError):
        api.send(forged)
    rehashed = api.Release(rel.session_id, forged.text, gate.sha256(forged.text), rel.created_at)
    with pytest.raises(api.ReleaseMismatchError):
        api.send(rehashed)


def test_send_refuses_self_made_release(monkeypatch):
    # Eine Freigabe, die nicht von release() stammt, wird nicht akzeptiert.
    monkeypatch.setattr(cloud, "ask", lambda text: pytest.fail("darf nicht senden"))
    result = api.analyze(SAMPLE)
    text = result.masked_text
    with pytest.raises(api.ReleaseMismatchError):
        api.send(api.Release(result.session_id, text, gate.sha256(text), "2026-01-01T00:00:00+00:00"))


def test_send_without_key_raises_no_api_key():
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    assert api.has_api_key() is False
    with pytest.raises(api.NoApiKeyError) as e:
        api.send(rel)
    assert str(e.value).startswith("Kein API-Key gefunden — Kopier-Modus.")


def test_send_passes_exactly_the_released_text(monkeypatch):
    sent = []
    monkeypatch.setattr(cloud, "ask", lambda text: sent.append(text) or "Antwort zu [PERSON_1]")
    result = api.analyze(SAMPLE)
    rel = api.release(result.session_id)
    assert api.send(rel) == "Antwort zu [PERSON_1]"
    assert sent == [rel.text]
    for value in ORIGINALS:
        assert value not in sent[0]


# --- Rückübersetzung -----------------------------------------------------------

def test_round_trip_gives_original():
    result = api.analyze(SAMPLE)
    restored = api.restore(result.session_id, result.masked_text)
    assert restored.text == SAMPLE
    assert restored.unknown == restored.changed == restored.missing == []
    assert restored.warnings == []


def test_unknown_placeholder_is_reported():
    result = api.analyze(SAMPLE)
    restored = api.restore(result.session_id, "[PERSON_1] und [PERSON_9] und [FOO_1]")
    assert restored.text.startswith("Jonas Weidenfeld und [PERSON_9]")
    assert restored.unknown == ["[PERSON_9]"]
    assert "Unbekannt, nicht ersetzt: [PERSON_9]" in restored.warnings


def test_bare_placeholder_replaced_with_warning():
    result = api.analyze(SAMPLE)
    restored = api.restore(result.session_id, "[PERSON_1], PERSON_2 und [PERSON_9]")
    assert restored.text == "Jonas Weidenfeld, Theresa Kolbinger und [PERSON_9]"
    assert "PERSON_2 kam ohne Klammern zurück und wurde trotzdem ersetzt." in restored.warnings
    assert restored.unknown == ["[PERSON_9]"]


def test_changed_forms_are_not_replaced():
    result = api.analyze(SAMPLE)
    answer = "Person 1, PERSON1, [Person_1] und [PERSON 2]"
    restored = api.restore(result.session_id, answer)
    assert restored.text == answer
    assert restored.changed == ["Person 1", "PERSON1", "[Person_1]", "[PERSON 2]"]
    assert "Möglicherweise verändert, nicht ersetzt: „Person 1“" in restored.warnings


def test_missing_placeholders_are_reported():
    result = api.analyze(SAMPLE)
    restored = api.restore(result.session_id, "Kurz: [PERSON_1].")
    assert "[IBAN_1]" in restored.missing
    assert "[PERSON_1]" not in restored.missing
    assert "Nicht in der Antwort: [IBAN_1]" in restored.warnings


# --- Kein Leck über Logs oder stdout ------------------------------------------

def test_logs_and_stdout_contain_no_originals(caplog, capsys, monkeypatch):
    monkeypatch.setattr(cloud, "ask", lambda text: text)
    caplog.set_level(logging.DEBUG)
    result = api.analyze(SAMPLE)
    api.add_manual(result.session_id, "Weidenfeld", "PERSON")
    rel = api.release(result.session_id)
    answer = api.send(rel)
    api.restore(result.session_id, answer + " PERSON_2 [PERSON_9] Person 1")
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""
    for value in ORIGINALS + ["Weidenfeld"]:
        assert value not in caplog.text
