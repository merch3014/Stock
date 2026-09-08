"""stock_analyzer: Phase 1 live data pipeline for the AI Stock Analyzer.

Public API: `analyze(ticker) -> dict`, matching every input field
StockAnalyzer.jsx's worksheet needs (see PROJECT_BRIEF.md / reference/StockAnalyzer.jsx).
"""

from .analyzer import analyze
from .exceptions import StockAnalysisError

__all__ = ["analyze", "StockAnalysisError"]

__version__ = "0.1.0"
