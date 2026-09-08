"""stock_analyzer: live data (Phase 1), composite scoring (Phase 2), and
backtesting (Phase 3) for the AI Stock Analyzer.

Public API:
    analyze(ticker) -> dict            Phase 1: live worksheet inputs
    score(data) -> dict                 Phase 2: composite score from those inputs
    analyze_and_score(ticker) -> dict   both, combined (data["score"] = score(data))
    run_backtest(tickers=None) -> dict  Phase 3: verdict-vs-forward-return backtest

See PROJECT_BRIEF.md / reference/StockAnalyzer.jsx for what these are ported from.
"""

from .analyzer import analyze, analyze_and_score
from .backtest import DEFAULT_BASKET, run_backtest
from .exceptions import StockAnalysisError
from .scoring import score

__all__ = [
    "analyze",
    "score",
    "analyze_and_score",
    "run_backtest",
    "DEFAULT_BASKET",
    "StockAnalysisError",
]

__version__ = "0.3.0"
