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

TYPES = ["PERSON", "FIRMA", "ADRESSE", "ORT", "EMAIL", "TELEFON", "IBAN", "DATUM", "KENNUNG"]

# Strukturierte Typen: hier ist Regex exakt und gewinnt bei Überlappungen.
STRUCTURED_TYPES = {"EMAIL", "IBAN", "TELEFON", "DATUM", "KENNUNG"}

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

_EMAIL = re.compile(r"(?<![\w.%+-])[\w.%+-]+@[\w.-]+\.[^\W\d_]{2,}(?![\w-])")

# IBAN in Blöcken (mit oder ohne Leerzeichen), allgemein: 2 Buchstaben, 2 Ziffern, bis 30 Zeichen.
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b")

# Telefonnummern: +Ländervorwahl / 0049 / führende 0, Trennzeichen Leerzeichen, - oder /.
_PHONE = re.compile(
    r"(?<![\w+])"
    r"(?:(?:\+\d{1,3}|0049)[ \-/]?(?:\(0\)[ \-/]?)?\(?\d{1,5}\)?|\(?0\d{2,5}\)?)"
    r"(?:[ \-/]?\d{2,}){1,4}"
    r"(?![\w])"
)

# Kennungen mit Bezeichner davor: Der Bezeichner verrät den Typ, der Wert darf fast jedes Format haben.
_LABELED_ID = re.compile(
    r"(?<!\w)(?i:Steuer-?ID|(?:Steuer)?identifikationsnummer|IdNr\.?|Steuernummer|St\.?-?Nr\.?"
    r"|SV-?(?:Nr\.?|Nummer)|Sozialversicherungsnummer|Versicherten-?(?:Nr\.?|Nummer)"
    r"|Aktenzeichen|Az\.?|Gesch[äa]ftszeichen|Mandanten-?(?:Nr\.?|Nummer)|Patienten-?(?:Nr\.?|Nummer)"
    r"|Personalausweis-?(?:Nr\.?|Nummer)|Kennzeichen)"
    # Wert: Blöcke aus Großbuchstaben und Ziffern. Ein Punkt am Blockende beendet ihn, sonst käme der nächste Satz mit.
    r"[\s:.#]*(?P<value>[A-ZÄÖÜ0-9](?:[A-ZÄÖÜ0-9./\-]*[A-ZÄÖÜ0-9])?(?!\w)(?: [A-ZÄÖÜ0-9](?:[A-ZÄÖÜ0-9./\-]*[A-ZÄÖÜ0-9])?(?!\w))*)"
)

# Steuer-ID ohne Bezeichner, 11 Stellen. Zählt nur mit gültiger Prüfziffer, sonst wäre jede lange Zahl eine Kennung.
# Steuernummern sind ohne Bezeichner nicht von Rechnungs- oder Aktennummern zu unterscheiden, sie kommen nur über _LABELED_ID.
_TAX_ID = re.compile(r"(?<![\d/.,])[1-9]\d(?: ?\d{3}){3}(?![\d/.,]\d)")

# Kennungen, deren Format auch ohne Bezeichner eindeutig genug ist. Jedes Muster enthält Buchstaben oder Schrägstrich-Struktur,
# eine nackte Zahl allein ist nie eine Kennung.
_BARE_IDS = [
    re.compile(r"\b\d{2} ?\d{6} ?[A-Z] ?\d{3}\b"),                           # SV-Nummer
    re.compile(r"\b[A-Z]\d{9}\b"),                                           # Krankenversichertennummer
    re.compile(r"(?<![\w/])(?:\d{1,3}|[IVX]+) [A-Z][A-Za-z]{0,2} \d{1,6}/\d{2,4}\b"),  # Aktenzeichen 3 O 123/26
    re.compile(r"(?<![\w@.])(?:https?://|www\.)[^\s<>\"']+"),                # URL, kann Patienten- oder Fallnummern enthalten
]

# Eindeutige Straßenendungen zählen immer, mehrdeutige („Bundesgerichtshof 12“) nur mit „Am …“ davor oder PLZ dahinter.
_STREET_SUFFIXES = "straße|strasse|str\\.|weg|gasse|allee|ring|damm|ufer|chaussee|pfad|steig|stieg"
_PLACE_SUFFIXES = "platz|berg|bach|hof|feld|garten|kamp|bahn|markt|wall|graben|deich"
_NOT_STREET = r"(?!(?:Rechts|Dienst|Instanzen)weg\b|Arbeitsplatz\b)"
_HOUSE_NUMBER = r"\s+\d{1,4}(?:\s?[a-zA-Z](?!\w)|\s?[\-/]\s?\d{1,4})?"
_POSTCODE_CITY = (
    r"\d{5}\s+(?!(?:Euro|EUR|Dollar|Stück|Menschen|Personen|Kunden|Mitarbeiter)\b)[A-ZÄÖÜ][\w\-]+"
    r"(?:\s+(?:im|am|an der|bei|ob der)\s+[A-ZÄÖÜ][\w\-]+)?"
)
# Straße mit Hausnummer, optional mit PLZ und Ort dahinter.
_ADDRESS = re.compile(
    r"(?<![\w\-])(?:"
    rf"(?:(?:Am|An der|Auf der|Auf dem|Im|In der|Zum|Zur)\s+)?{_NOT_STREET}"
    rf"(?:[A-ZÄÖÜ][\w\-]*(?:{_STREET_SUFFIXES})"
    r"|(?!(?:Der|Die|Das|Diese[rs]?|Eine?)\b)[A-ZÄÖÜ][\w\-]+(?:\s+|-)(?:Straße|Strasse|Str\.|Weg|Platz|Allee|Gasse|Ring|Damm|Ufer))"
    rf"{_HOUSE_NUMBER}(?:,?\s+{_POSTCODE_CITY})?"
    rf"|(?:Am|An der|Auf der|Auf dem|Zum|Zur)\s+{_NOT_STREET}[A-ZÄÖÜ][\w\-]*(?:{_PLACE_SUFFIXES}){_HOUSE_NUMBER}(?:,?\s+{_POSTCODE_CITY})?"
    rf"|{_NOT_STREET}[A-ZÄÖÜ][\w\-]*(?:{_PLACE_SUFFIXES}){_HOUSE_NUMBER},?\s+{_POSTCODE_CITY}"
    r")"
)
# PLZ und Ort allein. Nur nach einem Trenner oder „in“, sonst wären „es kamen 50000 Gäste“ auch Adressen.
_POSTCODE_ALONE = re.compile(rf"(?<!\d){_POSTCODE_CITY}")
_BEFORE_POSTCODE = re.compile(r"(?:^|[,:;(\n]|(?<!\w)(?:[Ii]n|aus|nach|bei|von|PLZ))[ \t]*$")

_NAME_WORD = r"[^\W\d_]+(?:['’\-][^\W\d_]+)*"   # alle Schriften: Nguyễn, Çelik, O'Neill, Müller-Lüdenscheidt
_NAME_PARTICLES = {"von", "van", "de", "der", "den", "zu", "la", "di", "da", "del", "ten", "ter"}
# Anrede oder Titel, dahinter bis zu vier Wörter. Welche davon zum Namen gehören, entscheidet _salutation_name().
_SALUTATION = re.compile(
    r"(?<!\w)(?:(?i:Herrn?|Frau)|Dr\.|Prof\.)\s+(?:(?:Dr\.|Prof\.|med\.|jur\.|rer\.|nat\.)\s+)*"
    # Nur vorausschauen: Die Wörter dürfen die nächste Anrede nicht verbrauchen („Frau Çelik schreibt Herrn Šimić“).
    rf"(?=(?P<name>{_NAME_WORD}(?: {_NAME_WORD}){{0,3}}))"
)

_MONTHS = "Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember"
_DATE = re.compile(
    r"\b(?:"
    r"\d{1,2}\.\d{1,2}\.(?:\d{4}|\d{2})"            # 14.03.1979, 1.3.79
    r"|\d{4}-\d{2}-\d{2}"                           # 1979-03-14
    rf"|\d{{1,2}}\. ?(?:{_MONTHS}) \d{{4}}"         # 14. März 1979
    r")(?!\d)"
)


def _tax_id_valid(raw: str) -> bool:
    """Prüfziffer der Steuer-ID nach ISO 7064 (MOD 11,10)."""
    digits = [int(c) for c in raw if c.isdigit()]
    if len(digits) != 11:
        return False
    product = 10
    for d in digits[:10]:
        total = (d + product) % 10 or 10
        product = total * 2 % 11
    return (11 - product) % 10 == digits[10]


def _salutation_name(m: re.Match) -> tuple[int, int] | None:
    """Position des Namens hinter einer Anrede: überspringt Berufe, endet am ersten kleingeschriebenen Wort."""
    start = end = None
    for word in re.finditer(r"\S+", m.group("name")):
        value = word.group()
        if value.lower() in _ROLE_WORDS:
            if end is not None:
                break
        elif value[0].isupper():
            start = word.start() if start is None else start
            end = word.end()
        elif value in _NAME_PARTICLES:
            start = word.start() if start is None else start
        else:
            break
    if end is None:
        return None
    offset = m.start("name")
    return offset + start, offset + end


def _iban_valid(raw: str) -> bool:
    """Prüfsumme nach ISO 13616 (mod 97)."""
    s = raw.replace(" ", "")
    if not 15 <= len(s) <= 34:
        return False
    rearranged = s[4:] + s[:4]
    digits = "".join(str(int(c, 36)) for c in rearranged)
    return int(digits) % 97 == 1


class RegexDetector:
    """EMAIL, IBAN, TELEFON, DATUM, KENNUNG sowie ADRESSE und PERSON als Netz, falls das Modell sie übersieht."""

    name = "regex"

    def detect(self, text: str) -> list[Finding]:
        found: list[Finding] = []

        def add(m: re.Match, typ: str, group: str | int = 0) -> None:
            found.append(Finding(m.start(group), m.end(group), m.group(group), typ, self.name, 1.0))

        # Kennungen vor TELEFON: Bei gleicher Länge gewinnt, was zuerst gefunden wurde („022/815/08150“).
        for m in _LABELED_ID.finditer(text):
            if any(c.isdigit() for c in m.group("value")):
                add(m, "KENNUNG", "value")
        for m in _TAX_ID.finditer(text):
            if _tax_id_valid(m.group()):
                add(m, "KENNUNG")
        for pattern in _BARE_IDS:
            for m in pattern.finditer(text):
                add(m, "KENNUNG")
        for m in _ADDRESS.finditer(text):
            add(m, "ADRESSE")
        for m in _POSTCODE_ALONE.finditer(text):
            if _BEFORE_POSTCODE.search(text[max(0, m.start() - 8) : m.start()]):
                add(m, "ADRESSE")
        for m in _SALUTATION.finditer(text):
            if (span := _salutation_name(m)) is not None:
                found.append(Finding(span[0], span[1], text[span[0] : span[1]], "PERSON", self.name, 1.0))
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
    "doktor", "rechtsanwalt", "rechtsanwältin", "anwalt", "anwältin", "richter", "richterin", "notar", "notarin",
    "professor", "professorin", "steuerberater", "steuerberaterin", "vorsitzender", "vorsitzende",
}
_NOT_A_NAME = _ROLE_WORDS | {"herr", "herrn", "frau"}

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


def _split_long(offset: int, chunk: str, max_chars: int, overlap: int = 100) -> list[tuple[int, str]]:
    """Teilt ein zu langes Stück an Leerzeichen, sonst hart. Alles dahinter sähe das Modell sonst nie.

    Die Stücke überlappen, damit ein Name an der Schnittstelle in einem davon ganz steht.
    Doppelte Fundstellen löst merge_findings() auf.
    """
    pieces: list[tuple[int, str]] = []
    start = 0
    while len(chunk) - start > max_chars:
        cut = chunk.rfind(" ", start + overlap + 1, start + max_chars)
        if cut == -1:
            cut = start + max_chars
        pieces.append((offset + start, chunk[start:cut]))
        start = cut - overlap
    pieces.append((offset + start, chunk[start:]))
    return pieces


def _chunks(text: str, max_chars: int = 800) -> list[tuple[int, str]]:
    """Teilt den Text an Zeilengrenzen in Stücke, die GLiNER verarbeiten kann.

    Liefert (Offset, Stück). Überlange Zeilen werden an Satzenden geteilt,
    Sätze über max_chars an Leerzeichen.
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
    return [split for offset, chunk in chunks for split in _split_long(offset, chunk, max_chars)]


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
    if f.typ == "PERSON":
        # Anrede und Beruf gehören nicht zum Wert, sonst ergibt die Rückübersetzung „Frau Frau Muster“.
        while (m := re.match(r"(\S+)\s+", text[start:end])) and m[1].lower() in _NOT_A_NAME:
            start += m.end()
        if text[start:end].lower() in _NOT_A_NAME:
            return None
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


def _drop_name_variants(findings: list[Finding]) -> list[Finding]:
    """Verwirft „Kettelhut“ aus „Frau Kettelhut“, wenn „Sabine Kettelhut“ auch gefunden wurde.

    Sonst bekäme dieselbe Person zwei Platzhalter. Den Namensteil maskiert danach mask.propagate().
    """
    persons = [(f, set(f.text.lower().split())) for f in findings if f.typ == "PERSON"]

    def is_variant(f: Finding) -> bool:
        parts = set(f.text.lower().split())
        return f.quelle == RegexDetector.name and f.typ == "PERSON" and any(parts < other for _, other in persons)

    return [f for f in findings if not is_variant(f)]


def detect_all(text: str, detectors: list[Detector]) -> list[Finding]:
    found: list[Finding] = []
    for d in detectors:
        found.extend(d.detect(text))
    return _drop_name_variants(merge_findings(found, text))
