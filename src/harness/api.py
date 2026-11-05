"""Der Vertrag des Harness-Kerns. Die Weboberfläche importiert NUR dieses Modul.

Signaturen, Feldnamen und Ausnahmen bleiben stabil. Ergänzungen nur zusätzlich
und mit Eintrag in BACKLOG.md unter „Vertrag erweitert“.

Datentypen (Felder siehe jeweiliges Modul, hier re-exportiert):
    Replacement(placeholder, original, typ, start, end)             mask.py
    MaskResult(session_id, original_text, masked_text,
               replacements, warnings)                               mask.py
    Release(session_id, text, sha256, created_at)                    gate.py
    RestoreResult(text, unknown, changed, missing, warnings)         restore.py
    LeakError, ReleaseMismatchError                                  gate.py
    NoApiKeyError                                                    cloud.py

Sitzungszustand (Originaltext, Stellen) liegt im Speicher, die Zuordnung in SQLite.
Keine Funktion gibt etwas auf stdout aus. Logs enthalten nur Platzhalter, Typen, Zählungen.
"""

from __future__ import annotations

import atexit
import logging
import signal
import sys
import threading
from collections import Counter
from dataclasses import dataclass, field

from . import cloud, gate, mask, vault
from . import restore as _restore
from .cloud import CloudError, NoApiKeyError
from .detect import TYPES, Detector, GlinerDetector, RegexDetector, detect_all
from .gate import LeakError, Release, ReleaseMismatchError
from .mask import MaskResult, Replacement, Span
from .restore import RestoreResult

__all__ = [
    "TYPES", "Replacement", "MaskResult", "Release", "RestoreResult",
    "LeakError", "ReleaseMismatchError", "NoApiKeyError", "CloudError",
    "analyze", "add_manual", "remove", "get", "release", "has_api_key", "send", "restore",
    "set_detectors",
]

log = logging.getLogger(__name__)

WARN_TERM_NOT_FOUND = "„{term}“ kommt im Text nicht vor, es wurde nichts maskiert."
WARN_TERM_PARTLY_MASKED = "„{term}“ überschneidet sich mit einer anderen Ersetzung und ist nicht vollständig maskiert. Nimm diese erst zurück."


@dataclass
class _Session:
    original_text: str
    spans: list[Span] = field(default_factory=list)
    issued: set[str] = field(default_factory=set)   # SHA-256 der gültigen Freigaben


_sessions: dict[str, _Session] = {}
_lock = threading.RLock()
_detectors: list[Detector] | None = None

# Ohne den Prozess sind die Sitzungen weg, also auch ihre Zuordnung löschen. Nach einem Absturz greift vault.SESSION_TTL.
atexit.register(lambda: vault.delete_sessions(list(_sessions)))

# SIGTERM und ein geschlossenes Terminal (SIGHUP) beenden Python sonst ohne atexit. uvicorn ruft diesen Handler nach seinem Shutdown auf.
if threading.current_thread() is threading.main_thread():
    for _name in ("SIGTERM", "SIGHUP"):
        _signal = getattr(signal, _name, None)   # SIGHUP gibt es unter Windows nicht
        if _signal is not None and signal.getsignal(_signal) == signal.SIG_DFL:
            signal.signal(_signal, lambda signum, _frame: sys.exit(128 + signum))


def set_detectors(detectors: list[Detector] | None) -> None:
    """Erweiterung: Detektoren festlegen (Tests, weitere Detektoren). None = Standard (Regex + GLiNER)."""
    global _detectors
    _detectors = detectors


def _active_detectors() -> list[Detector]:
    global _detectors
    if _detectors is None:
        _detectors = [RegexDetector(), GlinerDetector()]
    return _detectors


def _session(session_id: str) -> _Session:
    try:
        return _sessions[session_id]
    except KeyError:
        raise KeyError(f"Unbekannte Sitzung: {session_id}") from None


def _masked(session_id: str, s: _Session) -> tuple[str, list[Replacement], list[vault.Mapping]]:
    mappings = vault.mappings(session_id)
    types = {m.placeholder: m.typ for m in vault.mappings(session_id, active_only=False)}
    masked, replacements = mask.build(s.original_text, s.spans, types)
    return masked, replacements, mappings


def _all_mappings(session_id: str) -> list[vault.Mapping]:
    """Auch zurückgenommene Werte: propagate() maskiert sie nicht, braucht sie aber für mehrdeutige Namensteile."""
    return vault.mappings(session_id, active_only=False)


def _result(session_id: str, extra_warnings: list[str] | None = None) -> MaskResult:
    s = _session(session_id)
    masked, replacements, mappings = _masked(session_id, s)
    warnings = gate.name_part_warnings(masked, mappings) + (extra_warnings or [])
    return MaskResult(session_id, s.original_text, masked, replacements, warnings)


def _log_counts(action: str, session_id: str, s: _Session) -> None:
    counts = Counter(p.placeholder.strip("[]").rsplit("_", 1)[0] for p in s.spans)
    log.info("%s: Sitzung %s, %d Stellen %s", action, session_id[:8], len(s.spans), dict(counts))


def analyze(text: str) -> MaskResult:
    """Neue Sitzung: erkennen und maskieren."""
    with _lock:
        session_id = vault.create_session()
        s = _Session(original_text=text)
        for f in detect_all(text, _active_detectors()):
            placeholder = vault.placeholder_for(session_id, f.text, f.typ)
            if all(f.end <= x.start or f.start >= x.end for x in s.spans):
                s.spans.append(Span(f.start, f.end, placeholder))
        s.spans = mask.propagate(text, sorted(s.spans, key=lambda x: x.start), _all_mappings(session_id))
        _sessions[session_id] = s
        _log_counts("analyze", session_id, s)
        return _result(session_id)


def _fully_masked(spans: list[Span], start: int, end: int) -> bool:
    """Deckt spans den Bereich start bis end lückenlos ab?"""
    position = start
    for span in sorted(spans, key=lambda x: x.start):
        if span.start <= position < span.end:
            position = span.end
    return position >= end


def add_manual(session_id: str, term: str, typ: str) -> MaskResult:
    """Jedes Vorkommen von term zusätzlich maskieren."""
    typ = typ.strip().upper()
    if typ not in TYPES:
        raise ValueError(f"Unbekannter Typ: {typ}. Erlaubt: {', '.join(TYPES)}")
    term = " ".join(term.split())
    if not term:
        raise ValueError("Leerer Begriff.")
    with _lock:
        s = _session(session_id)
        if not mask.occurrence_pattern(term).search(s.original_text):
            return _result(session_id, [WARN_TERM_NOT_FOUND.format(term=term)])
        placeholder = vault.placeholder_for(session_id, term, typ)
        s.spans = mask.add_occurrences(s.original_text, s.spans, term, placeholder)
        # Namensteile neu berechnen: Eine neue Person kann einen bisher eindeutigen Teil mehrdeutig machen.
        s.spans = mask.propagate(s.original_text, s.spans, _all_mappings(session_id))
        s.issued.clear()   # jede Änderung macht bisherige Freigaben ungültig
        _log_counts(f"add_manual {placeholder}", session_id, s)
        partly = any(
            not _fully_masked(s.spans, m.start(), m.end()) for m in mask.occurrence_pattern(term).finditer(s.original_text)
        )
        return _result(session_id, [WARN_TERM_PARTLY_MASKED.format(term=term)] if partly else None)


def remove(session_id: str, placeholder: str) -> MaskResult:
    """Ersetzung zurücknehmen."""
    placeholder = placeholder.strip()
    if not placeholder.startswith("["):
        placeholder = f"[{placeholder}]"
    with _lock:
        s = _session(session_id)
        if not vault.deactivate(session_id, placeholder):
            raise ValueError(f"Platzhalter nicht in dieser Sitzung: {placeholder}")
        s.spans = mask.drop(s.spans, placeholder)
        # Andere bekannte Werte, die in der freigelegten Stelle stecken, bleiben maskiert.
        s.spans = mask.propagate(s.original_text, s.spans, _all_mappings(session_id))
        s.issued.clear()
        _log_counts(f"remove {placeholder}", session_id, s)
        return _result(session_id)


def get(session_id: str) -> MaskResult:
    with _lock:
        return _result(session_id)


def release(session_id: str) -> Release:
    """Gibt den AKTUELLEN maskierten Text frei, LeakError bei Leck."""
    with _lock:
        s = _session(session_id)
        masked, _, mappings = _masked(session_id, s)
        try:
            rel = gate.make_release(session_id, masked, mappings)
        except LeakError as e:
            log.warning("release blockiert: Sitzung %s, Leck bei %s", session_id[:8], e.placeholders)
            raise
        s.issued.add(rel.sha256)
        log.info("release: Sitzung %s, sha256 %s", session_id[:8], rel.sha256[:12])
        return rel


def has_api_key() -> bool:
    return cloud.has_api_key()


def send(rel: Release) -> str:
    """Antwort von Claude; ReleaseMismatchError / NoApiKeyError.

    Die Freigabe wird immer zuerst geprüft. NoApiKeyError heißt also auch:
    rel.text ist gültig freigegeben und darf im Kopier-Modus ausgegeben werden.
    """
    with _lock:
        s = _sessions.get(rel.session_id)
        current = _masked(rel.session_id, s)[0] if s else None
        gate.verify(rel, current, s.issued if s else set())
    return cloud.ask(rel.text)


def restore(session_id: str, answer: str) -> RestoreResult:
    with _lock:
        s = _session(session_id)
        masked, _, mappings = _masked(session_id, s)
    originals = {m.placeholder: m.original for m in mappings}
    sent = list(dict.fromkeys(gate.PLACEHOLDER_RE.findall(masked)))
    result = _restore.restore(answer, originals, sent)
    log.info(
        "restore: Sitzung %s, unbekannt %s, verändert %d, fehlend %s",
        session_id[:8], result.unknown, len(result.changed), result.missing,
    )
    return result
