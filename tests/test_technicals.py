from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from stock_analyzer.technicals import (
    bollinger_bands,
    compute_technicals,
    ema,
    rsi,
    sma,
    vwap,
)


def _daily_frame(closes: list[float]) -> pd.DataFrame:
    idx = pd.date_range("2024-01-01", periods=len(closes), freq="D")
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


def test_sma_returns_none_when_not_enough_data():
    assert sma(pd.Series([1.0, 2.0, 3.0]), window=5) is None


def test_sma_averages_last_n():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    assert sma(s, window=3) == pytest.approx((3 + 4 + 5) / 3)


def test_ema_uses_full_series():
    s = pd.Series([10.0] * 20)
    assert ema(s, span=9) == pytest.approx(10.0)


def test_rsi_all_gains_is_100():
    s = pd.Series(np.arange(1, 30, dtype=float))  # strictly increasing
    assert rsi(s, period=14) == pytest.approx(100.0)


def test_rsi_none_when_too_short():
    assert rsi(pd.Series([1.0, 2.0]), period=14) is None


def test_bollinger_bands_shape():
    s = pd.Series([100.0] * 25)
    bands = bollinger_bands(s, window=20)
    assert bands is not None
    lower, mid, upper = bands
    assert mid == pytest.approx(100.0)
    assert lower == pytest.approx(100.0)  # zero variance -> bands collapse to mid
    assert upper == pytest.approx(100.0)


def test_vwap_weights_by_volume():
    idx = pd.date_range("2024-01-01 09:30", periods=2, freq="5min")
    intraday = pd.DataFrame(
        {
            "High": [10.0, 12.0],
            "Low": [10.0, 12.0],
            "Close": [10.0, 12.0],
            "Volume": [100, 300],
        },
        index=idx,
    )
    # typical price == close here (High==Low==Close), so vwap is volume-weighted avg of [10, 12]
    expected = (10 * 100 + 12 * 300) / 400
    assert vwap(intraday) == pytest.approx(expected)


def test_vwap_none_when_no_intraday_volume():
    idx = pd.date_range("2024-01-01 09:30", periods=1, freq="5min")
    intraday = pd.DataFrame({"High": [10.0], "Low": [10.0], "Close": [10.0], "Volume": [0]}, index=idx)
    assert vwap(intraday) is None


def test_compute_technicals_falls_back_gracefully_with_short_history():
    daily = _daily_frame([100.0, 101.0, 102.0])  # far too short for SMA50/200/BB20
    result = compute_technicals(daily, intraday=None, fallback_price=102.0)

    assert result["ma50"] == 102.0
    assert result["ma200"] == 102.0
    assert result["bbLower"] == 102.0
    assert result["bbUpper"] == 102.0
    assert result["rsi"] == 50.0
    assert len(result["warnings"]) >= 4


def test_compute_technicals_uses_real_indicators_with_enough_history():
    closes = [100.0 + i * 0.1 for i in range(250)]
    daily = _daily_frame(closes)
    result = compute_technicals(daily, intraday=None, fallback_price=closes[-1])

    assert result["ma50"] == pytest.approx(sma(pd.Series(closes), 50), abs=0.01)
    assert result["ma200"] == pytest.approx(sma(pd.Series(closes), 200), abs=0.01)
    # steadily increasing closes -> RSI pinned at 100
    assert result["rsi"] == pytest.approx(100.0)
