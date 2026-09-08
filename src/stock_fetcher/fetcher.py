"""Fetch live stock data for a ticker.

Phase 1 scope: given a ticker symbol, return live/near-live quote and
fundamentals data as a flat, JSON-serializable dict. The field names use
camelCase to match what a JS/React worksheet component would typically
expect (see ASSUMPTIONS.md for why this shape was chosen, and adjust it
once the real worksheet contract is known).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

import yfinance as yf

from .exceptions import StockFetchError

# Fields pulled from yfinance's `fast_info` / `info` dicts, and the
# worksheet-facing key each maps to. Kept as a module-level constant so
# the shape is easy to audit/change in one place once the real
# StockAnalyzer.jsx contract is known.
_REQUIRED_PRICE_FIELD = "lastPrice"


def _safe_get(source: dict[str, Any], *keys: str) -> Any:
    """Return the first non-None value found in `source` for `keys`."""
    for key in keys:
        value = source.get(key)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            return value
    return None


def _round_if_number(value: Any, digits: int = 2) -> Any:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(value, digits)
    return value


def fetch_stock_data(ticker: str) -> dict[str, Any]:
    """Fetch live data for `ticker` and return it in worksheet shape.

    Args:
        ticker: Stock ticker symbol, e.g. "AAPL". Case-insensitive.

    Returns:
        A JSON-serializable dict, e.g.::

            {
                "ticker": "AAPL",
                "companyName": "Apple Inc.",
                "currency": "USD",
                "price": 227.52,
                "previousClose": 225.91,
                "open": 226.10,
                "dayHigh": 228.05,
                "dayLow": 225.80,
                "change": 1.61,
                "changePercent": 0.71,
                "volume": 41234567,
                "averageVolume": 52345678,
                "marketCap": 3456789012345,
                "peRatio": 34.12,
                "eps": 6.67,
                "dividendYield": 0.44,
                "fiftyTwoWeekHigh": 237.23,
                "fiftyTwoWeekLow": 164.08,
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "fetchedAt": "2026-09-08T12:00:00+00:00",
            }

    Raises:
        StockFetchError: if the ticker is invalid/empty, or no price data
            could be retrieved (e.g. unknown symbol, network failure).
    """
    if not ticker or not ticker.strip():
        raise StockFetchError("Ticker symbol must be a non-empty string.")

    symbol = ticker.strip().upper()

    try:
        yf_ticker = yf.Ticker(symbol)
        fast_info: dict[str, Any] = dict(yf_ticker.fast_info or {})
        info: dict[str, Any] = yf_ticker.info or {}
    except Exception as exc:  # yfinance can raise a variety of errors
        raise StockFetchError(f"Failed to fetch data for '{symbol}': {exc}") from exc

    price = _safe_get(fast_info, "lastPrice", "last_price") or _safe_get(
        info, "currentPrice", "regularMarketPrice"
    )
    if price is None:
        raise StockFetchError(
            f"No price data found for '{symbol}'. It may be an invalid ticker."
        )

    previous_close = _safe_get(
        fast_info, "previousClose", "previous_close"
    ) or _safe_get(info, "previousClose", "regularMarketPreviousClose")

    change = None
    change_percent = None
    if previous_close not in (None, 0):
        change = price - previous_close
        change_percent = (change / previous_close) * 100

    data: dict[str, Any] = {
        "ticker": symbol,
        "companyName": _safe_get(info, "longName", "shortName") or symbol,
        "currency": _safe_get(fast_info, "currency") or _safe_get(info, "currency"),
        "price": _round_if_number(price),
        "previousClose": _round_if_number(previous_close),
        "open": _round_if_number(
            _safe_get(fast_info, "open") or _safe_get(info, "regularMarketOpen")
        ),
        "dayHigh": _round_if_number(
            _safe_get(fast_info, "dayHigh", "day_high")
            or _safe_get(info, "regularMarketDayHigh")
        ),
        "dayLow": _round_if_number(
            _safe_get(fast_info, "dayLow", "day_low")
            or _safe_get(info, "regularMarketDayLow")
        ),
        "change": _round_if_number(change),
        "changePercent": _round_if_number(change_percent),
        "volume": _safe_get(fast_info, "lastVolume", "last_volume")
        or _safe_get(info, "volume", "regularMarketVolume"),
        "averageVolume": _safe_get(fast_info, "threeMonthAverageVolume")
        or _safe_get(info, "averageVolume"),
        "marketCap": _safe_get(fast_info, "marketCap", "market_cap")
        or _safe_get(info, "marketCap"),
        "peRatio": _round_if_number(_safe_get(info, "trailingPE", "forwardPE")),
        "eps": _round_if_number(_safe_get(info, "trailingEps")),
        "dividendYield": _round_if_number(_safe_get(info, "dividendYield")),
        "fiftyTwoWeekHigh": _round_if_number(
            _safe_get(fast_info, "yearHigh", "year_high")
            or _safe_get(info, "fiftyTwoWeekHigh")
        ),
        "fiftyTwoWeekLow": _round_if_number(
            _safe_get(fast_info, "yearLow", "year_low")
            or _safe_get(info, "fiftyTwoWeekLow")
        ),
        "sector": _safe_get(info, "sector"),
        "industry": _safe_get(info, "industry"),
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
    }

    return data
