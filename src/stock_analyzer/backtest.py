"""Phase 3: backtest the composite score's verdict buckets against what
actually happened next.

Per PROJECT_BRIEF.md:
    Pull 1-2 years of historical price data for a basket of ~20 tickers.
    Recompute the composite score at each historical point (using only data
    that would have been available at that time — no lookahead). Check
    whether "Bullish" periods actually outperformed "Bearish" periods going
    forward over reasonable holding windows (1 week, 1 month). This is the
    step that tells you whether the scoring weights are real or arbitrary.

No-lookahead guarantee: at each historical date, this recomputes ma50/ma200/
ema9/rsi/Bollinger Bands using `stock_analyzer.technicals`'s own scalar
functions (the exact ones `analyze()` uses live) on a slice of price history
that ends at that date — `closes.iloc[:i + 1]`, never anything past it. The
same slice is fed straight into `stock_analyzer.scoring.score()`, so the
backtest is scoring history with the live code path, not a reimplementation
of it. Forward returns (what we're checking the score against) are computed
from data *after* that date, but only ever used as the outcome being
evaluated, never as an input to the score itself.

Known limitation (see NOTES.md): sentiment and peVsSector have no free,
reliable historical source, so both are held at neutral (0) for every
historical point here — this backtests the technicals-only reduction of the
composite (trend, RSI, EMA9, Bollinger position), not the full live score.
ivRank/expectedMove aren't part of the composite formula at all (they only
drive the options-stance text and price targets), so they're skipped
entirely rather than faked.
"""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd
import yfinance as yf

from .exceptions import StockAnalysisError
from .scoring import score
from .technicals import bollinger_bands, ema, rsi, sma

# A ~20-ticker, sector-diversified basket, per the brief's "basket of ~20
# tickers" — swap for your own personal watchlist via `run_backtest(tickers=...)`.
DEFAULT_BASKET: list[str] = [
    "AAPL", "MSFT", "GOOGL", "NVDA", "META",  # tech
    "AMZN", "TSLA", "HD", "DIS", "SBUX",       # consumer
    "JPM", "V", "BAC",                          # financials
    "UNH", "JNJ", "PFE",                        # healthcare
    "XOM", "CVX",                                # energy
    "PG", "KO",                                  # staples
]

# label -> trading days held forward
HOLDING_WINDOWS: dict[str, int] = {"1w": 5, "1m": 21}

VERDICT_ORDER: list[str] = ["Bullish", "Mildly Bullish", "Neutral", "Mildly Bearish", "Bearish"]


def backtest_ticker(
    daily: pd.DataFrame,
    holding_windows: dict[str, int] = HOLDING_WINDOWS,
    min_lookback: int = 200,
) -> pd.DataFrame:
    """Walk `daily` (needs a chronologically-ordered 'Close' column) day by
    day, scoring each date from only the history up to and including it, and
    recording the actual forward return over each holding window.

    `min_lookback` (default 200, matching SMA200's window) skips dates too
    early to have real indicators yet, rather than silently scoring off the
    price-fallback values `stock_analyzer.technicals` uses for live quotes
    with thin history — a backtest of fallback values would be meaningless.

    Returns a DataFrame with columns: date, price, composite, verdict, and
    one `fwd_return_<label>` column per holding window (NaN for the most
    recent dates that don't have `days` of future data yet).
    """
    closes = daily["Close"].dropna() if daily is not None and not daily.empty else pd.Series(dtype=float)
    n = len(closes)
    rows: list[dict[str, Any]] = []

    for i in range(min_lookback, n):
        window = closes.iloc[: i + 1]  # history up to and including day i — nothing past it
        price = float(window.iloc[-1])

        ma50 = sma(window, 50)
        ma200 = sma(window, 200)
        ema9_val = ema(window, 9)
        rsi_val = rsi(window, 14)
        bands = bollinger_bands(window, 20)
        if ma50 is None or ma200 is None or ema9_val is None or rsi_val is None or bands is None:
            continue
        bb_lower, _bb_mid, bb_upper = bands

        result = score(
            {
                "price": price,
                "ma50": ma50,
                "ma200": ma200,
                "rsi": rsi_val,
                "expectedMove": 10.0,  # not used by the composite formula
                "ivRank": 50.0,        # not used by the composite formula
                "sentiment": 0,        # neutral placeholder — no historical source (see NOTES.md)
                "peVsSector": 0.0,     # neutral placeholder — no historical source (see NOTES.md)
                "ema9": ema9_val,
                "bbLower": bb_lower,
                "bbUpper": bb_upper,
            }
        )

        row: dict[str, Any] = {
            "date": closes.index[i],
            "price": price,
            "composite": result["composite"],
            "verdict": result["verdict"],
        }
        for label, hold_days in holding_windows.items():
            j = i + hold_days
            row[f"fwd_return_{label}"] = (float(closes.iloc[j]) / price - 1) if j < n else float("nan")
        rows.append(row)

    return pd.DataFrame(
        rows, columns=["date", "price", "composite", "verdict", *[f"fwd_return_{l}" for l in holding_windows]]
    )


def summarize(rows: pd.DataFrame, holding_windows: dict[str, int] = HOLDING_WINDOWS) -> pd.DataFrame:
    """Per-verdict-bucket stats (sample size, mean/median forward return, win
    rate) for each holding window, across every ticker/date in `rows`
    combined. Every verdict bucket is included even with zero samples, so the
    shape of the report is stable regardless of what a given run happened to
    hit.
    """
    records = []
    for verdict in VERDICT_ORDER:
        group = rows[rows["verdict"] == verdict] if not rows.empty else rows
        record: dict[str, Any] = {"verdict": verdict, "n": len(group)}
        for label in holding_windows:
            col = f"fwd_return_{label}"
            valid = group[col].dropna() if col in group.columns else pd.Series(dtype=float)
            record[f"n_{label}"] = int(len(valid))
            record[f"mean_{label}"] = float(valid.mean()) if len(valid) else float("nan")
            record[f"median_{label}"] = float(valid.median()) if len(valid) else float("nan")
            record[f"win_rate_{label}"] = float((valid > 0).mean()) if len(valid) else float("nan")
        records.append(record)
    return pd.DataFrame(records)


def bullish_vs_bearish_edge(
    rows: pd.DataFrame, holding_windows: dict[str, int] = HOLDING_WINDOWS
) -> dict[str, dict[str, float]]:
    """The number the brief is actually asking Phase 3 to produce: did
    Bullish-flagged periods (Bullish + Mildly Bullish) outperform
    Bearish-flagged ones (Bearish + Mildly Bearish) going forward?

    Returns, per holding window: bullish_mean, bearish_mean, edge
    (bullish_mean - bearish_mean — positive means the score is pointing the
    right way), and the sample size behind each mean.
    """
    bullish = rows[rows["verdict"].isin(["Bullish", "Mildly Bullish"])]
    bearish = rows[rows["verdict"].isin(["Bearish", "Mildly Bearish"])]

    edge: dict[str, dict[str, float]] = {}
    for label in holding_windows:
        col = f"fwd_return_{label}"
        b_valid = bullish[col].dropna() if col in bullish.columns else pd.Series(dtype=float)
        r_valid = bearish[col].dropna() if col in bearish.columns else pd.Series(dtype=float)
        b_mean = float(b_valid.mean()) if len(b_valid) else float("nan")
        r_mean = float(r_valid.mean()) if len(r_valid) else float("nan")
        edge[label] = {
            "bullish_mean": b_mean,
            "bearish_mean": r_mean,
            "edge": (b_mean - r_mean) if pd.notna(b_mean) and pd.notna(r_mean) else float("nan"),
            "bullish_n": int(len(b_valid)),
            "bearish_n": int(len(r_valid)),
        }
    return edge


def run_backtest(
    tickers: list[str] | None = None,
    *,
    period: str = "2y",
    holding_windows: dict[str, int] = HOLDING_WINDOWS,
    min_lookback: int = 200,
    yf_ticker_factory: Callable[[str], Any] = yf.Ticker,
) -> dict:
    """Backtest every ticker in `tickers` (default: DEFAULT_BASKET) over
    `period` of daily history, and combine + summarize the results.

    A ticker that fails to fetch, or has no usable history, is skipped (not
    fatal) with a note in the returned `warnings` — one bad symbol shouldn't
    sink a ~20-ticker basket run.

    Returns {"per_ticker": {ticker: DataFrame}, "combined": DataFrame,
    "summary": DataFrame, "edge": dict, "warnings": [...]}.

    Raises StockAnalysisError only if *no* ticker produced usable data.
    """
    tickers = tickers or DEFAULT_BASKET
    warnings: list[str] = []
    per_ticker: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        try:
            yf_ticker = yf_ticker_factory(ticker)
            daily = yf_ticker.history(period=period, interval="1d")
        except Exception as exc:
            warnings.append(f"Could not fetch history for {ticker}: {exc}")
            continue

        if daily is None or daily.empty:
            warnings.append(f"No price history for {ticker}; skipped.")
            continue

        ticker_rows = backtest_ticker(daily, holding_windows, min_lookback)
        if ticker_rows.empty:
            warnings.append(f"Not enough history for {ticker} to score any dates; skipped.")
            continue
        per_ticker[ticker] = ticker_rows

    if not per_ticker:
        raise StockAnalysisError("No tickers produced usable backtest data.")

    combined = pd.concat(
        [df.assign(ticker=t) for t, df in per_ticker.items()],
        ignore_index=True,
    )
    summary = summarize(combined, holding_windows)
    edge = bullish_vs_bearish_edge(combined, holding_windows)

    return {
        "per_ticker": per_ticker,
        "combined": combined,
        "summary": summary,
        "edge": edge,
        "warnings": warnings,
    }
