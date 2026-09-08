#!/usr/bin/env python3
"""Thin repo-root wrapper so `python analyze.py TICKER` works as named in
PROJECT_BRIEF.md's Phase 4, without requiring an editable install.

Equivalent to `python -m stock_analyzer TICKER`; see stock_analyzer.cli for
the actual implementation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_analyzer.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
