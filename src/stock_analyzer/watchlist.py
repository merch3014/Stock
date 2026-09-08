"""Phase 4 (on-demand half): scan a watchlist of tickers in one pass.

Per PROJECT_BRIEF.md's Phase 4: "decide: scheduled daily scan of a watchlist
(cron + email/notification) vs. on-demand lookup. Don't build scheduling
until the CLI output is something you'd actually trust reading every day."

This implements only the on-demand half. Scheduled scans (cron + a daily
email/notification) are deliberately NOT built yet: Phase 3's backtest
hasn't been run against real market data from this dev environment (no
network access to Yahoo Finance — see NOTES.md), so there's no evidence yet
that the composite score is worth reading on a schedule, let alone worth an
unattended notification. Build that once `python backtest.py`'s edge numbers
say the score is real, and reuse `scan_watchlist` below as the payload for
whatever triggers it (cron, a scheduled task, etc.) at that point.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from .analyzer import analyze_and_score
from .exceptions import StockAnalysisError


def load_watchlist(path: str | Path) -> list[str]:
    """Read tickers from a text file: one per line, blank lines and anything
    after a '#' ignored. Tickers are upper-cased and de-duplicated, keeping
    first-seen order.
    """
    tickers: dict[str, None] = {}
    for line in Path(path).read_text().splitlines():
        ticker = line.split("#", 1)[0].strip()
        if ticker:
            tickers.setdefault(ticker.upper(), None)
    return list(tickers.keys())


def scan_watchlist(
    tickers: list[str],
    *,
    analyzer: Callable[..., dict] = analyze_and_score,
    **analyzer_kwargs: Any,
) -> dict:
    """Run `analyzer` (default: `analyze_and_score`) over every ticker in
    `tickers`, skipping — with a note in `warnings`, not a crash — any that
    fail.

    Returns {"results": [...], "warnings": [...]}, with `results` sorted by
    composite score descending (most bullish first): a daily read of a
    watchlist wants the notable names at the top, not fetch order.
    """
    results: list[dict] = []
    warnings: list[str] = []

    for ticker in tickers:
        try:
            results.append(analyzer(ticker, **analyzer_kwargs))
        except StockAnalysisError as exc:
            warnings.append(f"Could not analyze {ticker}: {exc}")

    results.sort(key=lambda data: data.get("score", {}).get("composite", 50), reverse=True)
    return {"results": results, "warnings": warnings}
