#!/usr/bin/env python3
"""Thin repo-root wrapper: `python scheduled_scan.py [TICKER ...] [--watchlist FILE] [--email]`.

This is what a cron entry (or OS task scheduler) would actually call — see
src/stock_analyzer/scheduled_scan.py's module docstring for what it does
and, importantly, what it deliberately does NOT do (schedule itself), and
README.md's "Scheduling it yourself" section for a crontab line.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_analyzer.scheduled_scan import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
