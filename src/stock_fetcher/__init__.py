"""stock_fetcher: Phase 1 live stock data fetcher.

Fetches live/near-live quote and fundamentals data for a ticker and
returns it as a plain, JSON-serializable dict shaped for consumption by
a front-end worksheet component.
"""

from .fetcher import StockFetchError, fetch_stock_data

__all__ = ["fetch_stock_data", "StockFetchError"]

__version__ = "0.1.0"
