"""
Preflight: is the configured LLM model actually still alive?

This exists because of a specific 28-day outage. On 2026-08-26 the model
configured as LLM_MODEL reached end of life. Every verifier call began
returning:

    410 Gone -- The model '...' has reached its end of life on
    2026-08-26T09:00:00Z and is no longer available.

Nothing checked, so nothing noticed: the daily workflow scraped, failed every
verify, committed the pool, and reported success for four consecutive weeks.

Hosted model catalogs retire models on a schedule. That will happen again.
This turns it from a silent four-week outage into a red build on the first
day, with the live list of replacements printed in the log.

Exits 0 if the model answers, 1 with a readable diagnosis otherwise.

Usage:
    cd backend && .venv/bin/python scripts/check_llm.py
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from app.settings import settings  # noqa: E402


def main() -> int:
    base = settings.llm_api_base.rstrip("/")
    model = settings.llm_model
    key = settings.llm_api_key

    if not key:
        print("LLM_API_KEY is unset — the verifier cannot run.")
        return 1

    print(f"provider: {base}")
    print(f"model:    {model}")

    headers = {"Authorization": f"Bearer {key}"}

    # The real check is a completion, not a catalog lookup: a model can be
    # listed and still refuse, and it is the completion path that matters.
    try:
        response = requests.post(
            f"{base}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with the single word: ok"}],
                "max_tokens": 5,
                "temperature": 0,
            },
            timeout=60,
        )
    except requests.RequestException as error:
        print(f"\nFAIL: could not reach {base} — {error}")
        return 1

    if response.status_code == 200:
        print("\nOK: the model answered.")
        return 0

    print(f"\nFAIL: HTTP {response.status_code}")
    print(response.text[:400])

    # A retired or renamed model is the common case, so print what IS
    # available rather than making someone go and look it up.
    try:
        listing = requests.get(f"{base}/models", headers=headers, timeout=30)
        if listing.ok:
            ids = sorted(m.get("id", "") for m in listing.json().get("data", []))
            print(f"\n{len(ids)} models currently available at this endpoint:")
            for model_id in ids:
                print(f"  {model_id}")
            print("\nSet LLM_MODEL (repo secret, and backend/.env) to one of these.")
    except requests.RequestException:
        pass

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
