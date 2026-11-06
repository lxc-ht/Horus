"""Der einzige Weg nach draußen: freigegebenen Text an Claude senden.

Hier kommt nur Text an, den gate.verify() geprüft hat. Keine Zuordnung, keine Originale.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import anthropic
from dotenv import load_dotenv

log = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-5-5"

SYSTEM_PROMPT = (
    "Der folgende Text wurde pseudonymisiert. Platzhalter in eckigen Klammern wie [PERSON_1], "
    "[FIRMA_2] oder [IBAN_1] stehen für echte Angaben, die du nicht kennst. Übernimm jeden "
    "Platzhalter, den du verwendest, exakt in dieser Schreibweise, mit Klammern, Großbuchstaben "
    "und Nummer. Erfinde keine neuen Platzhalter und versuche nicht, die echten Angaben zu erraten."
)

# Modelle, die den serverseitigen Fallback bei Ablehnungen (refusal) unterstützen.
_FALLBACK_MODELS = {"claude-sonnet-5-5", "claude-opus-5-5", "claude-opus-5", "claude-fable-5-1"}

NO_KEY_MESSAGE = (
    # Neutral, weil auch die Weboberfläche ihn zeigen kann. Die Bedienhinweise gibt die CLI selbst.
    "Kein API-Key gefunden — Kopier-Modus. Der freigegebene Text kann kopiert und von Hand an Claude gegeben werden."
)


TRUNCATED_NOTE = "\n\nACHTUNG: Die Antwort wurde wegen des Längenlimits abgeschnitten und ist unvollständig."


class NoApiKeyError(Exception):
    def __init__(self, message: str = NO_KEY_MESSAGE):
        super().__init__(message)


class CloudError(Exception):
    """Claude war nicht erreichbar oder hat abgelehnt. Die Meldung enthält nie Text aus der Anfrage."""


def _load_env() -> None:
    root = Path(__file__).resolve().parents[2]
    for candidate in (root / ".env", Path.cwd() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)


def has_api_key() -> bool:
    _load_env()
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def model() -> str:
    _load_env()
    return os.environ.get("CLAUDE_MODEL", "").strip() or DEFAULT_MODEL


def ask(text: str) -> str:
    """Sendet text an Claude und liefert die Antwort als Text."""
    if not has_api_key():
        raise NoApiKeyError()
    model_id = model()
    extra: dict = {}
    if model_id in _FALLBACK_MODELS:
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    client = anthropic.Anthropic()
    log.info("Sende freigegebenen Text an %s (%d Zeichen)", model_id, len(text))
    try:
        response = client.beta.messages.create(
            model=model_id,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": text}],
            **extra,
        )
    except anthropic.AuthenticationError as e:
        raise CloudError("Der API-Key wurde abgelehnt. Bitte .env prüfen.") from e
    except anthropic.APIStatusError as e:
        raise CloudError(f"Claude-API meldet Fehler {e.status_code}.") from e
    except anthropic.APIConnectionError as e:
        raise CloudError("Claude-API nicht erreichbar. Bitte Verbindung prüfen.") from e

    if response.stop_reason == "refusal":
        raise CloudError("Claude hat die Anfrage abgelehnt.")
    answer = "".join(block.text for block in response.content if block.type == "text")
    if response.stop_reason == "max_tokens":
        # Der Teil kann brauchbar sein, also nicht verwerfen, aber sichtbar machen. send() liefert laut Vertrag nur Text.
        log.warning("Antwort wegen Längenlimit abgeschnitten")
        answer += TRUNCATED_NOTE
    return answer
