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

from app.llm import LLMUnavailable, chat, dialect_for  # noqa: E402
from app.settings import settings  # noqa: E402


def probe(label: str, base: str, key: str, model: str) -> bool:
    """One real completion against one provider. True if it answered."""
    print(f"\n[{label}]")
    print(f"  provider: {base}")
    print(f"  model:    {model}")
    try:
        # Through app.llm.chat deliberately, NOT a hand-rolled POST. The old
        # version sent max_tokens and temperature 0 directly, which Azure
        # gpt-5.6 rejects with a 400, so the preflight would have failed the
        # whole nightly workflow the moment the verifier moved provider, and the
        # printed diagnosis would have been "model unavailable" when the model
        # was fine. A health check that cannot speak the dialect the real caller
        # speaks is not checking anything.
        result = chat(
            base=base, key=key, model=model,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
            max_tokens=2000, temperature=0.0, timeout=60,
        )
        text = result.text
    except LLMUnavailable as error:
        print(f"  FAIL: {error}")
        _print_catalog(base, key)
        return False

    print(f"  OK: answered {text.strip()[:40]!r} "
          f"({result.total_tokens} tokens)")
    learned = dialect_for(base, model)
    if learned and (learned["token"] != "max_tokens" or learned["drop"]):
        print(f"  dialect:  {learned['token']}"
              + (f", omits {sorted(learned['drop'])}" if learned["drop"] else ""))
    return True


def _print_catalog(base: str, key: str) -> None:
    """A retired or renamed model is the common case, so print what IS
    available rather than making someone go and look it up."""
    try:
        listing = requests.get(
            f"{base}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30
        )
        if not listing.ok:
            return
        ids = sorted(m.get("id", "") for m in listing.json().get("data", []))
        if ids:
            print(f"  {len(ids)} models the key can see:")
            for model_id in ids:
                print(f"    {model_id}")
            print("  Set the model env var to one of these.")
    except (requests.RequestException, ValueError):
        pass


def main() -> int:
    """Check every CONFIGURED provider, not just the shared one.

    The advisor and the verifier can now point at different vendors: the
    verifier moved to Azure because it handles no student data, while /advisor
    stays on NIM until the privacy page names a new recipient. Checking only
    one would leave the other free to be broken for weeks, which is the exact
    outage this script exists to prevent.
    """
    v_base, v_key, v_model = settings.verifier_provider
    targets = []
    if settings.llm_api_key:
        targets.append(("advisor", settings.llm_api_base.rstrip("/"),
                        settings.llm_api_key, settings.llm_model))
    if v_key:
        entry = ("verifier", v_base.rstrip("/"), v_key, v_model)
        # Same provider for both is the common case; do not pay for it twice.
        if not any(t[1:] == entry[1:] for t in targets):
            targets.append(entry)
        else:
            print("verifier shares the advisor's provider — one check covers both.")

    if not targets:
        print("No LLM configured. Set LLM_API_KEY, or VERIFIER_API_KEY for the "
              "nightly verifier alone. The verifier cannot run without one.")
        return 1

    results = [probe(*t) for t in targets]
    print()
    if all(results):
        print(f"OK: {len(results)} provider(s) answered.")
        return 0
    print(f"FAIL: {results.count(False)} of {len(results)} provider(s) did not answer.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
