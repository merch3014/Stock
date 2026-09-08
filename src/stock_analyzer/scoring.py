"""Phase 2: composite scoring, ported as-is from StockAnalyzer.jsx's `useMemo` block.

Per PROJECT_BRIEF.md: "Reuse the composite scoring rules from the prototype
artifact ... port them from JS to Python as-is initially. Don't redesign
them yet; the point of Phase 3 is to find out if they're any good before
you touch them further." So every constant, threshold, and formula below is
a direct, line-for-line translation of reference/StockAnalyzer.jsx's
`result = useMemo(...)` block — do not "fix" or rebalance the weights here;
that's Phase 3's job, once backtesting shows whether they're worth keeping.
"""

from __future__ import annotations


def clamp(n: float, lo: float, hi: float) -> float:
    """Same as the JSX's `clamp = (n, min, max) => Math.min(max, Math.max(min, n))`."""
    return min(hi, max(lo, n))


def score(data: dict) -> dict:
    """Compute the composite score and downstream outputs from worksheet inputs.

    `data` is anything with the same keys `stock_analyzer.analyze()` returns
    (or the same fields entered manually into the worksheet): price, ma50,
    ma200, rsi, expectedMove, ivRank, sentiment, peVsSector, ema9, bbLower,
    bbUpper. (bbMid, ivPercentile, peRatio, week52High/Low, and catalyst are
    part of the worksheet's inputs but aren't used by the scoring formula
    itself — same as in the original JSX.)

    Returns a dict with: composite, verdict, verdictTone, targetLow,
    targetHigh, profitTake, stopLevel, stockAction, optionsView, breakdown
    (list of {label, value} dicts) — mirroring the JSX's `result` object.
    """
    price = data["price"]
    ma50 = data["ma50"]
    ma200 = data["ma200"]
    rsi = data["rsi"]
    expected_move = data["expectedMove"]
    iv_rank = data["ivRank"]
    sentiment = data["sentiment"]
    pe_vs_sector = data["peVsSector"]
    ema9 = data["ema9"]
    bb_lower = data["bbLower"]
    bb_upper = data["bbUpper"]

    trend_score = clamp(
        ((price - ma50) / ma50) * 200 + ((ma50 - ma200) / ma200) * 150,
        -25,
        25,
    )
    rsi_score = clamp((rsi - 50) * 0.6, -15, 15)
    sentiment_score = sentiment * 12
    valuation_score = clamp(-pe_vs_sector * 0.8, -10, 10)
    short_trend_score = clamp(((price - ema9) / ema9) * 150, -8, 8) if ema9 > 0 else 0
    band_span = bb_upper - bb_lower
    band_score = (
        clamp((((price - bb_lower) / band_span) - 0.5) * 20, -8, 8) if band_span > 0 else 0
    )

    raw = trend_score + rsi_score + sentiment_score + valuation_score + short_trend_score + band_score
    composite = clamp(50 + raw, 0, 100)

    if composite >= 72:
        verdict, verdict_tone = "Bullish", "up"
    elif composite >= 58:
        verdict, verdict_tone = "Mildly Bullish", "up"
    elif composite > 42:
        verdict, verdict_tone = "Neutral", "flat"
    elif composite > 28:
        verdict, verdict_tone = "Mildly Bearish", "down"
    else:
        verdict, verdict_tone = "Bearish", "down"

    move_frac = expected_move / 100
    bias = (composite - 50) / 50
    target_low = price * (1 + bias * move_frac * 0.6 - move_frac * 0.35)
    target_high = price * (1 + bias * move_frac * 0.6 + move_frac * 0.65)
    profit_take = price * (1 + bias * move_frac * 1.15)
    stop_level = price * (1 - move_frac * 0.5)

    if composite >= 72:
        stock_action = "Add / Initiate"
    elif composite >= 58:
        stock_action = "Hold / Small Add"
    elif composite > 42:
        stock_action = "Hold, No Action"
    elif composite > 28:
        stock_action = "Trim"
    else:
        stock_action = "Reduce / Exit"

    high_iv = iv_rank >= 55
    if composite >= 58 and high_iv:
        options_view = "Sell cash-secured puts or put credit spreads — premium is rich, direction favors you."
    elif composite >= 58 and not high_iv:
        options_view = "Buy calls or call debit spreads — cheap premium, favorable trend."
    elif composite <= 42 and high_iv:
        options_view = "Sell call credit spreads — elevated premium, direction favors downside."
    elif composite <= 42 and not high_iv:
        options_view = "Buy puts or put debit spreads — cheap premium, weakening trend."
    else:
        options_view = "Premium-neutral setup — consider an iron condor or stand aside until conviction improves."

    return {
        "composite": composite,
        "verdict": verdict,
        "verdictTone": verdict_tone,
        "targetLow": target_low,
        "targetHigh": target_high,
        "profitTake": profit_take,
        "stopLevel": stop_level,
        "stockAction": stock_action,
        "optionsView": options_view,
        "breakdown": [
            {"label": "Trend (price vs MAs)", "value": trend_score},
            {"label": "Momentum (RSI)", "value": rsi_score},
            {"label": "News / sentiment", "value": sentiment_score},
            {"label": "Valuation vs sector", "value": valuation_score},
            {"label": "Short-term trend (EMA9)", "value": short_trend_score},
            {"label": "Band position (BB20)", "value": band_score},
        ],
    }
