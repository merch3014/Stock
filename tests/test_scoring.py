"""Tests for stock_analyzer.scoring — the ported StockAnalyzer.jsx composite score.

Where a test needs a concrete expected number, it's computed independently
(by hand, or via a standalone calculation, documented inline) rather than by
calling `score()` itself and asserting it equals its own output.
"""

from __future__ import annotations

import pytest

from stock_analyzer.scoring import clamp, score


def _base_inputs(**overrides):
    """A neutral baseline: price sits exactly on every reference level, so
    every sub-score is 0 and composite lands exactly on 50 unless overridden."""
    data = {
        "price": 100.0,
        "ma50": 100.0,
        "ma200": 100.0,
        "rsi": 50.0,
        "expectedMove": 10.0,
        "ivRank": 30.0,
        "sentiment": 0,
        "peVsSector": 0.0,
        "ema9": 100.0,
        "bbLower": 90.0,
        "bbUpper": 110.0,  # price=100 is exactly mid-band -> bandScore 0
    }
    data.update(overrides)
    return data


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-5, 0, 10) == 0
    assert clamp(15, 0, 10) == 10


def test_neutral_baseline_gives_composite_50_neutral_verdict():
    result = score(_base_inputs())
    assert result["composite"] == pytest.approx(50.0)
    assert result["verdict"] == "Neutral"
    assert result["verdictTone"] == "flat"
    assert result["stockAction"] == "Hold, No Action"
    for row in result["breakdown"]:
        assert row["value"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    "rsi, expected_score",
    [
        (50, 0.0),      # (50-50)*0.6 = 0
        (100, 15.0),    # (100-50)*0.6 = 30 -> clamped to 15
        (0, -15.0),     # (0-50)*0.6 = -30 -> clamped to -15
        (75, 15.0),     # (75-50)*0.6 = 15, exactly at the clamp boundary
    ],
)
def test_rsi_score_matches_hand_calculation_and_clamps(rsi, expected_score):
    result = score(_base_inputs(rsi=rsi))
    momentum_row = next(r for r in result["breakdown"] if r["label"] == "Momentum (RSI)")
    assert momentum_row["value"] == pytest.approx(expected_score)


@pytest.mark.parametrize("sentiment, expected_score", [(-2, -24), (-1, -12), (0, 0), (1, 12), (2, 24)])
def test_sentiment_score_is_linear_times_12(sentiment, expected_score):
    result = score(_base_inputs(sentiment=sentiment))
    row = next(r for r in result["breakdown"] if r["label"] == "News / sentiment")
    assert row["value"] == expected_score


@pytest.mark.parametrize(
    "pe_vs_sector, expected_score",
    [
        (0, 0.0),
        (50, -10.0),   # -50*0.8 = -40 -> clamped to -10 (overpriced vs sector -> penalized)
        (-50, 10.0),   # -(-50)*0.8 = 40 -> clamped to 10 (cheap vs sector -> rewarded)
        (12.5, -10.0),  # -12.5*0.8 = -10, exactly at the clamp boundary
    ],
)
def test_valuation_score_matches_hand_calculation_and_clamps(pe_vs_sector, expected_score):
    result = score(_base_inputs(peVsSector=pe_vs_sector))
    row = next(r for r in result["breakdown"] if r["label"] == "Valuation vs sector")
    assert row["value"] == pytest.approx(expected_score)


def test_short_trend_score_zero_when_ema9_not_positive():
    result = score(_base_inputs(ema9=0, price=120))
    row = next(r for r in result["breakdown"] if r["label"] == "Short-term trend (EMA9)")
    assert row["value"] == 0


def test_short_trend_score_matches_hand_calculation():
    # ((110-100)/100)*150 = 15 -> clamped to 8
    result = score(_base_inputs(price=110, ema9=100))
    row = next(r for r in result["breakdown"] if r["label"] == "Short-term trend (EMA9)")
    assert row["value"] == pytest.approx(8.0)


def test_band_score_zero_when_band_span_not_positive():
    result = score(_base_inputs(bbLower=100, bbUpper=100))
    row = next(r for r in result["breakdown"] if r["label"] == "Band position (BB20)")
    assert row["value"] == 0


def test_band_score_matches_hand_calculation():
    # price at top of a 90-110 band: ((110-90)/20 - 0.5)*20 = (1-0.5)*20 = 10 -> clamped to 8
    result = score(_base_inputs(price=110, bbLower=90, bbUpper=110))
    row = next(r for r in result["breakdown"] if r["label"] == "Band position (BB20)")
    assert row["value"] == pytest.approx(8.0)


def test_trend_score_matches_hand_calculation():
    # ((110-100)/100)*200 + ((100-90)/90)*150 = 20 + 16.666... = 36.666 -> clamped to 25
    result = score(_base_inputs(price=110, ma50=100, ma200=90))
    row = next(r for r in result["breakdown"] if r["label"] == "Trend (price vs MAs)")
    assert row["value"] == pytest.approx(25.0)


@pytest.mark.parametrize(
    "composite_inputs, verdict, tone, action",
    [
        # sentiment alone drives composite to exactly 50 + 24 = 74 -> Bullish
        ({"sentiment": 2}, "Bullish", "up", "Add / Initiate"),
        # 50 + 12 = 62 -> Mildly Bullish
        ({"sentiment": 1}, "Mildly Bullish", "up", "Hold / Small Add"),
        # baseline: 50 -> Neutral
        ({}, "Neutral", "flat", "Hold, No Action"),
        # 50 - 12 = 38 -> Mildly Bearish
        ({"sentiment": -1}, "Mildly Bearish", "down", "Trim"),
        # 50 - 24 = 26 -> Bearish
        ({"sentiment": -2}, "Bearish", "down", "Reduce / Exit"),
    ],
)
def test_verdict_tone_and_action_thresholds(composite_inputs, verdict, tone, action):
    result = score(_base_inputs(**composite_inputs))
    assert result["verdict"] == verdict
    assert result["verdictTone"] == tone
    assert result["stockAction"] == action


@pytest.mark.parametrize(
    "composite_inputs, iv_rank, expected_view_contains",
    [
        ({"sentiment": 2}, 60, "Sell cash-secured puts"),
        ({"sentiment": 2}, 40, "Buy calls"),
        ({"sentiment": -2}, 60, "Sell call credit spreads"),
        ({"sentiment": -2}, 40, "Buy puts"),
        ({}, 60, "Premium-neutral"),  # composite==50, neither branch's threshold hit
    ],
)
def test_options_view_selects_correct_quadrant(composite_inputs, iv_rank, expected_view_contains):
    result = score(_base_inputs(ivRank=iv_rank, **composite_inputs))
    assert expected_view_contains in result["optionsView"]


def test_price_targets_at_neutral_composite_bias_zero():
    # composite=50 -> bias=0, so targets collapse to price scaled by moveFrac alone.
    data = _base_inputs(price=100.0, expectedMove=10.0)
    result = score(data)
    move_frac = 0.10
    assert result["targetLow"] == pytest.approx(100.0 * (1 - move_frac * 0.35))
    assert result["targetHigh"] == pytest.approx(100.0 * (1 + move_frac * 0.65))
    assert result["profitTake"] == pytest.approx(100.0)
    assert result["stopLevel"] == pytest.approx(100.0 * (1 - move_frac * 0.5))


def test_golden_intc_default_scenario_matches_independently_computed_values():
    """StockAnalyzer.jsx's own default useState values for ticker INTC.
    Expected numbers below were computed independently (see the session's
    scratch calculation), not by calling `score()` itself."""
    data = {
        "price": 99.16,
        "ma50": 92.46,
        "ma200": 90.03,
        "rsi": 75.5,
        "expectedMove": 19,
        "ivRank": 28,
        "sentiment": 1,
        "peVsSector": 0,
        "ema9": 96.74,
        "bbLower": 91.54,
        "bbUpper": 98.98,
    }
    result = score(data)

    assert result["composite"] == pytest.approx(100.0)
    assert result["verdict"] == "Bullish"
    assert result["verdictTone"] == "up"
    assert result["stockAction"] == "Add / Initiate"
    assert result["targetLow"] == pytest.approx(103.8701, abs=1e-3)
    assert result["targetHigh"] == pytest.approx(122.7105, abs=1e-3)
    assert result["profitTake"] == pytest.approx(120.82646, abs=1e-3)
    assert result["stopLevel"] == pytest.approx(89.7398, abs=1e-3)
    assert "Buy calls" in result["optionsView"]  # composite>=58, ivRank=28 < 55
