"""
Tests for app/llm.py — the provider-dialect negotiation.

Two providers are in play and they disagree about the request body. NVIDIA NIM
takes `max_tokens` and `temperature: 0`. Azure AI Foundry's gpt-5.6 refuses
both, with these exact messages, observed in production:

    "Unsupported parameter: 'max_tokens' is not supported with this model.
     Use 'max_completion_tokens' instead."
    "Unsupported value: 'temperature' does not support 0.0 with this model.
     Only the default (1) value is supported."

The alternative to negotiating was sniffing the hostname for "azure.com", which
breaks silently the day a provider renames a domain or a third one is added. So
these tests pin the learning behaviour, and especially the boundary: a 400 that
is NOT a parameter disagreement must surface, not be retried into a timeout.
"""

from __future__ import annotations

import json

import pytest

from app import llm


class FakeResponse:
    def __init__(self, status: int, payload: dict | str):
        self.status_code = status
        self._payload = payload
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict:
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


def reply(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


@pytest.fixture(autouse=True)
def clear_dialect():
    llm._DIALECT.clear()
    yield
    llm._DIALECT.clear()


def run(monkeypatch, responses: list[FakeResponse], **over):
    """Drive chat() against a scripted sequence, capturing each request body."""
    sent: list[dict] = []
    it = iter(responses)

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return next(it)

    monkeypatch.setattr(llm.requests, "post", fake_post)
    kwargs = dict(base="https://x.test/v1", key="k", model="m",
                  messages=[{"role": "user", "content": "hi"}], max_tokens=100)
    kwargs.update(over)
    return llm.chat(**kwargs), sent


def test_a_cooperative_provider_is_called_once(monkeypatch) -> None:
    text, sent = run(monkeypatch, [FakeResponse(200, reply("ok"))])
    assert text == "ok"
    assert len(sent) == 1
    assert sent[0]["max_tokens"] == 100
    assert sent[0]["temperature"] == 0.0


def test_the_token_parameter_is_renamed_on_request(monkeypatch) -> None:
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'max_tokens' is not supported with this model. "
        "Use 'max_completion_tokens' instead."}})
    text, sent = run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))])
    assert text == "ok"
    assert "max_tokens" not in sent[1]
    assert sent[1]["max_completion_tokens"] == 100


def test_an_unsupported_temperature_is_dropped_not_guessed(monkeypatch) -> None:
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported value: 'temperature' does not support 0.0 with this model. "
        "Only the default (1) value is supported."}})
    text, sent = run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))])
    assert text == "ok"
    assert "temperature" not in sent[1], "temperature should be omitted, not altered"


def test_both_disagreements_are_learned_in_one_call(monkeypatch) -> None:
    """Azure gpt-5.6 refuses both, one error at a time."""
    tok = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'max_tokens' ... Use 'max_completion_tokens' instead."}})
    temp = FakeResponse(400, {"error": {"message":
        "Unsupported value: 'temperature' does not support 0.0 with this model."}})
    text, sent = run(monkeypatch, [tok, temp, FakeResponse(200, reply("ok"))])
    assert text == "ok"
    assert sent[2]["max_completion_tokens"] == 100
    assert "temperature" not in sent[2]
    assert llm.dialect_for("https://x.test/v1", "m") == {
        "token": "max_completion_tokens", "drop": {"temperature"},
    }


def test_what_was_learned_is_reused_for_the_next_call(monkeypatch) -> None:
    """Otherwise every verifier call in a 60-candidate run pays the extra
    request — 60 wasted round trips a night."""
    tok = FakeResponse(400, {"error": {"message":
        "Use 'max_completion_tokens' instead."}})
    run(monkeypatch, [tok, FakeResponse(200, reply("first"))])
    text, sent = run(monkeypatch, [FakeResponse(200, reply("second"))])
    assert text == "second"
    assert len(sent) == 1, "the second call renegotiated instead of remembering"
    assert sent[0]["max_completion_tokens"] == 100


def test_an_unrelated_400_surfaces_immediately(monkeypatch) -> None:
    """The boundary that keeps this from masking real bugs. A content-filter
    block or a bad model name must fail loudly on the first try."""
    bad = FakeResponse(400, {"error": {"message": "The model 'm' does not exist."}})
    with pytest.raises(llm.LLMUnavailable) as caught:
        run(monkeypatch, [bad])
    assert "does not exist" in str(caught.value)


def test_response_format_is_never_dropped(monkeypatch) -> None:
    """Dropping it would let prose reach a parser that expects JSON, which is a
    silent data-quality failure rather than a loud one."""
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'response_format' is not supported."}})
    with pytest.raises(llm.LLMUnavailable):
        run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))],
            response_format={"type": "json_object"})


def test_a_reasoning_model_answer_is_read_from_the_other_field(monkeypatch) -> None:
    """content is null on gpt-oss-20b, grok and DeepSeek-R1; the answer is in
    reasoning_content. This raised AttributeError once and burned a candidate."""
    payload = {"choices": [{"message": {"content": None,
                                        "reasoning_content": "the answer"}}]}
    text, _ = run(monkeypatch, [FakeResponse(200, payload)])
    assert text == "the answer"


def test_an_empty_message_raises_rather_than_returning_nothing(monkeypatch) -> None:
    """Returning "" would let a caller treat "no answer" as "answer was
    nothing" — how a four-week outage reported success every day."""
    with pytest.raises(llm.LLMUnavailable):
        run(monkeypatch, [FakeResponse(200, {"choices": [{"message": {"content": "  "}}]})])


def test_a_network_error_becomes_llm_unavailable(monkeypatch) -> None:
    def boom(*a, **k):
        raise llm.requests.ConnectionError("dns")

    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LLMUnavailable):
        llm.chat(base="https://x.test/v1", key="k", model="m",
                 messages=[{"role": "user", "content": "hi"}], max_tokens=10)
