"""analyze(ticker) -> dict: the Phase 1 entry point.

Fetches live price/technicals, options metrics, fundamentals, and a
news-driven sentiment score for `ticker`, and returns them in exactly the
shape StockAnalyzer.jsx's worksheet state needs — so this dict can be used
as a drop-in replacement for manual/screenshot entry (e.g. by calling the
matching `setX(data.x)` for each field).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

import pandas as pd
import yfinance as yf

from .exceptions import StockAnalysisError
from .fundamentals import compute_fundamentals
from .options import compute_options_metrics
from .sentiment import MessagesClient, fetch_news_headlines, score_sentiment_and_catalyst
from .technicals import compute_technicals


def _safe_get(source: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = source.get(key)
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            return value
    return None


def _default_etf_pe_fetcher(symbol: str) -> float | None:
    return yf.Ticker(symbol).info.get("trailingPE")


def analyze(
    ticker: str,
    *,
    anthropic_api_key: str | None = None,
    yf_ticker_factory: Callable[[str], Any] = yf.Ticker,
    sentiment_client: MessagesClient | None = None,
    etf_pe_fetcher: Callable[[str], float | None] = _default_etf_pe_fetcher,
) -> dict:
    """Fetch and assemble live worksheet data for `ticker`.

    The optional keyword arguments exist so callers/tests can inject fakes
    for the network-touching pieces (yfinance, the sector-ETF P/E lookup,
    the Anthropic client) without needing real network access or API keys.

    Returns a dict with keys: ticker, price, ma50, ma200, ema9, vwap, rsi,
    bbLower, bbMid, bbUpper, ivRank, ivPercentile, expectedMove, peRatio,
    peVsSector, week52High, week52Low, sentiment, catalyst, fetchedAt, plus
    diagnostic extras (sectorAvgPE, warnings) the worksheet can ignore.

    Raises StockAnalysisError if the ticker is invalid/empty or no price
    data could be found at all.
    """
    if not ticker or not ticker.strip():
        raise StockAnalysisError("Ticker symbol must be a non-empty string.")

    symbol = ticker.strip().upper()
    warnings: list[str] = []

    try:
        yf_ticker = yf_ticker_factory(symbol)
        fast_info: dict[str, Any] = dict(yf_ticker.fast_info or {})
        info: dict[str, Any] = yf_ticker.info or {}
    except Exception as exc:
        raise StockAnalysisError(f"Failed to fetch data for '{symbol}': {exc}") from exc

    price = _safe_get(fast_info, "lastPrice", "last_price") or _safe_get(
        info, "currentPrice", "regularMarketPrice"
    )
    if price is None:
        raise StockAnalysisError(
            f"No price data found for '{symbol}'. It may be an invalid ticker."
        )
    price = float(price)

    try:
        daily = yf_ticker.history(period="1y", interval="1d")
    except Exception as exc:
        daily = pd.DataFrame()
        warnings.append(f"Could not fetch daily price history: {exc}")

    try:
        intraday = yf_ticker.history(period="1d", interval="5m")
    except Exception as exc:
        intraday = pd.DataFrame()
        warnings.append(f"Could not fetch intraday price history: {exc}")

    technicals = compute_technicals(daily, intraday, price)
    warnings.extend(technicals.pop("warnings"))

    daily_closes = daily["Close"].dropna() if daily is not None and not daily.empty else pd.Series(dtype=float)
    options_metrics = compute_options_metrics(yf_ticker, price, daily_closes)
    warnings.extend(options_metrics.pop("warnings"))

    fundamentals = compute_fundamentals(info, fast_info, etf_pe_fetcher)
    warnings.extend(fundamentals.pop("warnings"))

    headlines = fetch_news_headlines(yf_ticker)
    sentiment_result = score_sentiment_and_catalyst(
        symbol, headlines, api_key=anthropic_api_key, client=sentiment_client
    )
    warnings.extend(sentiment_result.pop("warnings"))

    return {
        "ticker": symbol,
        "price": round(price, 2),
        **technicals,
        **options_metrics,
        **fundamentals,
        **sentiment_result,
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "warnings": warnings,
    }
