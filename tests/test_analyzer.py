from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from stock_analyzer import StockAnalysisError, analyze, analyze_and_score


def _daily_frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2023-01-01", periods=len(closes), freq="D")
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.01 for c in closes],
            "Low": [c * 0.99 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * len(closes),
        },
        index=idx,
    )


def _make_fake_yf_ticker(price=150.0, sector="Technology"):
    closes = [140.0 + i * 0.05 for i in range(260)]
    daily = _daily_frame(closes)

    calls = pd.DataFrame({"strike": [price], "impliedVolatility": [0.3], "bid": [2.0], "ask": [2.0], "lastPrice": [2.0]})
    puts = pd.DataFrame({"strike": [price], "impliedVolatility": [0.28], "bid": [2.1], "ask": [2.1], "lastPrice": [2.1]})

    ticker = MagicMock()
    ticker.fast_info = {"lastPrice": price, "yearHigh": price * 1.2, "yearLow": price * 0.7}
    ticker.info = {"trailingPE": 28.0, "sector": sector}
    ticker.history.side_effect = lambda period, interval: daily if interval == "1d" else pd.DataFrame()
    ticker.options = ["2024-06-21"]
    ticker.option_chain.return_value = MagicMock(calls=calls, puts=puts)
    ticker.news = [{"title": "Strong quarter, beats estimates"}]
    return ticker


def test_analyze_returns_full_worksheet_shape():
    fake_ticker = _make_fake_yf_ticker()

    data = analyze(
        "aapl",
        yf_ticker_factory=lambda symbol: fake_ticker,
        etf_pe_fetcher=lambda symbol: 24.0,
        anthropic_api_key=None,  # forces the no-key fallback path
    )

    expected_keys = {
        "ticker", "price", "ma50", "ma200", "ema9", "vwap", "rsi",
        "bbLower", "bbMid", "bbUpper", "ivRank", "ivPercentile", "expectedMove",
        "peRatio", "peVsSector", "week52High", "week52Low", "sentiment",
        "catalyst", "fetchedAt", "warnings",
    }
    assert expected_keys.issubset(data.keys())
    assert data["ticker"] == "AAPL"
    assert data["price"] == 150.0
    assert data["sentiment"] == 0  # no API key -> neutral fallback
    assert data["catalyst"] == "Strong quarter, beats estimates"
    assert isinstance(data["warnings"], list)


def test_analyze_rejects_empty_ticker():
    with pytest.raises(StockAnalysisError, match="non-empty string"):
        analyze("   ")


def test_analyze_raises_when_no_price_found():
    ticker = MagicMock()
    ticker.fast_info = {}
    ticker.info = {}

    with pytest.raises(StockAnalysisError, match="No price data found"):
        analyze("BADTICKER", yf_ticker_factory=lambda symbol: ticker)


def test_analyze_wraps_factory_errors():
    def boom(symbol):
        raise RuntimeError("network down")

    with pytest.raises(StockAnalysisError, match="Failed to fetch data"):
        analyze("AAPL", yf_ticker_factory=boom)


def test_analyze_survives_history_fetch_failure():
    ticker = _make_fake_yf_ticker()
    ticker.history.side_effect = RuntimeError("history unavailable")

    data = analyze("AAPL", yf_ticker_factory=lambda symbol: ticker, etf_pe_fetcher=lambda s: 24.0)

    # Falls back to price-based technicals rather than raising.
    assert data["ma50"] == data["price"]
    assert any("history" in w.lower() for w in data["warnings"])


def test_analyze_and_score_attaches_composite_score():
    fake_ticker = _make_fake_yf_ticker()

    data = analyze_and_score(
        "aapl", yf_ticker_factory=lambda symbol: fake_ticker, etf_pe_fetcher=lambda symbol: 24.0
    )

    assert "score" in data
    score = data["score"]
    assert 0 <= score["composite"] <= 100
    assert score["verdict"] in {"Bullish", "Mildly Bullish", "Neutral", "Mildly Bearish", "Bearish"}
    assert len(score["breakdown"]) == 6
    # analyze()'s own fields are still present alongside the score.
    assert data["ticker"] == "AAPL"
    assert data["price"] == 150.0
