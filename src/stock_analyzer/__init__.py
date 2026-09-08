"""stock_analyzer: live data pipeline (Phase 1) + composite scoring (Phase 2)
for the AI Stock Analyzer.

Public API:
    analyze(ticker) -> dict          Phase 1: live worksheet inputs
    score(data) -> dict               Phase 2: composite score from those inputs
    analyze_and_score(ticker) -> dict  both, combined (data["score"] = score(data))

See PROJECT_BRIEF.md / reference/StockAnalyzer.jsx for what these are ported from.
"""

from .analyzer import analyze, analyze_and_score
from .exceptions import StockAnalysisError
from .scoring import score

__all__ = ["analyze", "score", "analyze_and_score", "StockAnalysisError"]

__version__ = "0.2.0"
