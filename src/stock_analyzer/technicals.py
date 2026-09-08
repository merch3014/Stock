"""Price/technicals: SMA50, SMA200, EMA9, VWAP, RSI(14), Bollinger Bands(20).

All functions take pandas DataFrames shaped like what `yfinance.Ticker.history()`
returns (columns: Open, High, Low, Close, Volume; DatetimeIndex) so they can be
unit-tested with plain DataFrames instead of hitting the network.
"""

from __future__ import annotations

import pandas as pd


def sma(closes: pd.Series, window: int) -> float | None:
    """Simple moving average of the last `window` closes.

    Returns None if there isn't at least `window` data points — callers
    decide how to fall back (e.g. to price) rather than silently averaging
    over a too-short window.
    """
    if len(closes) < window:
        return None
    return float(closes.tail(window).mean())


def ema(closes: pd.Series, span: int) -> float | None:
    """Exponential moving average (last value), using the full series."""
    if closes.empty:
        return None
    return float(closes.ewm(span=span, adjust=False).mean().iloc[-1])


def rsi(closes: pd.Series, period: int = 14) -> float | None:
    """Wilder's RSI over `period`, using the last value of the smoothed series."""
    if len(closes) < period + 1:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    last_avg_loss = avg_loss.iloc[-1]
    if last_avg_loss == 0:
        return 100.0
    rs = avg_gain.iloc[-1] / last_avg_loss
    return float(100 - (100 / (1 + rs)))


def bollinger_bands(
    closes: pd.Series, window: int = 20, num_std: float = 2.0
) -> tuple[float, float, float] | None:
    """Returns (lower, mid, upper) Bollinger Bands, or None if not enough data."""
    if len(closes) < window:
        return None
    recent = closes.tail(window)
    mid = float(recent.mean())
    std = float(recent.std())
    return (mid - num_std * std, mid, mid + num_std * std)


def vwap(intraday: pd.DataFrame) -> float | None:
    """Volume-weighted average price for the session in `intraday`.

    Expects intraday (e.g. 5-minute) bars for a single trading session, with
    High/Low/Close/Volume columns. Returns None if there's no usable intraday
    data (e.g. market closed and yfinance returned nothing) — callers should
    fall back to a coarser approximation (e.g. the daily bar's typical price).
    """
    if intraday is None or intraday.empty or intraday["Volume"].sum() == 0:
        return None
    typical_price = (intraday["High"] + intraday["Low"] + intraday["Close"]) / 3
    cumulative_pv = (typical_price * intraday["Volume"]).cumsum()
    cumulative_vol = intraday["Volume"].cumsum()
    return float((cumulative_pv / cumulative_vol).iloc[-1])


def compute_technicals(
    daily: pd.DataFrame, intraday: pd.DataFrame | None, fallback_price: float
) -> dict:
    """Compute the full technicals block, falling back to `fallback_price`
    (the current quote) for any indicator that can't be computed from the
    available history, so the worksheet always gets a usable number.

    Returns a dict with keys: ma50, ma200, ema9, vwap, rsi, bbLower, bbMid,
    bbUpper, and a `warnings` list describing any fallbacks that were used.
    """
    warnings: list[str] = []
    closes = daily["Close"].dropna() if daily is not None and not daily.empty else pd.Series(dtype=float)

    ma50 = sma(closes, 50)
    if ma50 is None:
        warnings.append("Not enough daily history for SMA50; used current price instead.")
        ma50 = fallback_price

    ma200 = sma(closes, 200)
    if ma200 is None:
        warnings.append("Not enough daily history for SMA200; used current price instead.")
        ma200 = fallback_price

    ema9 = ema(closes, 9)
    if ema9 is None:
        warnings.append("Not enough daily history for EMA9; used current price instead.")
        ema9 = fallback_price

    rsi14 = rsi(closes, 14)
    if rsi14 is None:
        warnings.append("Not enough daily history for RSI(14); defaulted to 50 (neutral).")
        rsi14 = 50.0

    bands = bollinger_bands(closes, 20)
    if bands is None:
        warnings.append("Not enough daily history for Bollinger Bands(20); collapsed to current price.")
        bb_lower, bb_mid, bb_upper = fallback_price, fallback_price, fallback_price
    else:
        bb_lower, bb_mid, bb_upper = bands

    session_vwap = vwap(intraday)
    if session_vwap is None:
        if daily is not None and not daily.empty:
            last_bar = daily.iloc[-1]
            session_vwap = float((last_bar["High"] + last_bar["Low"] + last_bar["Close"]) / 3)
            warnings.append(
                "No intraday data available for VWAP (market likely closed); "
                "approximated using the last daily bar's typical price."
            )
        else:
            session_vwap = fallback_price
            warnings.append("No price history available for VWAP; used current price instead.")

    return {
        "ma50": round(ma50, 2),
        "ma200": round(ma200, 2),
        "ema9": round(ema9, 2),
        "vwap": round(session_vwap, 2),
        "rsi": round(rsi14, 2),
        "bbLower": round(bb_lower, 2),
        "bbMid": round(bb_mid, 2),
        "bbUpper": round(bb_upper, 2),
        "warnings": warnings,
    }
