"""Tests for stock_analyzer.backtest.

Uses fully synthetic, deterministic price series (a straight uptrend and a
straight downtrend) instead of real market data — real data isn't available
without network access, and a deterministic series lets each assertion state
exactly what should happen rather than "probably outperformed."
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from stock_analyzer.backtest import (
    VERDICT_ORDER,
    backtest_ticker,
    bullish_vs_bearish_edge,
    run_backtest,
    summarize,
)
from stock_analyzer.exceptions import StockAnalysisError


def _trend_frame(start: float, step: float, n: int) -> pd.DataFrame:
    """A daily OHLCV frame following a straight line: close[i] = start + step*i."""
    closes = [start + step * i for i in range(n)]
    idx = pd.date_range("2022-01-03", periods=n, freq="B")  # business days
    return pd.DataFrame(
        {
            "Open": closes,
            "High": [c * 1.001 for c in closes],
            "Low": [c * 0.999 for c in closes],
            "Close": closes,
            "Volume": [1_000_000] * n,
        },
        index=idx,
    )


def test_uptrend_scores_bullish_and_forward_returns_are_positive():
    daily = _trend_frame(start=100.0, step=0.5, n=400)
    rows = backtest_ticker(daily)

    assert not rows.empty
    assert set(rows["verdict"]) <= {"Bullish", "Mildly Bullish"}  # a clean uptrend never reads bearish
    non_nan_1w = rows["fwd_return_1w"].dropna()
    non_nan_1m = rows["fwd_return_1m"].dropna()
    assert len(non_nan_1w) > 0 and (non_nan_1w > 0).all()
    assert len(non_nan_1m) > 0 and (non_nan_1m > 0).all()


def test_downtrend_scores_bearish_and_forward_returns_are_negative():
    daily = _trend_frame(start=300.0, step=-0.5, n=400)
    rows = backtest_ticker(daily)

    assert not rows.empty
    assert set(rows["verdict"]) <= {"Bearish", "Mildly Bearish"}
    non_nan_1w = rows["fwd_return_1w"].dropna()
    non_nan_1m = rows["fwd_return_1m"].dropna()
    assert len(non_nan_1w) > 0 and (non_nan_1w < 0).all()
    assert len(non_nan_1m) > 0 and (non_nan_1m < 0).all()


def test_backtest_ticker_skips_dates_before_min_lookback():
    daily = _trend_frame(start=100.0, step=0.1, n=250)
    rows = backtest_ticker(daily, min_lookback=200)
    # Only dates from index 200 onward can have a real SMA200; there are 50 such dates (200..249).
    assert len(rows) == 50


def test_backtest_ticker_empty_on_insufficient_history():
    daily = _trend_frame(start=100.0, step=0.1, n=50)  # far short of the default 200-day lookback
    rows = backtest_ticker(daily)
    assert rows.empty


def test_most_recent_dates_have_nan_forward_returns():
    daily = _trend_frame(start=100.0, step=0.1, n=210)
    rows = backtest_ticker(daily, min_lookback=200)
    # The very last row has no future data at all for either window.
    assert pd.isna(rows.iloc[-1]["fwd_return_1w"])
    assert pd.isna(rows.iloc[-1]["fwd_return_1m"])


def test_no_lookahead_past_score_unaffected_by_future_data():
    """The core correctness property Phase 3 depends on: mutating the future
    must not change a historical date's score."""
    n = 400
    original = _trend_frame(start=100.0, step=0.5, n=n)
    rows_original = backtest_ticker(original)

    sabotaged = original.copy()
    cutoff = 250  # somewhere well before the end of the series
    # Wildly change every close *after* the cutoff date.
    sabotaged.iloc[cutoff + 1 :, sabotaged.columns.get_loc("Close")] = 999_999.0
    rows_sabotaged = backtest_ticker(sabotaged)

    cutoff_date = original.index[cutoff]
    row_original = rows_original[rows_original["date"] == cutoff_date].iloc[0]
    row_sabotaged = rows_sabotaged[rows_sabotaged["date"] == cutoff_date].iloc[0]

    assert row_original["price"] == row_sabotaged["price"]
    assert row_original["composite"] == row_sabotaged["composite"]
    assert row_original["verdict"] == row_sabotaged["verdict"]


def test_summarize_includes_every_verdict_bucket_even_with_zero_samples():
    rows = pd.DataFrame(
        {
            "verdict": ["Bullish", "Bullish", "Bearish"],
            "fwd_return_1w": [0.02, 0.01, -0.01],
            "fwd_return_1m": [0.05, 0.04, -0.03],
        }
    )
    summary = summarize(rows, holding_windows={"1w": 5, "1m": 21})

    assert list(summary["verdict"]) == VERDICT_ORDER
    bullish = summary[summary["verdict"] == "Bullish"].iloc[0]
    assert bullish["n"] == 2
    assert bullish["mean_1w"] == pytest.approx(0.015)
    assert bullish["win_rate_1w"] == pytest.approx(1.0)

    neutral = summary[summary["verdict"] == "Neutral"].iloc[0]
    assert neutral["n"] == 0
    assert pd.isna(neutral["mean_1w"])


def test_bullish_vs_bearish_edge_detects_outperformance():
    rows = pd.DataFrame(
        {
            "verdict": ["Bullish", "Mildly Bullish", "Bearish", "Mildly Bearish"],
            "fwd_return_1w": [0.03, 0.02, -0.02, -0.01],
        }
    )
    edge = bullish_vs_bearish_edge(rows, holding_windows={"1w": 5})

    assert edge["1w"]["bullish_mean"] == pytest.approx(0.025)
    assert edge["1w"]["bearish_mean"] == pytest.approx(-0.015)
    assert edge["1w"]["edge"] == pytest.approx(0.04)
    assert edge["1w"]["bullish_n"] == 2
    assert edge["1w"]["bearish_n"] == 2


def test_bullish_vs_bearish_edge_nan_when_a_side_has_no_samples():
    rows = pd.DataFrame({"verdict": ["Neutral", "Neutral"], "fwd_return_1w": [0.01, -0.01]})
    edge = bullish_vs_bearish_edge(rows, holding_windows={"1w": 5})
    assert pd.isna(edge["1w"]["edge"])
    assert edge["1w"]["bullish_n"] == 0


def test_run_backtest_combines_baskets_and_computes_edge():
    up = _trend_frame(start=100.0, step=0.5, n=400)
    down = _trend_frame(start=300.0, step=-0.5, n=400)

    def factory(ticker):
        m = MagicMock()
        m.history.return_value = up if ticker == "UP" else down
        return m

    result = run_backtest(["UP", "DOWN"], yf_ticker_factory=factory)

    assert set(result["per_ticker"].keys()) == {"UP", "DOWN"}
    assert not result["combined"].empty
    assert result["warnings"] == []
    assert result["edge"]["1w"]["edge"] > 0  # up-trend bullish beat down-trend bearish
    assert result["edge"]["1m"]["edge"] > 0


def test_run_backtest_skips_bad_tickers_with_warning_instead_of_failing():
    up = _trend_frame(start=100.0, step=0.5, n=400)

    def factory(ticker):
        m = MagicMock()
        if ticker == "GOOD":
            m.history.return_value = up
        elif ticker == "EMPTY":
            m.history.return_value = pd.DataFrame()
        else:
            m.history.side_effect = RuntimeError("network down")
        return m

    result = run_backtest(["GOOD", "EMPTY", "BROKEN"], yf_ticker_factory=factory)

    assert set(result["per_ticker"].keys()) == {"GOOD"}
    assert len(result["warnings"]) == 2
    assert any("EMPTY" in w for w in result["warnings"])
    assert any("BROKEN" in w for w in result["warnings"])


def test_run_backtest_raises_when_every_ticker_fails():
    def factory(ticker):
        m = MagicMock()
        m.history.return_value = pd.DataFrame()
        return m

    with pytest.raises(StockAnalysisError, match="No tickers produced usable backtest data"):
        run_backtest(["A", "B"], yf_ticker_factory=factory)
