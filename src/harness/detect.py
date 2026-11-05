"""Erkennung sensibler Angaben.

Ein Detektor liefert Fundstellen (start, end, text, typ, quelle, score). Weitere
Detektoren (z. B. ein lokales LLM) implementieren dieselbe Schnittstelle und
werden über merge_findings() zusammengeführt.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Protocol

TYPES = ["PERSON", "FIRMA", "ADRESSE", "ORT", "EMAIL", "TELEFON", "IBAN", "DATUM"]

# Strukturierte Typen: hier ist Regex exakt und gewinnt bei Überlappungen.
STRUCTURED_TYPES = {"EMAIL", "IBAN", "TELEFON", "DATUM"}

# Zeichen, die am Rand einer Fundstelle nicht zum Wert gehören.
_EDGE_CHARS = " \t\r\n,;:.!?()[]{}\"'„“”‚‘’«»"


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    text: str
    typ: str
    quelle: str   # Name des Detektors, z. B. "regex" oder "gliner"
    score: float


class Detector(Protocol):
    name: str

    def detect(self, text: str) -> list[Finding]: ...


# --- Regex -----------------------------------------------------------------

_EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w-])")

# IBAN in Blöcken (mit oder ohne Leerzeichen), allgemein: 2 Buchstaben, 2 Ziffern, bis 30 Zeichen.
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b")

# Deutsche Telefonnummern: +49 / 0049 / führende 0, Trennzeichen Leerzeichen, - oder /.
_PHONE = re.compile(
    r"(?<![\w+])"
    r"(?:(?:\+|00)49[ \-/]?(?:\(0\)[ \-/]?)?\(?\d{2,5}\)?|\(?0\d{2,5}\)?)"
    r"(?:[ \-/]?\d{2,}){1,4}"
    r"(?![\w])"
)

_MONTHS = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
_DATE = re.compile(
    r"\b(?:"
    r"\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})"            # 14.03.1979, 1.3.79
    r"|\d{4}-\d{2}-\d{2}"                           # 1979-03-14
    rf"|\d{{1,2}}\. ?(?:{_MONTHS}) \d{{4}}"         # 14. März 1979
    r")(?!\d)"
)


def _iban_valid(raw: str) -> bool:
    """Prüfsumme nach ISO 13616 (mod 97)."""
    s = raw.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1


class RegexDetector:
    """EMAIL, IBAN (DE und allgemein), TELEFON (deutsche Formate) und DATUM."""

    name = "regex"

    def detect(self, text: str) -> list[Finding]:
        found: list[Finding] = []

        def add(m: re.Match, typ: str) -> None:
            found.append(Finding(m.start(), m.end(), m.group(), typ, self.name, 1.0))

        for m in _EMAIL.finditer(text):
            add(m, "EMAIL")
        for m in _IBAN.finditer(text):
            compact = m.group().replace(" ", "")
            # Deutsche IBAN am Format erkennen, alle anderen nur mit gültiger Prüfsumme.
            if (compact.startswith("DE") and len(compact) == 22) or _iban_valid(m.group()):
                add(m, "IBAN")
        for m in _PHONE.finditer(text):
            if 6 <= sum(c.isdigit() for c in m.group()) <= 15:
                add(m, "TELEFON")
        for m in _DATE.finditer(text):
            add(m, "DATUM")
        return found


# --- GLiNER ----------------------------------------------------------------

GLINER_MODEL = "urchade/gliner_multi_pii-v1"

# GLiNER-Label → Typ des Harness
GLINER_LABELS = {
    "person": "PERSON",
    "organization": "FIRMA",
    "address": "ADRESSE",
    "city": "ORT",
}

# Rollenwörter, die das Modell gern als PERSON meldet, die aber niemanden benennen.
_ROLE_WORDS = {
    "mandant", "mandantin", "patient", "patientin", "vermieter", "vermieterin", "mieter", "mieterin",
    "kläger", "klägerin", "beklagte", "beklagter", "kollege", "kollegin", "kolleginnen", "kollegen",
    "ärztin", "arzt", "ansprechpartner", "ansprechpartnerin", "gesellschafter", "gesellschafterin",
}

_gliner_cache: dict[str, object] = {}


def _load_gliner(model_name: str):
    """Lädt das Modell einmal pro Prozess und verwendet es danach wieder."""
    if model_name not in _gliner_cache:
        os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
        from gliner import GLiNER  # spät importieren: torch braucht Sekunden

        _gliner_cache[model_name] = GLiNER.from_pretrained(model_name)
    return _gliner_cache[model_name]


def _chunks(text: str, max_chars: int = 800) -> list[tuple[int, str]]:
    """Teilt den Text an Zeilengrenzen in Stücke, die GLiNER verarbeiten kann.

    Liefert (Offset, Stück). Überlange Zeilen werden an Satzenden geteilt.
    """
    pieces: list[tuple[int, str]] = []
    pos = 0
    for line in text.splitlines(keepends=True):
        if len(line) <= max_chars:
            pieces.append((pos, line))
        else:
            sub = 0
            for m in re.finditer(r".*?(?:[.!?](?=\s)|$)\s*", line, re.S):
                if m.group():
                    pieces.append((pos + sub, m.group()))
                    sub += len(m.group())
        pos += len(line)

    chunks: list[tuple[int, str]] = []
    for offset, piece in pieces:
        if chunks and len(chunks[-1][1]) + len(piece) <= max_chars:
            chunks[-1] = (chunks[-1][0], chunks[-1][1] + piece)
        else:
            chunks.append((offset, piece))
    return chunks


class GlinerDetector:
    """PERSON, FIRMA, ADRESSE und ORT über urchade/gliner_multi_pii-v1."""

    name = "gliner"

    def __init__(self, threshold: float | None = None, model_name: str = GLINER_MODEL):
        if threshold is None:
            threshold = float(os.environ.get("HARNESS_GLINER_THRESHOLD", "0.5"))
        self.threshold = threshold
        self.model_name = model_name

    def detect(self, text: str) -> list[Finding]:
        model = _load_gliner(self.model_name)
        labels = list(GLINER_LABELS)
        found: list[Finding] = []
        for offset, chunk in _chunks(text):
            if not chunk.strip():
                continue
            for ent in model.predict_entities(chunk, labels, threshold=self.threshold):
                typ = GLINER_LABELS.get(ent["label"])
                if typ is None or (typ == "PERSON" and ent["text"].strip().lower() in _ROLE_WORDS):
                    continue
                start, end = offset + ent["start"], offset + ent["end"]
                found.append(Finding(start, end, text[start:end], typ, self.name, float(ent["score"])))
        return found


# --- Zusammenführen ----------------------------------------------------------

def _trim(f: Finding, text: str) -> Finding | None:
    """Schneidet Satzzeichen und Leerraum am Rand ab; verwirft zu kurze Fundstellen."""
    start, end = f.start, f.end
    while start < end and text[start] in _EDGE_CHARS:
        start += 1
    while end > start and text[end - 1] in _EDGE_CHARS:
        end -= 1
    if end - start < 2:
        return None
    return Finding(start, end, text[start:end], f.typ, f.quelle, f.score)


def merge_findings(findings: list[Finding], text: str) -> list[Finding]:
    """Löst Überlappungen auf und liefert nicht überlappende Fundstellen nach start sortiert.

    Bei strukturierten Typen gewinnt Regex (exakt bei IBAN und E-Mail),
    sonst die längere Stelle (das Modell ist bei Namen besser), dann der höhere Score.
    """
    cleaned = [t for f in findings if (t := _trim(f, text)) is not None]

    def priority(f: Finding) -> tuple:
        regex_structured = f.quelle == RegexDetector.name and f.typ in STRUCTURED_TYPES
        return (0 if regex_structured else 1, -(f.end - f.start), -f.score, f.start)

    accepted: list[Finding] = []
    for f in sorted(cleaned, key=priority):
        if all(f.end <= a.start or f.start >= a.end for a in accepted):
            accepted.append(f)
    return sorted(accepted, key=lambda f: f.start)


def detect_all(text: str, detectors: list[Detector]) -> list[Finding]:
    found: list[Finding] = []
    for d in detectors:
        found.extend(d.detect(text))
    return merge_findings(found, text)
