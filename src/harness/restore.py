"""Rückübersetzung: Platzhalter in der Antwort lokal durch die Originale ersetzen.

Die Rückübersetzung rät nie. Ersetzt wird nur, was eindeutig ist:
- [TYP_N] exakt, wenn der Platzhalter in der Sitzung steht.
- TYP_N ohne Klammern, ebenfalls eindeutig, aber mit Warnung.
Alles andere bleibt stehen und wird gemeldet.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .detect import TYPES

WARN_NO_BRACKETS = "{platzhalter} kam ohne Klammern zurück und wurde trotzdem ersetzt."
WARN_UNKNOWN = "Unbekannt, nicht ersetzt: {platzhalter}"
WARN_CHANGED = "Möglicherweise verändert, nicht ersetzt: „{fundstelle}“"
WARN_MISSING = "Nicht in der Antwort: {platzhalter}"


@dataclass
class RestoreResult:
    text: str
    unknown: list[str] = field(default_factory=list)    # Platzhalter, die nicht in der Sitzung stehen
    changed: list[str] = field(default_factory=list)    # verdächtige Formen wie „Person 1“, nicht ersetzt
    missing: list[str] = field(default_factory=list)    # gesendete Platzhalter, die in der Antwort fehlen
    warnings: list[str] = field(default_factory=list)   # fertige deutsche Sätze


# Ein Treffer: optionale Klammer, Typname (beliebige Schreibweise), Trenner, Nummer, optionale Klammer.
_CANDIDATE = re.compile(
    r"(?P<open>\[\s*)?(?<![\w])(?P<typ>" + "|".join(TYPES) + r")(?P<sep>[ _\-]?)(?P<num>\d+)(?![\w])(?P<close>\s*\])?",
    re.IGNORECASE,
)


def _add(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def restore(answer: str, originals: dict[str, str], sent: list[str]) -> RestoreResult:
    """originals: Platzhalter → Original (aktiv in der Sitzung). sent: Platzhalter im gesendeten Text."""
    result = RestoreResult(text="")
    seen: set[str] = set()
    bare_warned: list[str] = []
    parts: list[str] = []
    pos = 0

    for m in _CANDIDATE.finditer(answer):
        typ, sep, num = m.group("typ"), m.group("sep"), m.group("num")
        opened, closed = m.group("open"), m.group("close")
        canonical = f"[{typ.upper()}_{num}]"
        exact_form = typ.isupper() and sep == "_"

        if exact_form and opened == "[" and closed == "]":
            # Exakt [TYP_N]
            if canonical in originals:
                parts.append(answer[pos : m.start()] + originals[canonical])
                pos = m.end()
                seen.add(canonical)
            else:
                _add(result.unknown, canonical)
        elif exact_form and not opened and not closed:
            # TYP_N ohne Klammern: eindeutig, also ersetzen, aber melden.
            if canonical in originals:
                parts.append(answer[pos : m.start()] + originals[canonical])
                pos = m.end()
                seen.add(canonical)
                _add(bare_warned, canonical[1:-1])
            else:
                _add(result.unknown, canonical[1:-1])
        else:
            # Alles andere („Person 1“, „PERSON1“, „[Person_1]“, halbe Klammern): nicht raten.
            _add(result.changed, m.group().strip())

    parts.append(answer[pos:])
    result.text = "".join(parts)

    for placeholder in sent:
        if placeholder not in seen:
            _add(result.missing, placeholder)

    result.warnings = (
        [WARN_NO_BRACKETS.format(platzhalter=p) for p in bare_warned]
        + [WARN_UNKNOWN.format(platzhalter=p) for p in result.unknown]
        + [WARN_CHANGED.format(fundstelle=c) for c in result.changed]
        + [WARN_MISSING.format(platzhalter=p) for p in result.missing]
    )
    return result
