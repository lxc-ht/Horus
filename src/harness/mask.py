"""Maskieren: Fundstellen im Originaltext durch Platzhalter ersetzen.

Der Zustand einer Sitzung ist der Originaltext plus eine Liste nicht überlappender
Stellen (Span) in Koordinaten des Originaltexts. Der maskierte Text wird daraus
jedes Mal neu gebaut, von hinten nach vorn, damit die Positionen stimmen.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .vault import Mapping


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


@dataclass(frozen=True)
class Span:
    start: int   # im Originaltext
    end: int
    placeholder: str


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


def occurrence_pattern(value: str) -> re.Pattern:
    """Findet value ohne Groß-/Kleinschreibung und mit beliebigem Leerraum zwischen den Wörtern."""
    words = value.split()
    return re.compile(r"\s+".join(re.escape(w) for w in words), re.IGNORECASE)


def add_occurrences(original: str, spans: list[Span], value: str, placeholder: str) -> list[Span]:
    """Maskiert jedes Vorkommen von value zusätzlich.

    Überlappt ein Vorkommen bestehende Stellen, wird es nur übernommen, wenn es sie
    vollständig enthält und länger ist (dann ersetzt es sie). Sonst bleibt der Bestand.
    """
    result = list(spans)
    if not value.split():
        return result
    for m in occurrence_pattern(value).finditer(original):
        start, end = m.start(), m.end()
        overlapping = [s for s in result if s.start < end and start < s.end]
        if not overlapping:
            result.append(Span(start, end, placeholder))
        elif all(start <= s.start and s.end <= end and (end - start) > (s.end - s.start) for s in overlapping):
            result = [s for s in result if s not in overlapping]
            result.append(Span(start, end, placeholder))
    return sorted(result, key=lambda s: s.start)


def propagate(original: str, spans: list[Span], mappings: list[Mapping]) -> list[Span]:
    """Maskiert jeden bekannten Originalwert überall im Text, längere Werte zuerst.

    So bekommt derselbe Wert überall denselben Platzhalter, auch wenn der Detektor
    nur eine Stelle gefunden hat.
    """
    for mapping in sorted(mappings, key=lambda m: -len(m.original)):
        spans = add_occurrences(original, spans, mapping.original, mapping.placeholder)
    return spans


def drop(spans: list[Span], placeholder: str) -> list[Span]:
    return [s for s in spans if s.placeholder != placeholder]
