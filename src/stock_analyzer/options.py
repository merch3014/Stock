"""Options metrics: IV rank, IV percentile, expected move.

yfinance exposes a live options chain (via `Ticker.option_chain(expiration)`)
but no historical implied-volatility series, so true IV rank/percentile
(current IV vs. its own 52-week range) can't be computed from it alone. Per
the project brief, this approximates IV rank/percentile by ranking the
stock's current ATM implied volatility against its own trailing 1-year
realized-volatility regime — a reasonable stand-in until a real options
history provider (Tradier, CBOE) is wired in.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR = 252


def _atm_row(chain: pd.DataFrame, price: float) -> pd.Series | None:
    """Row of `chain` whose strike is closest to `price`."""
    if chain is None or chain.empty:
        return None
    idx = (chain["strike"] - price).abs().idxmin()
    return chain.loc[idx]


def _mid_price(row: pd.Series) -> float | None:
    bid = row.get("bid")
    ask = row.get("ask")
    if bid is not None and ask is not None and bid > 0 and ask > 0:
        return float((bid + ask) / 2)
    last = row.get("lastPrice")
    return float(last) if last not in (None, 0) else None


def realized_volatility_series(
    closes: pd.Series, window: int = 30, trading_days: int = TRADING_DAYS_PER_YEAR
) -> pd.Series:
    """Rolling `window`-day annualized realized volatility of daily returns."""
    returns = closes.pct_change().dropna()
    return returns.rolling(window).std().dropna() * np.sqrt(trading_days)


def iv_rank_and_percentile(atm_iv: float, hv_series: pd.Series) -> tuple[float, float]:
    """Rank `atm_iv` against the historical realized-vol distribution `hv_series`.

    Returns (ivRank, ivPercentile), both 0-100. ivRank is where atm_iv sits
    between the series' min and max; ivPercentile is the fraction of the
    series below atm_iv. See module docstring for why this is a proxy, not
    a true IV rank.
    """
    if hv_series is None or hv_series.empty:
        return 50.0, 50.0
    hv_min, hv_max = float(hv_series.min()), float(hv_series.max())
    if hv_max > hv_min:
        iv_rank = (atm_iv - hv_min) / (hv_max - hv_min) * 100
    else:
        iv_rank = 50.0
    iv_percentile = float((hv_series < atm_iv).mean()) * 100
    return max(0.0, min(100.0, iv_rank)), max(0.0, min(100.0, iv_percentile))


def nearest_expiration(expirations: list[str]) -> str | None:
    """First (soonest) expiration date string, or None if there are none.

    yfinance already returns `Ticker.options` sorted chronologically.
    """
    return expirations[0] if expirations else None


def compute_options_metrics(
    yf_ticker, price: float, daily_closes: pd.Series
) -> dict:
    """Fetch the nearest options chain and derive ivRank/ivPercentile/expectedMove.

    `yf_ticker` is a `yfinance.Ticker` (or any object exposing `.options` and
    `.option_chain(date)` with the same shape, which is all the tests mock).
    """
    warnings: list[str] = []

    try:
        expirations = list(yf_ticker.options or [])
    except Exception as exc:
        expirations = []
        warnings.append(f"Could not list option expirations: {exc}")

    expiration = nearest_expiration(expirations)
    if expiration is None:
        warnings.append("No listed options found; ivRank/ivPercentile/expectedMove defaulted.")
        return {
            "ivRank": 50.0,
            "ivPercentile": 50.0,
            "expectedMove": 5.0,
            "warnings": warnings,
        }

    try:
        chain = yf_ticker.option_chain(expiration)
        calls, puts = chain.calls, chain.puts
    except Exception as exc:
        warnings.append(f"Could not load option chain for {expiration}: {exc}")
        return {
            "ivRank": 50.0,
            "ivPercentile": 50.0,
            "expectedMove": 5.0,
            "warnings": warnings,
        }

    atm_call = _atm_row(calls, price)
    atm_put = _atm_row(puts, price)

    ivs = [
        float(row["impliedVolatility"])
        for row in (atm_call, atm_put)
        if row is not None and row.get("impliedVolatility") not in (None, 0)
    ]
    atm_iv = sum(ivs) / len(ivs) if ivs else None

    if atm_iv is None:
        warnings.append("No implied volatility on the ATM contracts; ivRank/ivPercentile defaulted.")
        iv_rank, iv_percentile = 50.0, 50.0
    else:
        hv_series = realized_volatility_series(daily_closes)
        iv_rank, iv_percentile = iv_rank_and_percentile(atm_iv, hv_series)

    call_mid = _mid_price(atm_call) if atm_call is not None else None
    put_mid = _mid_price(atm_put) if atm_put is not None else None
    if call_mid is not None and put_mid is not None and price:
        expected_move = (call_mid + put_mid) / price * 100
    else:
        warnings.append("Could not price the ATM straddle; expectedMove defaulted to 5%.")
        expected_move = 5.0

    return {
        "ivRank": round(iv_rank, 2),
        "ivPercentile": round(iv_percentile, 2),
        "expectedMove": round(expected_move, 2),
        "warnings": warnings,
    }
