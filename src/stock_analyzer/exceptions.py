"""Exceptions for stock_analyzer."""


class StockAnalysisError(Exception):
    """Raised when live data for a ticker cannot be fetched or analyzed."""
