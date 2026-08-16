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

for name, scraper in (("reddit", scrape_reddit), ("devpost", scrape_devpost)):
    print(f"=== {name} ===")
    try:
        scraper.main()
    except SystemExit as exit_:  # scrapers sys.exit() on fatal blocks
        print(f"{name} stopped: {exit_}")
    except Exception:
        traceback.print_exc()
