from __future__ import annotations

from unittest.mock import MagicMock

import pandas as pd
import pytest

from stock_analyzer.options import (
    compute_options_metrics,
    iv_rank_and_percentile,
    realized_volatility_series,
)


def _chain(strikes, ivs, bids=None, asks=None, lasts=None):
    n = len(strikes)
    return pd.DataFrame(
        {
            "strike": strikes,
            "impliedVolatility": ivs,
            "bid": bids or [1.0] * n,
            "ask": asks or [1.2] * n,
            "lastPrice": lasts or [1.1] * n,
        }
    )


def test_iv_rank_and_percentile_midrange():
    hv = pd.Series([0.1, 0.2, 0.3, 0.4, 0.5])
    rank, pct = iv_rank_and_percentile(0.3, hv)
    assert rank == pytest.approx(50.0)
    assert pct == pytest.approx(40.0)  # 2 of 5 values below 0.3


def test_iv_rank_defaults_to_50_when_no_history():
    rank, pct = iv_rank_and_percentile(0.3, pd.Series(dtype=float))
    assert rank == 50.0
    assert pct == 50.0


def test_realized_volatility_series_is_nonnegative():
    closes = pd.Series([100, 101, 99, 102, 98, 103] * 10, dtype=float)
    hv = realized_volatility_series(closes, window=5)
    assert (hv >= 0).all()


def test_compute_options_metrics_happy_path():
    calls = _chain([95, 100, 105], [0.3, 0.32, 0.31], bids=[6.0, 3.0, 1.0], asks=[6.0, 3.0, 1.0])
    puts = _chain([95, 100, 105], [0.29, 0.33, 0.30], bids=[1.0, 3.2, 6.0], asks=[1.0, 3.2, 6.0])

    yf_ticker = MagicMock()
    yf_ticker.options = ["2024-06-21"]
    yf_ticker.option_chain.return_value = MagicMock(calls=calls, puts=puts)

    closes = pd.Series([100.0 + (i % 5) for i in range(100)])
    result = compute_options_metrics(yf_ticker, price=100.0, daily_closes=closes)

    assert 0 <= result["ivRank"] <= 100
    assert 0 <= result["ivPercentile"] <= 100
    # ATM straddle ~ (3.0 + 3.2) / 100 * 100 = 6.2%
    assert result["expectedMove"] == pytest.approx(6.2, abs=0.01)
    assert result["warnings"] == []


def test_compute_options_metrics_no_expirations_defaults():
    yf_ticker = MagicMock()
    yf_ticker.options = []

    result = compute_options_metrics(yf_ticker, price=100.0, daily_closes=pd.Series(dtype=float))

    assert result["ivRank"] == 50.0
    assert result["ivPercentile"] == 50.0
    assert result["expectedMove"] == 5.0
    assert result["warnings"]


def test_compute_options_metrics_handles_chain_error():
    yf_ticker = MagicMock()
    yf_ticker.options = ["2024-06-21"]
    yf_ticker.option_chain.side_effect = RuntimeError("boom")

    result = compute_options_metrics(yf_ticker, price=100.0, daily_closes=pd.Series(dtype=float))

    assert result["ivRank"] == 50.0
    assert any("boom" in w for w in result["warnings"])
