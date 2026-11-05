from datetime import timedelta

from harness import api, vault
from harness.detect import RegexDetector


def _session_ids():
    with vault.closing(vault._connect()) as conn:
        return {row[0] for row in conn.execute("SELECT id FROM sessions")}


def test_old_sessions_are_deleted(monkeypatch):
    old = vault.create_session()
    vault.placeholder_for(old, "Max Müller", "PERSON")
    real_now = vault._now()
    monkeypatch.setattr(vault, "_now", lambda: real_now + vault.SESSION_TTL + timedelta(minutes=1))
    new = vault.create_session()
    assert _session_ids() == {new}
    assert vault.mappings(old) == []


def test_recent_sessions_stay():
    first = vault.create_session()
    second = vault.create_session()
    assert _session_ids() == {first, second}


def test_delete_sessions_removes_mapping():
    keep = vault.create_session()
    gone = vault.create_session()
    vault.placeholder_for(keep, "Anna Berg", "PERSON")
    vault.placeholder_for(gone, "Max Müller", "PERSON")
    vault.delete_sessions([gone])
    assert _session_ids() == {keep}
    assert vault.mappings(gone) == []
    assert len(vault.mappings(keep)) == 1


def test_kennung_is_masked_and_restored():
    api.set_detectors([RegexDetector()])
    result = api.analyze("Steuer-ID 12 345 678 901 prüfen.")
    assert "12 345 678 901" not in result.masked_text
    placeholder = result.replacements[0].placeholder
    assert placeholder == "[KENNUNG_1]"
    assert api.restore(result.session_id, f"Die {placeholder} stimmt.").text == "Die 12 345 678 901 stimmt."
