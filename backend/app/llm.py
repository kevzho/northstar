"""
One OpenAI-compatible chat call, usable against providers that disagree.

WHY THIS EXISTS. Two jobs call an LLM — the route advisor (student-facing) and
the nightly candidate verifier (no student data) — and they no longer want the
same provider. NVIDIA NIM's free tier has retired a model out from under this
project twice: meta/llama-3.1-70b-instruct on 2026-08-26 (four silent weeks of
410s) and again in the local .env that was never updated. Azure AI Foundry on a
sponsorship subscription is stable and already provisioned, but it takes no
student data until the privacy page names it, so the verifier moves first and
the advisor stays put. Two providers at once, therefore one place that knows how
to talk to both.

THE PARAMETER THAT DIFFERS. Sending `max_tokens` to gpt-5.6 on Azure returns:

    400 Unsupported parameter: 'max_tokens' is not supported with this model.
        Use 'max_completion_tokens' instead.

while NIM accepts only `max_tokens`. Rather than hardcode a provider sniff on
the URL — which silently breaks the day a provider changes hostname or a third
one appears — the first call tries `max_tokens`, reads that specific error, and
retries with the other name, remembering the answer per (base, model) for the
rest of the process. Self-correcting, and it costs one extra request once.

REASONING MODELS. `content` can be null while the real answer sits in
`reasoning_content`. gpt-oss-20b does this, grok does this, DeepSeek-R1 does
this. Handled here so every caller gets text or an explicit failure.
"""

from __future__ import annotations

import time
from typing import NamedTuple

import requests

# Per-(base, model) record of how this provider likes to be spoken to.
#   token: which of max_tokens / max_completion_tokens it accepts
#   drop:  parameters it rejects outright and that must be omitted
# Learned on first use and reused for the rest of the process.
_DIALECT: dict[tuple[str, str], dict] = {}

_ALT = {"max_tokens": "max_completion_tokens", "max_completion_tokens": "max_tokens"}

# Parameters safe to DROP when a provider refuses them. Only optional knobs
# belong here: dropping `messages` or `model` would send a meaningless request,
# and dropping `response_format` would let a non-JSON reply through to a parser
# that expects JSON. Losing `temperature` costs determinism, which is a real
# cost and is documented at the verifier's call site.
_DROPPABLE = frozenset({"temperature", "top_p", "reasoning_effort"})

MAX_ATTEMPTS = 4

# A 429 is the provider asking us to wait, not an error. Honour Retry-After once
# rather than failing the candidate: on a shared deployment a burst from another
# caller is routine, and dropping work because someone else was busy is the
# wrong response. One retry only — a queue that retries forever turns a busy
# minute into a stuck nightly job.
RATE_LIMIT_RETRIES = 1
MAX_RETRY_WAIT_S = 30


class ChatResult(NamedTuple):
    """Text plus what it cost. Usage is why this is not a bare str.

    Spend has to be measurable per call to be governable: public.advisor_calls
    counts CALLS, which was fine while the ceiling was 150 a day and stops being
    fine at hundreds of users, because a long question and a short one are not
    the same purchase.
    """

    text: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class LLMUnavailable(RuntimeError):
    """The provider could not be reached or refused the request.

    Raised rather than returning an empty string: a caller that silently treats
    "no answer" as "answer was nothing" is how a four-week outage reported
    success every day.
    """


def _adapt(dialect: dict, body: str, payload: dict) -> bool:
    """Learn one thing from a 400 and mutate the dialect. False if unlearnable.

    Two adaptations, both driven by what the provider actually said rather than
    by sniffing its hostname — a URL check silently breaks the day a provider
    renames a domain or a third one appears. Observed in production:

        "Unsupported parameter: 'max_tokens' is not supported with this model.
         Use 'max_completion_tokens' instead."          (Azure gpt-5.6)
        "Unsupported value: 'temperature' does not support 0.0 with this model.
         Only the default (1) value is supported."      (Azure gpt-5.6)

    NIM accepts both of the things Azure refuses, so neither can be hardcoded.
    """
    lowered = body.lower()
    other = _ALT[dialect["token"]]
    if other.lower() in lowered:
        dialect["token"] = other
        return True
    for name in _DROPPABLE:
        if name in payload and f"'{name}'" in lowered:
            dialect["drop"].add(name)
            return True
    return False


def chat(
    *,
    base: str,
    key: str,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.0,
    response_format: dict | None = None,
    reasoning_effort: str | None = None,
    timeout: int = 90,
) -> ChatResult:
    """Return the assistant's text. Raises LLMUnavailable on failure.

    ``base`` is the OpenAI-compatible root, e.g.
    ``https://integrate.api.nvidia.com/v1`` or
    ``https://<resource>.cognitiveservices.azure.com/openai/v1``. Both accept
    ``Authorization: Bearer`` — verified against production before this shipped,
    which is why there is no per-provider auth branch.
    """
    root = base.rstrip("/")
    ckey = (root, model)
    dialect = _DIALECT.setdefault(ckey, {"token": "max_tokens", "drop": set()})
    rate_limited = 0

    for attempt in range(1, MAX_ATTEMPTS + RATE_LIMIT_RETRIES + 1):
        payload: dict = {"model": model, "messages": messages}
        payload[dialect["token"]] = max_tokens
        if "temperature" not in dialect["drop"]:
            payload["temperature"] = temperature
        if response_format:
            payload["response_format"] = response_format
        # Reasoning models spend tokens thinking before they answer. On a tight
        # classification prompt that thinking buys nothing: measured on
        # gpt-6-luna, effort "none" returned the same verdict as "high" using
        # 611 tokens instead of 690 and 1.3s instead of 2.1s. Providers that do
        # not know the parameter reject it, and it is droppable for that reason.
        if reasoning_effort and "reasoning_effort" not in dialect["drop"]:
            payload["reasoning_effort"] = reasoning_effort

        try:
            response = requests.post(
                f"{root}/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=timeout,
            )
        except requests.RequestException as error:
            raise LLMUnavailable(f"{model}: {error}") from error

        if response.status_code == 400 and attempt < MAX_ATTEMPTS:
            # Only a parameter disagreement is retried. Every other 400 is a
            # genuine bad request and must surface rather than be masked.
            if _adapt(dialect, response.text, payload):
                continue

        if response.status_code == 429 and rate_limited < RATE_LIMIT_RETRIES:
            rate_limited += 1
            wait = MAX_RETRY_WAIT_S
            try:
                wait = min(float(response.headers.get("Retry-After", 5)), MAX_RETRY_WAIT_S)
            except (TypeError, ValueError):
                wait = 5.0
            time.sleep(max(0.0, wait))
            continue

        if not response.ok:
            raise LLMUnavailable(
                f"{model}: HTTP {response.status_code} {response.text[:200]}"
            )

        try:
            body = response.json()
            message = body["choices"][0]["message"]
        except (ValueError, KeyError, IndexError) as error:
            raise LLMUnavailable(f"{model}: unreadable response") from error

        text = message.get("content") or message.get("reasoning_content") or ""
        if not text.strip():
            raise LLMUnavailable(f"{model}: empty message")
        usage = body.get("usage") or {}
        return ChatResult(
            text=text,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            total_tokens=int(usage.get("total_tokens") or 0),
        )

    raise LLMUnavailable(
        f"{model}: gave up after {MAX_ATTEMPTS} attempts negotiating parameters"
    )


def dialect_for(base: str, model: str) -> dict | None:
    """What was learned about a provider, or None if untried. Tests and logs."""
    return _DIALECT.get((base.rstrip("/"), model))
