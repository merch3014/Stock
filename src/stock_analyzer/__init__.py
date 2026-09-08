"""stock_analyzer: live data (Phase 1), composite scoring (Phase 2),
backtesting (Phase 3), and on-demand watchlist scanning (Phase 4) for the AI
Stock Analyzer.

Public API:
    analyze(ticker) -> dict            Phase 1: live worksheet inputs
    score(data) -> dict                 Phase 2: composite score from those inputs
    analyze_and_score(ticker) -> dict   both, combined (data["score"] = score(data))
    run_backtest(tickers=None) -> dict  Phase 3: verdict-vs-forward-return backtest
    scan_watchlist(tickers) -> dict     Phase 4: analyze_and_score() over a ticker list
    load_watchlist(path) -> list[str]   Phase 4: read a watchlist file

See PROJECT_BRIEF.md / reference/StockAnalyzer.jsx for what these are ported from.
"""

from .analyzer import analyze, analyze_and_score
from .backtest import DEFAULT_BASKET, run_backtest
from .exceptions import StockAnalysisError
from .scoring import score
from .watchlist import load_watchlist, scan_watchlist

__all__ = [
    "analyze",
    "score",
    "analyze_and_score",
    "run_backtest",
    "DEFAULT_BASKET",
    "scan_watchlist",
    "load_watchlist",
    "StockAnalysisError",
]

__version__ = "0.4.0"
