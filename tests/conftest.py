"""Testaufbau: eigene SQLite-Datei pro Test, Regex + Fake-Detektor statt GLiNER, kein Netz."""

from __future__ import annotations

import re

import pytest

from harness import api, cloud
from harness.detect import Finding, RegexDetector


class FakeDetector:
    """Findet feste Begriffe wie ein Modell, aber ohne Download. terms: Begriff → Typ.

    first_only=True simuliert ein Modell, das nur die erste Stelle erkennt.
    """

    name = "fake"

    def __init__(self, terms: dict[str, str], first_only: bool = False):
        self.terms = terms
        self.first_only = first_only

    def detect(self, text: str) -> list[Finding]:
        found = []
        for term, typ in self.terms.items():
            for m in re.finditer(re.escape(term), text):
                found.append(Finding(m.start(), m.end(), term, typ, self.name, 0.9))
                if self.first_only:
                    break
        return found


KANZLEI_TERMS = {
    "Jonas Weidenfeld": "PERSON",
    "Theresa Kolbinger": "PERSON",
    "Grauberg Wohnbau GmbH": "FIRMA",
    "Lindenhofweg 17, 34127 Kassel": "ADRESSE",
}

SAMPLE = (
    "Mandant: Jonas Weidenfeld, geboren am 14.03.1979\n"
    "E-Mail: j.weidenfeld@example.org, Telefon +49 561 7712093\n"
    "Jonas Weidenfeld hat von der Grauberg Wohnbau GmbH die Kündigung erhalten. "
    "Ansprechpartnerin ist Theresa Kolbinger.\n"
    "Herr Weidenfeld zahlt von IBAN DE89 3704 0044 0532 0130 00.\n"
)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_DB", str(tmp_path / "vault.sqlite"))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(cloud, "_load_env", lambda: None)   # keine echte .env lesen
    api.set_detectors([RegexDetector(), FakeDetector(KANZLEI_TERMS)])
    yield
    api.set_detectors(None)
    api._sessions.clear()
