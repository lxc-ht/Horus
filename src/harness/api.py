"""Der Vertrag des Harness-Kerns. Die Weboberfläche importiert NUR dieses Modul.

Signaturen, Feldnamen und Ausnahmen bleiben stabil. Ergänzungen nur zusätzlich
und mit Eintrag in BACKLOG.md unter „Vertrag erweitert“.
"""

from dataclasses import dataclass

TYPES = ["PERSON", "FIRMA", "ADRESSE", "ORT", "EMAIL", "TELEFON", "IBAN", "DATUM"]


@dataclass
class Replacement:
    placeholder: str   # "[PERSON_1]"
    original: str      # "Max Müller"  (nur lokal, für die Anzeige)
    typ: str           # einer aus TYPES
    start: int         # Position im maskierten Text
    end: int


@dataclass
class MaskResult:
    session_id: str
    original_text: str
    masked_text: str
    replacements: list[Replacement]   # nach start sortiert
    warnings: list[str]               # fertige deutsche Sätze


@dataclass
class Release:
    session_id: str
    text: str
    sha256: str
    created_at: str    # ISO 8601


@dataclass
class RestoreResult:
    text: str
    unknown: list[str]    # Platzhalter, die nicht in der Sitzung stehen
    changed: list[str]    # verdächtige Formen wie „Person 1“, nicht ersetzt
    missing: list[str]    # gesendete Platzhalter, die in der Antwort fehlen
    warnings: list[str]   # fertige deutsche Sätze


class LeakError(Exception): ...
class ReleaseMismatchError(Exception): ...
class NoApiKeyError(Exception): ...


def analyze(text: str) -> MaskResult:
    """Neue Sitzung: erkennen und maskieren."""
    raise NotImplementedError


def add_manual(session_id: str, term: str, typ: str) -> MaskResult:
    """Jedes Vorkommen von term zusätzlich maskieren."""
    raise NotImplementedError


def remove(session_id: str, placeholder: str) -> MaskResult:
    """Ersetzung zurücknehmen."""
    raise NotImplementedError


def get(session_id: str) -> MaskResult:
    raise NotImplementedError


def release(session_id: str) -> Release:
    """Gibt den AKTUELLEN maskierten Text frei, LeakError bei Leck."""
    raise NotImplementedError


def has_api_key() -> bool:
    raise NotImplementedError


def send(rel: Release) -> str:
    """Antwort von Claude; ReleaseMismatchError / NoApiKeyError."""
    raise NotImplementedError


def restore(session_id: str, answer: str) -> RestoreResult:
    raise NotImplementedError
