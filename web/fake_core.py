"""Attrappe des Kerns: erfüllt nur den Vertrag von harness.api, schützt aber nichts.

Sie erkennt absichtlich nur E-Mails und eine feste Liste erfundener Namen.
"""
import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

TYPES = ["PERSON", "FIRMA", "ADRESSE", "ORT", "EMAIL", "TELEFON", "IBAN", "DATUM"]

_NAMES = ["Erika Musterfrau", "Max Mustermann", "Anna Beispiel", "Jonas Probe"]
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PLACEHOLDER = re.compile(r"\[[A-ZÄÖÜ]+_\d+\]")
_VARIANT = re.compile(r"\[[^\]\n]*_\d+\]")
_WARNING = "Die Attrappe erkennt nur E-Mails und eine feste Namensliste. Prüfe den Text genau."


@dataclass
class Replacement:
    placeholder: str
    original: str
    typ: str
    start: int
    end: int


@dataclass
class MaskResult:
    session_id: str
    original_text: str
    masked_text: str
    replacements: list[Replacement]
    warnings: list[str]


@dataclass
class Release:
    session_id: str
    text: str
    sha256: str
    created_at: str


@dataclass
class RestoreResult:
    text: str
    unknown: list[str]
    changed: list[str]
    missing: list[str]
    warnings: list[str]


class LeakError(Exception):
    pass


class ReleaseMismatchError(Exception):
    pass


class NoApiKeyError(Exception):
    pass


@dataclass
class _Entry:
    placeholder: str
    original: str
    typ: str


class _Session:
    def __init__(self, text: str):
        self.text = text
        self.entries: list[_Entry] = []
        self.counters: dict[str, int] = {}

    def add(self, original: str, typ: str) -> None:
        if any(e.original == original for e in self.entries):
            return
        # Nummern werden nie neu vergeben, sonst zeigt [PERSON_1] plötzlich auf jemand anderen.
        self.counters[typ] = self.counters.get(typ, 0) + 1
        self.entries.append(_Entry(f"[{typ}_{self.counters[typ]}]", original, typ))


_sessions: dict[str, _Session] = {}


def _session(session_id: str) -> _Session:
    if session_id not in _sessions:
        raise ValueError("Diese Sitzung ist unbekannt. Bitte den Text neu analysieren.")
    return _sessions[session_id]


def _mask(session_id: str) -> MaskResult:
    session = _session(session_id)
    by_original = {e.original: e for e in session.entries}
    replacements: list[Replacement] = []
    parts: list[str] = []
    position = 0  # Position im maskierten Text
    last = 0  # Position im Original
    if by_original:
        # Längste zuerst, damit "Max Mustermann" nicht an "Max" hängen bleibt.
        pattern = "|".join(re.escape(o) for o in sorted(by_original, key=len, reverse=True))
        for match in re.finditer(pattern, session.text):
            entry = by_original[match.group()]
            plain = session.text[last:match.start()]
            parts += [plain, entry.placeholder]
            position += len(plain)
            replacements.append(
                Replacement(entry.placeholder, entry.original, entry.typ, position, position + len(entry.placeholder))
            )
            position += len(entry.placeholder)
            last = match.end()
    parts.append(session.text[last:])
    return MaskResult(session_id, session.text, "".join(parts), replacements, [_WARNING])


def analyze(text: str) -> MaskResult:
    session_id = uuid.uuid4().hex
    session = _Session(text)
    _sessions[session_id] = session
    found = [(m.start(), m.group(), "EMAIL") for m in _EMAIL.finditer(text)]
    found += [(m.start(), name, "PERSON") for name in _NAMES for m in re.finditer(re.escape(name), text)]
    for _, original, typ in sorted(found):
        session.add(original, typ)
    return _mask(session_id)


def add_manual(session_id: str, term: str, typ: str) -> MaskResult:
    session = _session(session_id)
    if typ not in TYPES:
        raise ValueError(f"Den Typ {typ} gibt es nicht.")
    term = term.strip()
    visible = _PLACEHOLDER.sub("\0", _mask(session_id).masked_text)
    if not term or term not in visible:
        raise ValueError("Dieser Text steht nicht im maskierten Text und kann nicht ersetzt werden.")
    session.add(term, typ)
    return _mask(session_id)


def remove(session_id: str, placeholder: str) -> MaskResult:
    session = _session(session_id)
    remaining = [e for e in session.entries if e.placeholder != placeholder]
    if len(remaining) == len(session.entries):
        raise ValueError(f"Den Platzhalter {placeholder} gibt es in dieser Sitzung nicht.")
    session.entries = remaining
    return _mask(session_id)


def get(session_id: str) -> MaskResult:
    return _mask(session_id)


def release(session_id: str) -> Release:
    text = _mask(session_id).masked_text
    if any(e.original in text for e in _session(session_id).entries):
        raise LeakError("Im Text steht noch eine ersetzte Angabe im Klartext. Die Freigabe wurde abgelehnt.")
    digest = hashlib.sha256(text.encode()).hexdigest()
    return Release(session_id, text, digest, datetime.now(timezone.utc).isoformat())


def has_api_key() -> bool:
    return False


def send(rel: Release) -> str:
    if hashlib.sha256(rel.text.encode()).hexdigest() != rel.sha256 or rel.text != _mask(rel.session_id).masked_text:
        raise ReleaseMismatchError("Der Text passt nicht zur Freigabe. Bitte neu freigeben.")
    raise NoApiKeyError("Es ist kein API-Key gesetzt. Nutze den Kopier-Modus.")


def restore(session_id: str, answer: str) -> RestoreResult:
    known = {e.placeholder: e.original for e in _session(session_id).entries}
    seen = set(_PLACEHOLDER.findall(answer))
    unknown = sorted(seen - set(known))
    missing = sorted(set(known) - seen)
    changed = sorted(set(_VARIANT.findall(answer)) - seen)
    text = _PLACEHOLDER.sub(lambda m: known.get(m.group(), m.group()), answer)
    return RestoreResult(text, unknown, changed, missing, [])
