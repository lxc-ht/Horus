"""Maskieren: Fundstellen im Originaltext durch Platzhalter ersetzen.

Der Zustand einer Sitzung ist der Originaltext plus eine Liste nicht überlappender
Stellen (Span) in Koordinaten des Originaltexts. Der maskierte Text wird daraus
jedes Mal neu gebaut, von hinten nach vorn, damit die Positionen stimmen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .vault import Mapping


@dataclass
class Replacement:
    placeholder: str   # "[PERSON_1]"
    original: str      # "Max Müller"  (nur lokal, für die Anzeige)
    typ: str           # einer aus TYPES
    start: int         # Position im maskierten Text
    end: int


@dataclass
class Uncertain:
    """Eine Stelle, die der Mensch vor der Freigabe ansehen soll."""
    text: str       # der Wert im Klartext (nur lokal, für die Anzeige)
    typ: str        # Vorschlag aus TYPES
    start: int      # Position im maskierten Text
    end: int
    masked: bool    # True: steckt schon hinter einem Platzhalter, False: steht im Klartext
    reason: str     # fertiger deutscher Satz


@dataclass
class MaskResult:
    session_id: str
    original_text: str
    masked_text: str
    replacements: list[Replacement]   # nach start sortiert
    warnings: list[str]               # fertige deutsche Sätze
    uncertain: list[Uncertain] = field(default_factory=list)   # nach start sortiert


@dataclass(frozen=True)
class Span:
    start: int   # im Originaltext
    end: int
    placeholder: str
    name_part: bool = False   # nur ein Namensteil einer Person, wird bei propagate() neu berechnet


# Namensteile, die allein nichts über eine Person verraten.
NAME_STOPWORDS = {"dr", "prof", "med", "herr", "frau", "von", "van", "der", "den", "die", "und", "zu"}


def build(original: str, spans: list[Span], types: dict[str, str]) -> tuple[str, list[Replacement]]:
    """Baut den maskierten Text. types: Platzhalter → Typ."""
    ordered = sorted(spans, key=lambda s: s.start)
    masked = original
    for span in reversed(ordered):
        masked = masked[: span.start] + span.placeholder + masked[span.end :]

    replacements: list[Replacement] = []
    shift = 0
    for span in ordered:
        start = span.start + shift
        end = start + len(span.placeholder)
        replacements.append(
            Replacement(span.placeholder, original[span.start : span.end], types[span.placeholder], start, end)
        )
        shift += len(span.placeholder) - (span.end - span.start)
    return masked, replacements


# Gleichwertige Schreibweisen: „Müller“ und „Mueller“, „Weiß“ und „WEISS“.
_SPELLINGS = {
    "ä": "(?:ä|ae)", "ae": "(?:ä|ae)", "ö": "(?:ö|oe)", "oe": "(?:ö|oe)",
    "ü": "(?:ü|ue)", "ue": "(?:ü|ue)", "ß": "(?:ß|ss)", "ss": "(?:ß|ss)",
}
_SPELLING_RE = re.compile("|".join(sorted(_SPELLINGS, key=len, reverse=True)), re.IGNORECASE)


def occurrence_pattern(value: str, whole_word: bool = False) -> re.Pattern:
    """Findet value ohne Groß-/Kleinschreibung, mit beliebigem Leerraum zwischen den Wörtern
    und in gleichwertiger Schreibweise.

    whole_word=True: nur als ganzes Wort, nie mitten in einem längeren Wort. Ein Genitiv-s
    gehört noch zum Wort, bleibt aber außerhalb des Treffers: „[PERSON_1]s Antrag“.
    """
    words = value.split()
    body = r"\s+".join(
        _SPELLING_RE.sub(lambda m: _SPELLINGS[m.group().lower().replace("ſ", "s")], re.escape(w)) for w in words
    )
    if whole_word:
        body = rf"(?<!\w){body}(?=s?(?!\w))"
    return re.compile(body, re.IGNORECASE)


def name_parts(value: str) -> list[str]:
    """Einzelne Namensteile ab 3 Zeichen, ohne nichtssagende Teile wie „Frau“ oder „Dr.“."""
    parts: list[str] = []
    for part in re.split(r"[\s\-]+", value):
        part = part.strip(".,;:()\"'")
        if len(part) >= 3 and part.lower() not in NAME_STOPWORDS and part.lower() not in parts:
            parts.append(part.lower())
    return parts


def _fold(value: str) -> str:
    """Einheitliche Schreibweise, damit „Müller“ und „Mueller“ als derselbe Namensteil zählen."""
    return value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")


def name_part_owners(mappings: list[Mapping]) -> dict[str, list[str]]:
    """Namensteil (klein geschrieben) → Platzhalter aller Personen, zu denen er gehört.

    Schlüssel ist die zuerst gesehene Schreibweise. Teile, die sich nur darin unterscheiden, sind
    ein Teil: Die Suche träfe beide, also wäre sonst still die falsche Person eingesetzt.
    """
    owners: dict[str, list[str]] = {}
    spellings: dict[str, str] = {}
    for m in mappings:
        if m.typ != "PERSON":
            continue
        for part in name_parts(m.original):
            placeholders = owners.setdefault(spellings.setdefault(_fold(part), part), [])
            if m.placeholder not in placeholders:
                placeholders.append(m.placeholder)
    return owners


def _accept(original: str, match: re.Match, value: str, whole_word: bool) -> bool:
    """Exakte Treffer gelten immer. Schreibweisen und Genitiv nur als großgeschriebenes ganzes Wort.

    Sonst würde „März“ bei einer Person „Mae“ zerschnitten und „links“ bei „Anna Link“ zum Namen.
    Kleingeschriebenes bleibt stehen, dafür warnt gate.name_part_warnings().
    """
    start, end = match.span()
    genitive = whole_word and original[end : end + 1].lower() == "s"
    if " ".join(match.group().split()).lower() == " ".join(value.split()).lower() and not genitive:
        return True
    next_char = "" if genitive else original[end : end + 1]
    bounded = not re.match(r"\w", original[start - 1 : start] if start else "") and not re.match(r"\w", next_char)
    return bounded and match.group()[0].isupper()


def add_occurrences(
    original: str, spans: list[Span], value: str, placeholder: str,
    whole_word: bool = False, name_part: bool = False,
) -> list[Span]:
    """Maskiert jedes Vorkommen von value zusätzlich.

    Überlappt ein Vorkommen bestehende Stellen, wird es nur übernommen, wenn es sie
    vollständig enthält und länger ist (dann ersetzt es sie). Sonst bleibt der Bestand.
    """
    result = list(spans)
    if not value.split():
        return result
    for m in occurrence_pattern(value, whole_word).finditer(original):
        if not _accept(original, m, value, whole_word):
            continue
        start, end = m.start(), m.end()
        overlapping = [s for s in result if s.start < end and start < s.end]
        if not overlapping:
            result.append(Span(start, end, placeholder, name_part))
        elif all(start <= s.start and s.end <= end and (end - start) > (s.end - s.start) for s in overlapping):
            result = [s for s in result if s not in overlapping]
            result.append(Span(start, end, placeholder, name_part))
    return sorted(result, key=lambda s: s.start)


def propagate(original: str, spans: list[Span], mappings: list[Mapping]) -> list[Span]:
    """Maskiert jeden bekannten Originalwert überall im Text, längere Werte zuerst.

    So bekommt derselbe Wert überall denselben Platzhalter, auch wenn der Detektor
    nur eine Stelle gefunden hat.

    Danach einzelne Namensteile von Personen („Frau Musterfrau“ → „Frau [PERSON_1]“),
    aber nur als ganzes Wort und nur, wenn der Teil zu genau einer Person der Sitzung
    gehört. Zurückgenommene Personen (active=False) zählen dabei mit: Ihre Teile werden
    nicht wieder maskiert, machen einen gleichen Teil einer anderen Person aber
    mehrdeutig. Mehrdeutiges bleibt stehen, dafür warnt gate.name_part_warnings().

    mappings darf zurückgenommene Werte enthalten, maskiert werden nur aktive.
    """
    # Namensteile jedes Mal neu berechnen: Eine neue Person kann einen Teil mehrdeutig machen.
    spans = [s for s in spans if not s.name_part]
    active = [m for m in mappings if m.active]
    for mapping in sorted(active, key=lambda m: -len(m.original)):
        spans = add_occurrences(original, spans, mapping.original, mapping.placeholder)
    active_placeholders = {m.placeholder for m in active}
    for part, placeholders in name_part_owners(mappings).items():
        if len(placeholders) == 1 and placeholders[0] in active_placeholders:
            spans = add_occurrences(original, spans, part, placeholders[0], whole_word=True, name_part=True)
    return spans


def drop(spans: list[Span], placeholder: str) -> list[Span]:
    return [s for s in spans if s.placeholder != placeholder]
