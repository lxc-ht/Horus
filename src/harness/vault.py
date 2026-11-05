"""Zuordnung Platzhalter → Original in einer lokalen SQLite-Datenbank.

Die Zuordnung gilt pro Sitzung. Derselbe Originalwert (ohne Groß-/Kleinschreibung,
Leerzeichen normalisiert) bekommt in einer Sitzung immer denselben Platzhalter.
Nummeriert wird pro Typ, Nummern werden nie wiederverwendet.
"""

from __future__ import annotations

import os
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Sitzungen leben nur im Speicher des Prozesses. Was nach einem Absturz liegen bleibt, ist nutzlos und wird gelöscht.
SESSION_TTL = timedelta(hours=24)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mappings (
    session_id TEXT NOT NULL REFERENCES sessions(id),
    placeholder TEXT NOT NULL,
    original TEXT NOT NULL,
    typ TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,  -- 0 = vom Menschen zurückgenommen
    PRIMARY KEY (session_id, placeholder)
);
"""


@dataclass(frozen=True)
class Mapping:
    placeholder: str
    original: str
    typ: str
    active: bool


def normalize(value: str) -> str:
    return " ".join(value.split()).lower()


def db_path() -> Path:
    """HARNESS_DB oder data/vault.sqlite im Repo (bei Installation außerhalb: im Arbeitsverzeichnis)."""
    env = os.environ.get("HARNESS_DB")
    if env:
        return Path(env)
    root = Path(__file__).resolve().parents[2]
    base = root if (root / "pyproject.toml").exists() else Path.cwd()
    return base / "data" / "vault.sqlite"


def _connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA secure_delete = ON")   # gelöschte Originalwerte nicht lesbar in der Datei lassen
    conn.executescript(_SCHEMA)
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_session() -> str:
    session_id = uuid.uuid4().hex
    with closing(_connect()) as conn, conn:
        cutoff = (_now() - SESSION_TTL).isoformat(timespec="seconds")
        conn.execute("DELETE FROM mappings WHERE session_id IN (SELECT id FROM sessions WHERE created_at < ?)", (cutoff,))
        conn.execute("DELETE FROM sessions WHERE created_at < ?", (cutoff,))
        conn.execute(
            "INSERT INTO sessions (id, created_at) VALUES (?, ?)",
            (session_id, _now().isoformat(timespec="seconds")),
        )
    return session_id


def delete_sessions(session_ids: list[str]) -> None:
    """Löscht Sitzungen samt Zuordnung."""
    if not session_ids:
        return
    with closing(_connect()) as conn, conn:
        for session_id in session_ids:
            conn.execute("DELETE FROM mappings WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


def mappings(session_id: str, active_only: bool = True) -> list[Mapping]:
    sql = "SELECT placeholder, original, typ, active FROM mappings WHERE session_id = ?"
    if active_only:
        sql += " AND active = 1"
    with closing(_connect()) as conn:
        rows = conn.execute(sql, (session_id,)).fetchall()
    return [Mapping(p, o, t, bool(a)) for p, o, t, a in rows]


def placeholder_for(session_id: str, original: str, typ: str) -> str:
    """Liefert den Platzhalter für original und legt ihn bei Bedarf an.

    Ein zuvor zurückgenommener Wert wird wieder aktiv und behält seinen Platzhalter.
    """
    key = normalize(original)
    with closing(_connect()) as conn, conn:
        rows = conn.execute(
            "SELECT placeholder, original, active FROM mappings WHERE session_id = ?", (session_id,)
        ).fetchall()
        for placeholder, existing, active in rows:
            if normalize(existing) == key:
                if not active:
                    conn.execute(
                        "UPDATE mappings SET active = 1 WHERE session_id = ? AND placeholder = ?",
                        (session_id, placeholder),
                    )
                return placeholder

        prefix = f"[{typ}_"
        numbers = [int(p[len(prefix):-1]) for p, _, _ in rows if p.startswith(prefix)]
        placeholder = f"{prefix}{max(numbers, default=0) + 1}]"
        conn.execute(
            "INSERT INTO mappings (session_id, placeholder, original, typ) VALUES (?, ?, ?, ?)",
            (session_id, placeholder, original, typ),
        )
    return placeholder


def deactivate(session_id: str, placeholder: str) -> bool:
    with closing(_connect()) as conn, conn:
        cur = conn.execute(
            "UPDATE mappings SET active = 0 WHERE session_id = ? AND placeholder = ? AND active = 1",
            (session_id, placeholder),
        )
    return cur.rowcount > 0
