import os
import signal
import sqlite3
import stat
import subprocess
import sys
from datetime import timedelta

import pytest

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


@pytest.mark.parametrize("name", ["SIGTERM", "SIGHUP"])
def test_signal_deletes_mapping(tmp_path, name):
    db = tmp_path / "signal.sqlite"
    script = (
        "import os, signal\n"
        "from harness import api\n"
        "from harness.detect import RegexDetector\n"
        "api.set_detectors([RegexDetector()])\n"
        "api.analyze('Frau Muster, Tel. 0171 2398841')\n"
        f"os.kill(os.getpid(), signal.{name})\n"
    )
    done = subprocess.run([sys.executable, "-c", script], env={**os.environ, "HARNESS_DB": str(db)}, timeout=60)
    assert done.returncode == 128 + getattr(signal, name)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM mappings").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM sessions").fetchone()[0] == 0


def test_partial_overlap_warns():
    api.set_detectors([RegexDetector()])
    result = api.analyze("Kontakt Max Muster Haus.")
    result = api.add_manual(result.session_id, "Max Muster", "PERSON")
    assert result.warnings == []
    result = api.add_manual(result.session_id, "Muster Haus", "FIRMA")
    assert "Haus" in result.masked_text
    assert any("Muster Haus" in w and "nicht vollständig" in w for w in result.warnings)


def test_term_inside_existing_mask_does_not_warn():
    api.set_detectors([RegexDetector()])
    result = api.analyze("Kontakt Max Muster Haus.")
    result = api.add_manual(result.session_id, "Max Muster", "PERSON")
    result = api.add_manual(result.session_id, "Max", "PERSON")
    assert not any("nicht vollständig" in w for w in result.warnings)
def test_database_is_readable_only_by_owner():
    vault.create_session()
    assert stat.S_IMODE(vault.db_path().stat().st_mode) == 0o600


def test_existing_database_with_open_rights_is_tightened():
    vault.create_session()
    vault.db_path().chmod(0o644)
    vault.create_session()
    assert stat.S_IMODE(vault.db_path().stat().st_mode) == 0o600
