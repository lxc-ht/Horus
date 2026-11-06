from types import SimpleNamespace

import pytest

from harness import cloud


def _stub(monkeypatch, stop_reason):
    response = SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text="Antwort an [PERSON_1]")])
    client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=lambda **_: response)))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "nur-fuer-den-test")
    monkeypatch.setattr(cloud.anthropic, "Anthropic", lambda: client)


def test_complete_answer_stays_unchanged(monkeypatch):
    _stub(monkeypatch, "end_turn")
    assert cloud.ask("x") == "Antwort an [PERSON_1]"


def test_truncated_answer_is_marked(monkeypatch):
    _stub(monkeypatch, "max_tokens")
    answer = cloud.ask("x")
    assert answer.startswith("Antwort an [PERSON_1]")
    assert answer.endswith(cloud.TRUNCATED_NOTE)


def test_refusal_is_an_error(monkeypatch):
    _stub(monkeypatch, "refusal")
    with pytest.raises(cloud.CloudError):
        cloud.ask("x")


def test_no_key_message_has_no_cli_instructions():
    # Die Weboberfläche kann den Satz zeigen, dort gibt es weder END noch eine automatisch gefüllte Zwischenablage.
    message = str(cloud.NoApiKeyError())
    assert message.startswith("Kein API-Key gefunden")
    assert "END" not in message and "Zwischenablage" not in message
