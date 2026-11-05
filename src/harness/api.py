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
import re
import signal
import sys
import threading
from collections import Counter
from dataclasses import dataclass, field

from . import cloud, gate, mask, vault
from . import restore as _restore
from .cloud import CloudError, NoApiKeyError
from .detect import TYPES, UNSURE_BELOW_SCORE, Detector, Finding, GlinerDetector, RegexDetector, detect_all, merge_findings
from .gate import LeakError, Release, ReleaseMismatchError
from .mask import MaskResult, Replacement, Span, Uncertain
from .restore import RestoreResult

__all__ = [
    "TYPES", "Replacement", "Uncertain", "MaskResult", "Release", "RestoreResult",
    "LeakError", "ReleaseMismatchError", "NoApiKeyError", "CloudError",
    "analyze", "add_manual", "remove", "get", "release", "has_api_key", "send", "restore",
    "set_detectors",
]

log = logging.getLogger(__name__)

WARN_TERM_NOT_FOUND = "„{term}“ kommt im Text nicht vor, es wurde nichts maskiert."
WARN_TERM_PARTLY_MASKED = "„{term}“ überschneidet sich mit einer anderen Ersetzung und ist nicht vollständig maskiert. Nimm diese erst zurück."
WARN_PART_RESTORED = "{platzhalter} stand im gesendeten Text auch allein für „{teil}“, eingesetzt ist überall „{wert}“. Bitte diese Stellen prüfen."
UNKNOWN_SESSION = "Diese Sitzung ist nicht mehr bekannt, etwa nach einem Neustart. Bitte den Text neu analysieren."

# Nach einer Anrede ist der Nachname sicher ein Name, „Frau Erika Musterfrau“ stimmt dann auch.
_AFTER_SALUTATION = re.compile(r"(?:Herrn?|Frau|Dr\.|Prof\.)\s+$")


class _UnknownSession(KeyError):
    __str__ = Exception.__str__   # KeyError setzt die Meldung sonst in Anführungszeichen


@dataclass
class _Session:
    original_text: str
    spans: list[Span] = field(default_factory=list)
    issued: set[str] = field(default_factory=set)   # SHA-256 der gültigen Freigaben
    hints: list[Finding] = field(default_factory=list)   # Stellen unter der Schwelle des Modells
    unsure: set[str] = field(default_factory=set)        # Platzhalter, bei denen das Modell knapp lag


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
        raise _UnknownSession(UNKNOWN_SESSION) from None


def _masked(session_id: str, s: _Session) -> tuple[str, list[Replacement], list[vault.Mapping]]:
    mappings = vault.mappings(session_id)
    types = {m.placeholder: m.typ for m in vault.mappings(session_id, active_only=False)}
    masked, replacements = mask.build(s.original_text, s.spans, types)
    return masked, replacements, mappings


def _all_mappings(session_id: str) -> list[vault.Mapping]:
    """Auch zurückgenommene Werte: propagate() maskiert sie nicht, braucht sie aber für mehrdeutige Namensteile."""
    return vault.mappings(session_id, active_only=False)


REASON_MODEL_LOW = "Das Modell ist unsicher, ob das eine sensible Angabe ist."
REASON_NUMBER = "Diese Nummer wurde nicht ersetzt. Prüfe, ob sie eine Kennung ist, etwa ein Aktenzeichen."
REASON_UNSURE = "Ersetzt, aber das Modell war sich nicht sicher. Prüfe, ob das wirklich eine sensible Angabe ist."
REASON_NAME_PART = "Nur ein Namensteil von „{full}“. Prüfe, ob hier wirklich diese Person gemeint ist."

_LITERAL_PLACEHOLDER = re.compile(r"\b([A-Z]+)_(\d+)\b")
_NUMBER_LIKE = re.compile(r"(?<![\w/.-])[\w/.-]*\d[\w/.-]*")
_YEAR = re.compile(r"(?:19|20)\d\d")
_NOT_AN_ID_AFTER = re.compile(r"(?:,\d+)?\s*(?:Euro|EUR|€|%|Prozent)", re.IGNORECASE)
_SALUTATION_BEFORE = re.compile(r"(?:Frau|Herrn?|Dr\.|Prof\.)\s+$", re.IGNORECASE)


def _uncertain(s: _Session, masked: str, replacements: list[Replacement], mappings: list[vault.Mapping]) -> list[Uncertain]:
    """Stellen, die der Mensch vor der Freigabe ansehen soll. Sie ändern nichts am Text."""
    found: list[Uncertain] = []
    placeholders = [m.span() for m in gate.PLACEHOLDER_RE.finditer(masked)]

    def add_plain(start: int, end: int, typ: str, reason: str) -> None:
        if all(end <= a or start >= b for a, b in placeholders):
            found.append(Uncertain(masked[start:end], typ, start, end, False, reason))

    for hint in s.hints:
        for m in re.finditer(rf"(?<!\w){re.escape(hint.text)}(?!\w)", masked):
            add_plain(m.start(), m.end(), hint.typ, REASON_MODEL_LOW)

    for m in _NUMBER_LIKE.finditer(masked):
        token = m.group().rstrip("./-")
        end = m.start() + len(token)
        is_paragraph = masked[:m.start()].rstrip().endswith("§")
        if sum(c.isdigit() for c in token) < 3 or _YEAR.fullmatch(token) or is_paragraph or _NOT_AN_ID_AFTER.match(masked, end):
            continue
        add_plain(m.start(), end, "KENNUNG", REASON_NUMBER)

    full_names = {m.placeholder: m.original for m in mappings}
    for r in replacements:
        full = full_names.get(r.placeholder, r.original)
        if r.placeholder in s.unsure:
            found.append(Uncertain(r.original, r.typ, r.start, r.end, True, REASON_UNSURE))
        elif r.typ == "PERSON" and r.original.lower() != full.lower() and not _SALUTATION_BEFORE.search(masked[max(0, r.start - 8):r.start]):
            found.append(Uncertain(r.original, r.typ, r.start, r.end, True, REASON_NAME_PART.format(full=full)))

    found.sort(key=lambda u: (u.start, -u.end))
    # Modell und Nummernregel können dieselbe Stelle melden, einmal reicht.
    return [u for i, u in enumerate(found) if all(u.start >= p.end or u.end <= p.start for p in found[:i])]


def _result(session_id: str, extra_warnings: list[str] | None = None) -> MaskResult:
    s = _session(session_id)
    masked, replacements, mappings = _masked(session_id, s)
    warnings = gate.name_part_warnings(masked, mappings) + (extra_warnings or [])
    return MaskResult(session_id, s.original_text, masked, replacements, warnings, _uncertain(s, masked, replacements, mappings))


def _log_counts(action: str, session_id: str, s: _Session) -> None:
    counts = Counter(p.placeholder.strip("[]").rsplit("_", 1)[0] for p in s.spans)
    log.info("%s: Sitzung %s, %d Stellen %s", action, session_id[:8], len(s.spans), dict(counts))


def _literal_placeholders(text: str) -> set[str]:
    """Was im Text schon wie ein Platzhalter aussieht, mit oder ohne Klammern."""
    return {f"[{typ}_{number}]" for typ, number in _LITERAL_PLACEHOLDER.findall(text)}


def analyze(text: str) -> MaskResult:
    """Neue Sitzung: erkennen und maskieren. original_text ist der vereinheitlichte Text (mask.canonical)."""
    text = mask.canonical(text)
    reserved = _literal_placeholders(text)
    with _lock:
        session_id = vault.create_session()
        s = _Session(original_text=text)
        for f in detect_all(text, _active_detectors()):
            placeholder = vault.placeholder_for(session_id, f.text, f.typ, reserved)
            if all(f.end <= x.start or f.start >= x.end for x in s.spans):
                s.spans.append(Span(f.start, f.end, placeholder))
                if f.quelle == GlinerDetector.name and f.score < UNSURE_BELOW_SCORE:
                    s.unsure.add(placeholder)
        s.spans = mask.propagate(text, sorted(s.spans, key=lambda x: x.start), _all_mappings(session_id))
        hints = [f for d in _active_detectors() if hasattr(d, "uncertain") for f in d.uncertain(text)]
        s.hints = merge_findings(hints, text)
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
    term = " ".join(mask.canonical(term).split())
    if not term:
        raise ValueError("Leerer Begriff.")
    with _lock:
        s = _session(session_id)
        if not mask.occurrence_pattern(term).search(s.original_text):
            return _result(session_id, [WARN_TERM_NOT_FOUND.format(term=term)])
        placeholder = vault.placeholder_for(session_id, term, typ, _literal_placeholders(s.original_text))
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
    # Nur eigene Platzhalter: Ein wörtlich im Text stehender wird nicht ersetzt, restore() meldet ihn als unbekannt.
    sent = [p for p in dict.fromkeys(gate.PLACEHOLDER_RE.findall(masked)) if p in originals]
    result = _restore.restore(answer, originals, sent)
    # Ein Platzhalter kennt nur den vollen Wert. Stand er für einen Namensteil, kann das Eingesetzte falsch sein („Antrag“).
    parts = {
        (span.placeholder, s.original_text[span.start : span.end])
        for span in s.spans
        if span.name_part and span.placeholder[1:-1] in answer   # auch ohne Klammern wird ersetzt
        and not _AFTER_SALUTATION.search(s.original_text[: span.start])
    }
    result.warnings += [
        WARN_PART_RESTORED.format(platzhalter=p, teil=teil, wert=originals[p]) for p, teil in sorted(parts)
    ]
    log.info(
        "restore: Sitzung %s, unbekannt %s, verändert %d, fehlend %s",
        session_id[:8], result.unknown, len(result.changed), result.missing,
    )
    return result
