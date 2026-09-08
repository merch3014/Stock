#!/usr/bin/env python3
"""Thin repo-root wrapper: `python backtest.py [TICKER ...]` — Phase 3.

Backtests the composite score (stock_analyzer.scoring) against actual
forward returns for a basket of tickers. Requires real network access to
Yahoo Finance (via yfinance) — this is not mocked, unlike the test suite.

See stock_analyzer/backtest.py for the engine and stock_analyzer/backtest_cli.py
for the CLI implementation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from stock_analyzer.backtest_cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
