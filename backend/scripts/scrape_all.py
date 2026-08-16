"""
Run every scraper into the shared candidate pool.

This is what the daily launchd job (com.northstar.reddit-scraper)
executes. Each source is isolated: one failing never blocks the others.

Usage:
    cd backend && .venv/bin/python scripts/scrape_all.py
"""

from __future__ import annotations

import traceback

import scrape_devpost
import scrape_reddit
import verify_and_import

# Scrape every source into the pool, then let the verifier promote the
# clear wins into the live catalog. The verify stage no-ops (exits) when
# no LLM key is set, so the scrapers still run without it.
STAGES = (
    ("reddit", scrape_reddit),
    ("devpost", scrape_devpost),
    ("verify+import", verify_and_import),
)

for name, stage in STAGES:
    print(f"=== {name} ===")
    try:
        stage.main()
    except SystemExit as exit_:  # stages sys.exit() on fatal blocks
        print(f"{name} stopped: {exit_}")
    except Exception:
        traceback.print_exc()
