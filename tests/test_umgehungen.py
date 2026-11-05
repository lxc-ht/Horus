"""Umgehungsversuche aus dem Test gegen die laufende Demo. Alle Daten sind erfunden."""

import re
import unicodedata

import pytest

from harness import api
from harness.detect import RegexDetector, _chunks


def _masked(text):
    return api.analyze(text).masked_text


# --- Modellgrenze -----------------------------------------------------------

def test_chunks_stay_below_model_token_limit():
    """GLiNER schneidet nach 384 Wörtern still ab. Was dahinter steht, sähe das Modell nie."""
    text = "\n".join(f"{i};x;y;z" for i in range(400)) + "\nJonas Weidenfeld;x;y"
    chunks = _chunks(text)
    for offset, chunk in chunks:
        assert text[offset : offset + len(chunk)] == chunk
        assert len(re.findall(r"\w+(?:[-_]\w+)*|\S", chunk)) <= 350
    assert any("Jonas Weidenfeld" in chunk for _, chunk in chunks)


def test_token_chunks_keep_name_on_cut_whole():
    for padding in range(330, 370):
        text = "; ".join(["a"] * padding) + " Jonas Weidenfeld hat gekündigt."
        assert any("Jonas Weidenfeld" in chunk for _, chunk in _chunks(text)), padding


# --- Unicode ----------------------------------------------------------------

@pytest.mark.parametrize("text, secret", [
    ("Konto DE89 3704 0044 0532 0130 00.", "3704"),
    ("Konto DE89 3704 0044 0532 0130 00.", "3704"),
    ("DE89​3704​0044​0532​0130​00", "3704"),
    ("Tel. +49 561 7712093", "7712093"),
    ("geboren am 14. März 1979", "1979"),
    ("Tel. ０５６１ ７７１２０９３", "7712093"),
    ("ＤＥ８９ ３７０４ ００４４ ０５３２ ０１３０ ００", "3704"),
    ("Mail: weidenfeld＠example.org", "weidenfeld"),
    ("Mail: j.weiden­feld@example.org", "feld@"),
    (unicodedata.normalize("NFD", "Mail: jürgen@beispiel.de"), "beispiel"),
    ("Frau Hoﬀmann schrieb gestern.", "mann"),
])
def test_invisible_and_compatibility_characters_do_not_hide_values(text, secret):
    assert secret not in unicodedata.normalize("NFKC", _masked(text))


def test_original_text_is_the_checked_text():
    result = api.analyze("Herr Weiden­feld schrieb.")
    assert result.original_text == "Herr Weidenfeld schrieb."
    assert result.masked_text == "Herr [PERSON_1] schrieb."


def test_manual_term_is_normalized_like_the_text():
    result = api.analyze(unicodedata.normalize("NFD", "Das Büro Mühlenkamp ist zu."))
    result = api.add_manual(result.session_id, unicodedata.normalize("NFD", "Mühlenkamp"), "FIRMA")
    assert "Mühlenkamp" not in result.masked_text
    assert "[FIRMA_1]" in result.masked_text


# --- Platzhalter im Originaltext -------------------------------------------

def test_literal_placeholder_is_not_restored_to_a_person():
    text = "Jonas Weidenfeld klagt. Die Vorlage nennt [PERSON_1] und [IBAN_1]. Konto DE89 3704 0044 0532 0130 00."
    result = api.analyze(text)
    assert "[PERSON_1]" in result.masked_text and "[IBAN_1]" in result.masked_text
    back = api.restore(result.session_id, result.masked_text)
    assert back.text == text
    assert "[PERSON_1]" in back.unknown and "[IBAN_1]" in back.unknown
    assert back.missing == []


def test_literal_placeholder_without_brackets_is_not_restored():
    text = "Das Feld PERSON_1 ist leer. Jonas Weidenfeld klagt."
    result = api.analyze(text)
    assert result.masked_text == "Das Feld PERSON_1 ist leer. [PERSON_2] klagt."
    assert api.restore(result.session_id, result.masked_text).text == text


def test_manual_term_skips_literal_placeholder():
    text = "Die Vorlage nennt [FIRMA_1]. Das Büro Mühlenkamp ist zu."
    result = api.analyze(text)
    result = api.add_manual(result.session_id, "Mühlenkamp", "FIRMA")
    assert api.restore(result.session_id, result.masked_text).text == text


# --- Teile einer Adresse ----------------------------------------------------

def test_street_and_postcode_alone_are_masked():
    masked = _masked("Lindenhofweg 17, 34127 Kassel. Im Lindenhofweg gab es Lärm, PLZ 34127 liegt im Norden.")
    assert "Lindenhofweg" not in masked and "34127" not in masked


def test_address_parts_do_not_touch_ordinary_words():
    masked = _masked("Lange Straße 5, 34127 Kassel. Die Straße ist lang, es kamen 17 Gäste.")
    assert "Die Straße ist lang, es kamen 17 Gäste." in masked


# --- Formate ----------------------------------------------------------------

@pytest.mark.parametrize("text, typ, value", [
    ("Konto DE89-3704-0044-0532-0130-00 bitte", "IBAN", "DE89-3704-0044-0532-0130-00"),
    ("Konto DE 89 3704 0044 0532 0130 00 bitte", "IBAN", "DE 89 3704 0044 0532 0130 00"),
    ("Konto DE89.3704.0044.0532.0130.00 bitte", "IBAN", "DE89.3704.0044.0532.0130.00"),
    ("Konto DE89 370 400 440 532 013 000 bitte", "IBAN", "DE89 370 400 440 532 013 000"),
    ("Konto DE89 3704 0044 0532 0130 00 BIC folgt", "IBAN", "DE89 3704 0044 0532 0130 00"),
    ("Konto GB82-WEST-1234-5698-7654-32 bitte", "IBAN", "GB82-WEST-1234-5698-7654-32"),
    ("Kontonummer 532013000, BLZ 37040044", "KENNUNG", "532013000"),
    ("Kontonummer 532013000, BLZ 37040044", "KENNUNG", "37040044"),
    ("BIC COBADEFFXXX", "KENNUNG", "COBADEFFXXX"),
    ("Rechnungsnummer RE-2026-00471 offen", "KENNUNG", "RE-2026-00471"),
    ("Fallnummer 2026/4711 offen", "KENNUNG", "2026/4711"),
    ("Kunden-Nr. 88213 offen", "KENNUNG", "88213"),
    ("Karte 4111 1111 1111 1111 gesperrt", "KENNUNG", "4111 1111 1111 1111"),
    ("Zugriff von 192.168.17.23 gesehen", "KENNUNG", "192.168.17.23"),
    ("Fahrzeug KS-AB 1234 gesehen", "KENNUNG", "KS-AB 1234"),
    ("Tel. 0561.7712093", "TELEFON", "0561.7712093"),
    ("Tel. 0561 7 7 1 2 0 9 3", "TELEFON", "0561 7 7 1 2 0 9 3"),
    ("Tel. 7712093", "TELEFON", "7712093"),
    ("Mobil: 0171–1234567", "TELEFON", "0171–1234567"),
    ("geb. 14-03-1979 in", "DATUM", "14-03-1979"),
    ("geb. 14. 03. 1979 in", "DATUM", "14. 03. 1979"),
    ("geb. 14 März 1979 in", "DATUM", "14 März 1979"),
    ("geb. 14. Mrz. 1979 in", "DATUM", "14. Mrz. 1979"),
    ("Lindenhofweg 17, D-34127 Kassel", "ADRESSE", "Lindenhofweg 17, D-34127 Kassel"),
    ("Postfach 1234, 34127 Kassel", "ADRESSE", "Postfach 1234"),
])
def test_format_is_found(text, typ, value):
    assert (typ, value) in {(f.typ, f.text) for f in RegexDetector().detect(text)}


@pytest.mark.parametrize("text", [
    "Version 1.2.3 ist aktuell.",
    "Die Miete beträgt 1234567890123 Cent.",              # ungültige Prüfziffer, keine Karte
    "Abschnitt 1. 2. 20 bleibt.",
    "Das Konto ist leer und die Rechnung offen.",
    "Es kamen 5 Gäste, der Rat tagte am Mai-Feiertag.",
    "Der A-B-Test lief gut.",
])
def test_ordinary_text_stays(text):
    assert _masked(text) == text


# --- Zweite Runde: Zeilenumbrüche und Geheimnisse ------------------------------

@pytest.mark.parametrize("text, typ, value", [
    ("Konto DE89 3704 0044\n0532 0130 00 bitte", "IBAN", "DE89 3704 0044\n0532 0130 00"),
    ("Konto DE89 3704 0044 \n0532 0130 00 bitte", "IBAN", "DE89 3704 0044 \n0532 0130 00"),
    ("Tel. 0561\n7712093", "TELEFON", "0561\n7712093"),
    ("geboren am 14. März\n1979", "DATUM", "14. März\n1979"),
    ("geboren im März\n1979", "DATUM", "März\n1979"),
    ("Passwort: Sommer2026!", "KENNUNG", "Sommer2026!"),
    ("Kennwort = hallo123", "KENNUNG", "hallo123"),
    ("PIN: 4711", "KENNUNG", "4711"),
    ("API-Key: abc123def456", "KENNUNG", "abc123def456"),
    ("Schlüssel sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456", "KENNUNG", "sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"),
    ("Token ghp_abcdefghijklmnopqrstuvwx", "KENNUNG", "ghp_abcdefghijklmnopqrstuvwx"),
    ("Profil @jonas.weidenfeld79 gesehen", "KENNUNG", "@jonas.weidenfeld79"),
])
def test_format_across_lines_and_secrets_are_found(text, typ, value):
    assert (typ, value) in {(f.typ, f.text) for f in RegexDetector().detect(text)}


@pytest.mark.parametrize("text", [
    "Das Passwort wurde geändert und der Token ist abgelaufen.",
    "Die PIN ist neu.",
    "Preis @ 5 Euro.",
])
def test_secret_words_without_value_stay(text):
    assert _masked(text) == text


def test_email_is_not_mistaken_for_a_handle():
    assert _masked("Mail an j.w@example.org bitte") == "Mail an [EMAIL_1] bitte"


def test_line_break_in_value_restores_exactly():
    text = "Konto DE89 3704 0044\n0532 0130 00 bitte"
    result = api.analyze(text)
    assert "3704" not in result.masked_text
    assert api.restore(result.session_id, result.masked_text).text == text
