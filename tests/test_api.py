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
    assert result.masked_text.count("[PERSON_1]") == 3   # dazu „Herr [PERSON_1]“ aus dem Nachnamen


def test_numbering_per_type():
    result = api.analyze(SAMPLE)
    placeholders = {r.placeholder for r in result.replacements}
    assert {"[PERSON_1]", "[PERSON_2]", "[FIRMA_1]", "[EMAIL_1]", "[TELEFON_1]", "[IBAN_1]", "[DATUM_1]"} <= placeholders


def test_missed_occurrence_is_propagated():
    # Das „Modell“ findet nur die erste Stelle, die zweite (anders geschrieben) wird trotzdem maskiert.
    api.set_detectors([RegexDetector(), FakeDetector({"Jonas Weidenfeld": "PERSON"}, first_only=True)])
    result = api.analyze("Jonas Weidenfeld schreibt. Später: JONAS  WEIDENFELD unterschreibt.")
    assert result.masked_text == "[PERSON_1] schreibt. Später: [PERSON_1] unterschreibt."


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
    with pytest.raises(KeyError) as e:
        api.get("gibt-es-nicht")
    assert str(e.value) == api.UNKNOWN_SESSION   # ohne die Anführungszeichen von KeyError


def test_restore_warns_when_name_part_stood_for_a_common_word():
    api.set_detectors([FakeDetector({"Muellers Antrag": "PERSON"})])
    result = api.analyze("Sie stellte den Antrag. Muellers Antrag wurde abgelehnt.")
    assert result.masked_text == "Sie stellte den [PERSON_1]. [PERSON_1] wurde abgelehnt."
    restored = api.restore(result.session_id, result.masked_text)
    assert restored.warnings == [api.WARN_PART_RESTORED.format(platzhalter="[PERSON_1]", teil="Antrag", wert="Muellers Antrag")]


def test_restore_stays_quiet_after_salutation_or_without_placeholder():
    api.set_detectors([FakeDetector({"Erika Musterfrau": "PERSON"})])
    result = api.analyze("Erika Musterfrau klagt. Frau Musterfrau und Dr. Musterfrau erscheinen.")
    assert api.restore(result.session_id, result.masked_text).warnings == []

    result = api.analyze("Erika Musterfrau klagt. Musterfrau erscheint.")
    assert api.restore(result.session_id, "Keine Platzhalter hier.").warnings == ["Nicht in der Antwort: [PERSON_1]"]


# --- Namensteile ---------------------------------------------------------------

def _persons(*names):
    api.set_detectors([RegexDetector(), FakeDetector({n: "PERSON" for n in names})])


def test_last_name_alone_gets_same_placeholder():
    result = api.analyze(SAMPLE)
    assert "Herr [PERSON_1] zahlt" in result.masked_text
    assert "Weidenfeld" not in result.masked_text
    assert result.warnings == []
    hit = next(r for r in result.replacements if r.original == "Weidenfeld")
    assert hit.placeholder == "[PERSON_1]"


def test_name_part_whole_word_and_case_insensitive():
    _persons("Erika Musterfrau")
    result = api.analyze("Erika Musterfrau klagt. Frau MUSTERFRAU zweifelt, Erika auch.")
    assert result.masked_text == "[PERSON_1] klagt. Frau [PERSON_1] zweifelt, [PERSON_1] auch."
    assert result.warnings == []


def test_name_part_inside_longer_word_is_untouched():
    _persons("Erika Musterfrau")
    result = api.analyze("Erika Musterfrau ist Mitglied im Musterfrauenverband.")
    assert result.masked_text == "[PERSON_1] ist Mitglied im Musterfrauenverband."
    assert result.warnings == []


def test_shared_last_name_stays_with_warning():
    _persons("Max Mustermann", "Erika Mustermann")
    result = api.analyze("Max Mustermann und Erika Mustermann streiten. Mustermann gibt nach.")
    assert result.masked_text == "[PERSON_1] und [PERSON_2] streiten. Mustermann gibt nach."
    assert result.warnings == [
        "Achtung: „Mustermann“ steht noch im Text und gehört vermutlich zu [PERSON_1] oder [PERSON_2]."
    ]
    api.release(result.session_id)   # nur eine Warnung, kein Leck


def test_new_person_makes_name_part_ambiguous_again():
    _persons("Max Mustermann")
    result = api.analyze("Max Mustermann trifft Erika Mustermann. Mustermann gibt nach.")
    assert result.masked_text.endswith("[PERSON_1] gibt nach.")
    result = api.add_manual(result.session_id, "Erika Mustermann", "PERSON")
    assert result.masked_text == "[PERSON_1] trifft [PERSON_2]. Mustermann gibt nach."
    assert any("[PERSON_1] oder [PERSON_2]" in w for w in result.warnings)


def test_removed_person_name_part_is_not_masked_again():
    _persons("Erika Musterfrau")
    result = api.analyze("Erika Musterfrau klagt. Frau Musterfrau zweifelt.")
    result = api.remove(result.session_id, "[PERSON_1]")
    assert result.masked_text == "Erika Musterfrau klagt. Frau Musterfrau zweifelt."
    # Auch eine spätere Änderung, die alles neu berechnet, holt den Teil nicht zurück.
    result = api.add_manual(result.session_id, "klagt", "ORT")
    assert result.masked_text == "Erika Musterfrau [ORT_1]. Frau Musterfrau zweifelt."
    assert result.warnings == []


def test_removed_person_keeps_shared_part_ambiguous():
    # Der Mensch hat Erika zurückgenommen. „Mustermann“ kann trotzdem sie meinen, also kein Raten.
    _persons("Max Mustermann", "Erika Mustermann")
    result = api.analyze("Max Mustermann und Erika Mustermann streiten. Mustermann gibt nach.")
    result = api.remove(result.session_id, "[PERSON_2]")
    assert result.masked_text == "[PERSON_1] und Erika Mustermann streiten. Mustermann gibt nach."
    assert result.warnings == [
        "Achtung: „Mustermann“ steht noch im Text und gehört vermutlich zu [PERSON_1]."
    ]


def test_stopword_parts_are_not_masked():
    _persons("Dr. med. Konrad Haslinger")
    result = api.analyze("Dr. med. Konrad Haslinger schreibt. Herr Dr. Haslinger grüßt.")
    assert result.masked_text == "[PERSON_1] schreibt. Herr Dr. [PERSON_1] grüßt."


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
    text = SAMPLE.replace("Herr Weidenfeld", "Jonas Weidenfeld")
    result = api.analyze(text)
    restored = api.restore(result.session_id, result.masked_text)
    assert restored.text == text
    assert restored.unknown == restored.changed == restored.missing == []
    assert restored.warnings == []


def test_round_trip_last_name_comes_back_as_full_name():
    # Bekannte Eigenheit: Ein allein maskierter Nachname kommt als voller Name zurück.
    result = api.analyze(SAMPLE)
    restored = api.restore(result.session_id, result.masked_text)
    assert restored.text == SAMPLE.replace("Herr Weidenfeld", "Herr Jonas Weidenfeld")
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


def test_round_trip_with_ids():
    text = ("Az.: 3 O 123/26, Mandantennummer M-4711. Steuer-ID 52 749 130 681, St.-Nr. 22/815/08150, "
            "Versichertennummer A123456789. Erneut Az. 3 O 123/26 nach § 573 Abs. 2 BGB über 6.800 Euro.")
    result = api.analyze(text)
    assert "Az.: [KENNUNG_1]" in result.masked_text and "Az. [KENNUNG_1]" in result.masked_text
    for value in ["3 O 123/26", "M-4711", "52 749 130 681", "22/815/08150", "A123456789"]:
        assert value not in result.masked_text
    assert "§ 573 Abs. 2 BGB über 6.800 Euro" in result.masked_text
    restored = api.restore(result.session_id, result.masked_text)
    assert restored.text == text
    assert restored.unknown == restored.changed == restored.missing == []


def test_genitive_of_name_part_is_masked_and_keeps_its_s():
    _persons("Anna Müller")
    result = api.analyze("Anna Müller klagt. Müllers Antrag liegt vor.")
    assert result.masked_text == "[PERSON_1] klagt. [PERSON_1]s Antrag liegt vor."
    assert api.restore(result.session_id, "Frau [PERSON_1]s Antrag").text == "Frau Anna Müllers Antrag"


def test_longer_word_starting_with_name_part_stays():
    _persons("Anna Müller")
    result = api.analyze("Anna Müller wohnt in der Müllersiedlung.")
    assert result.masked_text == "[PERSON_1] wohnt in der Müllersiedlung."


def test_umlaut_spelling_variants_are_masked_both_ways():
    _persons("Anna Müller", "Jonas Krueger")
    result = api.analyze("Anna Müller und Jonas Krueger. Mueller und Krüger zahlen.")
    assert "Mueller" not in result.masked_text
    assert "Krüger" not in result.masked_text


def test_sharp_s_spelling_variants_are_masked():
    _persons("Hans Weiß")
    result = api.analyze("Hans Weiß klagt. WEISS und Weiss zahlen.")
    assert result.masked_text == "[PERSON_1] klagt. [PERSON_1] und [PERSON_1] zahlen."


def test_full_name_in_other_spelling_is_one_placeholder():
    _persons("Anna Müller")
    result = api.analyze("Anna Müller klagt. ANNA MUELLER zahlt.")
    assert result.masked_text == "[PERSON_1] klagt. [PERSON_1] zahlt."


def test_ambiguous_genitive_warns():
    _persons("Anna Müller", "Bernd Müller")
    result = api.analyze("Anna Müller und Bernd Müller. Müllers Antrag.")
    assert "Müllers" in result.masked_text
    assert any("Müller" in warning for warning in result.warnings)


def test_persons_differing_only_in_spelling_stay_ambiguous():
    _persons("Anna Müller", "Bernd Mueller")
    result = api.analyze("Anna Müller und Bernd Mueller. Mueller zahlt.")
    assert result.masked_text == "[PERSON_1] und [PERSON_2]. Mueller zahlt."
    assert any("[PERSON_1] oder [PERSON_2]" in warning for warning in result.warnings)


def test_removing_one_of_two_spellings_does_not_mix_persons():
    _persons("Anna Müller", "Bernd Mueller")
    result = api.analyze("Anna Müller und Bernd Mueller.")
    assert api.remove(result.session_id, "[PERSON_1]").masked_text == "Anna Müller und [PERSON_2]."


def test_spelling_variant_never_matches_inside_a_word():
    _persons("Mae", "Sue")
    result = api.analyze("Mae und Sue klagen im März in Süddeutschland.")
    assert result.masked_text == "[PERSON_1] und [PERSON_2] klagen im März in Süddeutschland."


def test_lowercase_genitive_form_is_not_masked_but_warned():
    _persons("Anna Link")
    result = api.analyze("Anna Link soll unten links unterschreiben.")
    assert result.masked_text == "[PERSON_1] soll unten links unterschreiben."
    assert any("„link“" in warning for warning in result.warnings)


def test_lowercase_spelling_variant_is_not_masked_but_warned():
    _persons("Hans Weiss")
    result = api.analyze("Hans Weiss sagt, ich weiß es nicht.")
    assert result.masked_text == "[PERSON_1] sagt, ich weiß es nicht."
    assert any("weiß" in warning for warning in result.warnings)


def test_lowercase_exact_name_part_stays_masked():
    _persons("Anna Müller")
    result = api.analyze("Anna Müller klagt, müller zahlt.")
    assert result.masked_text == "[PERSON_1] klagt, [PERSON_1] zahlt."


def test_long_s_in_value_does_not_crash():
    _persons("Hanss Berg")   # canonical() macht aus „ſ“ ein „s“, bevor der Detektor den Text sieht
    assert api.analyze("Hanſs Berg klagt.").masked_text == "[PERSON_1] klagt."


def test_bare_placeholder_with_genitive_is_restored_and_reported():
    _persons("Anna Müller")
    session = api.analyze("Anna Müller klagt.").session_id
    bare = api.restore(session, "PERSON_1s Antrag")
    assert bare.text == "Anna Müllers Antrag"
    assert any("ohne Klammern" in warning for warning in bare.warnings)
    assert api.restore(session, "person 1s Antrag").changed == ["person 1"]


# --- Vorladen ------------------------------------------------------------------

class _WarmDetector:
    name = "warm"

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = 0

    def detect(self, text):
        return []

    def warm_up(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("Modell nicht erreichbar")


def test_warm_up_loads_every_detector_that_can():
    warm = _WarmDetector()
    api.set_detectors([RegexDetector(), warm])   # RegexDetector hat nichts vorzuladen
    api.warm_up()
    assert warm.calls == 1


def test_warm_up_never_raises_and_logs_only_the_error_type(caplog):
    api.set_detectors([_WarmDetector(fail=True)])
    with caplog.at_level(logging.INFO, logger="harness.api"):
        api.warm_up()
    assert "RuntimeError" in caplog.text
    assert "nicht erreichbar" not in caplog.text
