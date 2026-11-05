"""Freigabe: Leck-Check vor dem Freigeben und Hash-Prüfung vor dem Senden."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone

from .vault import Mapping, normalize

LEAK_MESSAGE = "Gestoppt: Ein Originalwert steht noch im Text. Maskiere ihn oder nimm die Ersetzung bewusst zurück."
MISMATCH_MESSAGE = "Gestoppt: Der Text wurde nach der Freigabe geändert. Bitte erneut prüfen und freigeben."
NAME_PART_WARNING = "Achtung: „{teil}“ steht noch im Text und gehört vermutlich zu {platzhalter}."

PLACEHOLDER_RE = re.compile(r"\[[A-Z]+_\d+\]")

# Namensteile, die allein nichts über eine Person verraten.
_NAME_STOPWORDS = {"dr", "prof", "med", "herr", "frau", "von", "van", "der", "den", "die", "und", "zu"}


@dataclass
class Release:
    session_id: str
    text: str
    sha256: str
    created_at: str    # ISO 8601


class LeakError(Exception):
    """Ein Originalwert steht noch im Text. placeholders nennt die betroffenen Platzhalter, nie die Werte."""

    def __init__(self, placeholders: list[str] | None = None):
        super().__init__(LEAK_MESSAGE)
        self.placeholders = placeholders or []


class ReleaseMismatchError(Exception):
    def __init__(self, message: str = MISMATCH_MESSAGE):
        super().__init__(message)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _visible_text(masked_text: str) -> str:
    """Text ohne Platzhalter, normalisiert. Platzhalter werden durch \\x00 ersetzt, damit keine neuen Wortgrenzen entstehen."""
    return normalize(PLACEHOLDER_RE.sub("\x00", masked_text))


def find_leaks(masked_text: str, mappings: list[Mapping]) -> list[str]:
    """Platzhalter, deren Originalwert (ohne Groß-/Kleinschreibung) noch im Text steht."""
    visible = _visible_text(masked_text)
    return [m.placeholder for m in mappings if m.active and normalize(m.original) in visible]


def name_part_warnings(masked_text: str, mappings: list[Mapping]) -> list[str]:
    """Warnungen für einzelne Namensteile (ab 3 Zeichen) von Personen, die noch im Text stehen."""
    visible = PLACEHOLDER_RE.sub("\x00", masked_text)
    warnings: list[str] = []
    seen: set[str] = set()
    for m in mappings:
        if not m.active or m.typ != "PERSON":
            continue
        for part in re.split(r"[\s\-]+", m.original):
            part = part.strip(".,;:()\"'")
            if len(part) < 3 or part.lower() in _NAME_STOPWORDS or part.lower() in seen:
                continue
            if re.search(rf"(?<!\w){re.escape(part)}(?!\w)", visible, re.IGNORECASE):
                seen.add(part.lower())
                warnings.append(NAME_PART_WARNING.format(teil=part, platzhalter=m.placeholder))
    return warnings


def make_release(session_id: str, masked_text: str, mappings: list[Mapping]) -> Release:
    """Gibt genau diesen Text frei. LeakError, wenn ein Originalwert noch drinsteht."""
    leaks = find_leaks(masked_text, mappings)
    if leaks:
        raise LeakError(leaks)
    return Release(
        session_id=session_id,
        text=masked_text,
        sha256=sha256(masked_text),
        created_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def verify(rel: Release, current_text: str | None, issued: set[str]) -> None:
    """ReleaseMismatchError, wenn rel nicht mehr genau dem freigegebenen, aktuellen Text entspricht."""
    if sha256(rel.text) != rel.sha256:
        raise ReleaseMismatchError()
    if current_text is None or rel.text != current_text:
        raise ReleaseMismatchError()
    # Nur Freigaben, die release() selbst ausgestellt hat (und die seitdem nicht durch eine Änderung verfallen sind).
    if rel.sha256 not in issued:
        raise ReleaseMismatchError()
