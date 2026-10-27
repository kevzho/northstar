"""
Tests for app/llm.py, the provider-dialect negotiation.

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
    def __init__(self, status: int, payload: dict | str, headers: dict | None = None):
        self.status_code = status
        self._payload = payload
        self.headers = headers or {}
        self.text = payload if isinstance(payload, str) else json.dumps(payload)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300

    def json(self) -> dict:
        if isinstance(self._payload, str):
            raise ValueError("not json")
        return self._payload


def reply(text: str, total: int = 42) -> dict:
    return {
        "choices": [{"message": {"content": text}}],
        "usage": {"prompt_tokens": total - 12, "completion_tokens": 12,
                  "total_tokens": total},
    }


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
    result, sent = run(monkeypatch, [FakeResponse(200, reply("ok"))])
    assert result.text == "ok"
    assert len(sent) == 1
    assert sent[0]["max_tokens"] == 100
    assert sent[0]["temperature"] == 0.0


def test_the_token_parameter_is_renamed_on_request(monkeypatch) -> None:
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'max_tokens' is not supported with this model. "
        "Use 'max_completion_tokens' instead."}})
    result, sent = run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))])
    assert result.text == "ok"
    assert "max_tokens" not in sent[1]
    assert sent[1]["max_completion_tokens"] == 100


def test_an_unsupported_temperature_is_dropped_not_guessed(monkeypatch) -> None:
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported value: 'temperature' does not support 0.0 with this model. "
        "Only the default (1) value is supported."}})
    result, sent = run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))])
    assert result.text == "ok"
    assert "temperature" not in sent[1], "temperature should be omitted, not altered"


def test_both_disagreements_are_learned_in_one_call(monkeypatch) -> None:
    """Azure gpt-5.6 refuses both, one error at a time."""
    tok = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'max_tokens' ... Use 'max_completion_tokens' instead."}})
    temp = FakeResponse(400, {"error": {"message":
        "Unsupported value: 'temperature' does not support 0.0 with this model."}})
    result, sent = run(monkeypatch, [tok, temp, FakeResponse(200, reply("ok"))])
    assert result.text == "ok"
    assert sent[2]["max_completion_tokens"] == 100
    assert "temperature" not in sent[2]
    assert llm.dialect_for("https://x.test/v1", "m") == {
        "token": "max_completion_tokens", "drop": {"temperature"},
    }


def test_what_was_learned_is_reused_for_the_next_call(monkeypatch) -> None:
    """Otherwise every verifier call in a 60-candidate run pays the extra
    request, 60 wasted round trips a night."""
    tok = FakeResponse(400, {"error": {"message":
        "Use 'max_completion_tokens' instead."}})
    run(monkeypatch, [tok, FakeResponse(200, reply("first"))])
    result, sent = run(monkeypatch, [FakeResponse(200, reply("second"))])
    assert result.text == "second"
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
    result, _ = run(monkeypatch, [FakeResponse(200, payload)])
    assert result.text == "the answer"


def test_an_empty_message_raises_rather_than_returning_nothing(monkeypatch) -> None:
    """Returning "" would let a caller treat "no answer" as "answer was
    nothing", how a four-week outage reported success every day."""
    with pytest.raises(llm.LLMUnavailable):
        run(monkeypatch, [FakeResponse(200, {"choices": [{"message": {"content": "  "}}]})])


def test_a_network_error_becomes_llm_unavailable(monkeypatch) -> None:
    def boom(*a, **k):
        raise llm.requests.ConnectionError("dns")

    monkeypatch.setattr(llm.requests, "post", boom)
    with pytest.raises(llm.LLMUnavailable):
        llm.chat(base="https://x.test/v1", key="k", model="m",
                 messages=[{"role": "user", "content": "hi"}], max_tokens=10)


def test_usage_is_reported_so_spend_can_be_governed(monkeypatch) -> None:
    """A call count cannot govern spend once questions vary in length. The
    advisor budget needs tokens, so chat() must surface them."""
    result, _ = run(monkeypatch, [FakeResponse(200, reply("ok", total=900))])
    assert result.total_tokens == 900
    assert result.prompt_tokens == 888
    assert result.completion_tokens == 12


def test_missing_usage_does_not_crash(monkeypatch) -> None:
    """Not every provider returns usage; a missing block means "unknown", and
    unknown must not take down a working answer."""
    result, _ = run(monkeypatch, [FakeResponse(200, {"choices": [{"message": {"content": "ok"}}]})])
    assert result.text == "ok"
    assert result.total_tokens == 0


def test_a_429_waits_and_retries_once(monkeypatch) -> None:
    """A 429 is the provider asking us to wait, not a failed candidate. On a
    shared deployment another caller's burst is routine."""
    slept: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", lambda s: slept.append(s))
    busy = FakeResponse(429, {"error": {"message": "rate limited"}}, {"Retry-After": "3"})
    result, sent = run(monkeypatch, [busy, FakeResponse(200, reply("ok"))])
    assert result.text == "ok"
    assert slept == [3.0], f"expected one 3s wait, got {slept}"
    assert len(sent) == 2


def test_a_retry_after_wait_is_capped(monkeypatch) -> None:
    """A provider asking for ten minutes must not stall the nightly job."""
    slept: list[float] = []
    monkeypatch.setattr(llm.time, "sleep", lambda s: slept.append(s))
    busy = FakeResponse(429, "slow down", {"Retry-After": "600"})
    run(monkeypatch, [busy, FakeResponse(200, reply("ok"))])
    assert slept == [float(llm.MAX_RETRY_WAIT_S)]


def test_repeated_429s_eventually_surface(monkeypatch) -> None:
    """Retrying forever turns a busy minute into a stuck job."""
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)
    busy = FakeResponse(429, "slow down", {"Retry-After": "1"})
    with pytest.raises(llm.LLMUnavailable):
        run(monkeypatch, [busy, busy, busy, busy, busy, busy])


def test_reasoning_effort_is_sent_and_is_droppable(monkeypatch) -> None:
    """Reasoning tokens are pure cost on a classification prompt, but a provider
    that does not know the parameter must not be broken by it."""
    result, sent = run(monkeypatch, [FakeResponse(200, reply("ok"))],
                       reasoning_effort="none")
    assert sent[0]["reasoning_effort"] == "none"

    llm._DIALECT.clear()
    refusal = FakeResponse(400, {"error": {"message":
        "Unsupported parameter: 'reasoning_effort' is not supported."}})
    result, sent = run(monkeypatch, [refusal, FakeResponse(200, reply("ok"))],
                       reasoning_effort="none")
    assert result.text == "ok"
    assert "reasoning_effort" not in sent[1]


# --- the advisor budget counts money, not requests -----------------------


def test_unpriced_rows_are_charged_rather_than_ignored() -> None:
    """A NULL total_tokens means "unknown", not "free".

    Rows written before 20260926190000 have no token counts, and some providers
    return no usage block. Counting those as zero would let an unmeasured
    provider spend without limit, the budget would read 0 spent no matter how
    many calls were made. This exercises the FALLBACK path, which runs when the
    aggregate RPC is absent because a deploy landed before the migration.
    """
    from app import advisor

    class FakeTable:
        def select(self, *a, **k): return self
        def gte(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: data = [
                {"total_tokens": 900},
                {"total_tokens": None},   # pre-migration row
                {"total_tokens": 0},      # provider returned no usage
                {},                       # column absent entirely
            ]
            return R()

    class NoRpcSB:
        def table(self, name): return FakeTable()
        def rpc(self, *a, **k):
            # What Postgres says when the migration has not been applied.
            raise RuntimeError("function public.advisor_tokens_since does not exist")

    assumed = advisor.settings.advisor_assumed_tokens_per_call
    spent = advisor._tokens_spent(NoRpcSB(), "2026-09-26T00:00:00Z")
    assert spent == 900 + assumed * 3, (
        f"expected the three unpriced rows to cost {assumed} each, got {spent}"
    )


def test_the_aggregate_rpc_is_preferred_over_scanning_rows() -> None:
    """At 1,000 students the day's ledger is ~10,000 rows and this runs on every
    request. Summing in Postgres keeps the cost of asking "may I spend?" from
    growing with how much has already been spent."""
    from app import advisor

    called: dict = {}

    class RpcResult:
        data = 4321

    class RpcBuilder:
        # postgrest's rpc() returns a builder; the caller chains .execute().
        def execute(self):
            return RpcResult()

    class RpcSB:
        def rpc(self, name, params):
            called["name"] = name
            called["params"] = params
            return RpcBuilder()

        def table(self, name):
            raise AssertionError("fell back to a row scan despite a working RPC")

    spent = advisor._tokens_spent(RpcSB(), "2026-09-26T00:00:00Z")
    assert spent == 4321
    assert called["name"] == "advisor_tokens_since"
    assert called["params"]["p_since"] == "2026-09-26T00:00:00Z"
    assert called["params"]["p_assumed"] == advisor.settings.advisor_assumed_tokens_per_call


def test_a_truncated_fallback_scan_reads_as_over_budget() -> None:
    """If the ledger cannot be measured, the safe answer is "stop", not
    "continue", otherwise an unmeasurable day spends without a ceiling."""
    from app import advisor

    class BigTable:
        def select(self, *a, **k): return self
        def gte(self, *a, **k): return self
        def limit(self, *a, **k): return self
        def execute(self):
            class R: data = [{"total_tokens": 1}] * advisor.MAX_LEDGER_SCAN
            return R()

    class NoRpcSB:
        def table(self, name): return BigTable()
        def rpc(self, *a, **k): raise RuntimeError("missing")

    spent = advisor._tokens_spent(NoRpcSB(), "2026-09-26T00:00:00Z")
    assert spent >= advisor.settings.advisor_daily_token_budget


def test_the_assumed_cost_sits_above_the_measured_average() -> None:
    """Measured on gpt-6-luna a real advisor turn is ~925 tokens. An assumption
    BELOW that would make unmeasured traffic look cheaper than it is, which is
    the wrong direction for a safety limit to be wrong in."""
    from app import advisor

    assert advisor.settings.advisor_assumed_tokens_per_call >= 925


def test_the_token_budget_is_large_enough_to_be_useful() -> None:
    """A budget under a few hundred thousand tokens cannot serve hundreds of
    students at the per-student call cap, and would turn the money limit into an
    availability outage that looks like a bug."""
    from app import advisor

    per_student = advisor.settings.advisor_per_student_daily
    budget = advisor.settings.advisor_daily_token_budget
    # ~925 tokens/call measured; 100 students at the cap is the floor to clear.
    assert budget >= 100 * per_student * 925
