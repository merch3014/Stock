# AI Stock Analyzer — Build Brief for Claude Code

## Goal

Turn the prototype composite-scoring worksheet into a real tool that pulls live data instead
of manual/screenshot entry, for a personal research watchlist. Not for public distribution or
automated trading — personal decision support only.

## Phase 1 — Data pipeline (start here)

Build a Python project that, given a ticker, fetches:

- **Price/technicals**: current price, SMA50, SMA200, EMA9, VWAP, RSI(14), Bollinger
  Bands(20) — via `yfinance` to start (free, no key required); swap to Polygon.io or Alpha
  Vantage later if rate limits become a problem
- **Options**: IV rank, IV percentile, expected move — via Tradier's sandbox API or CBOE
  data if accessible; yfinance's options chain can approximate IV rank if nothing else is
  available yet
- **Fundamentals**: P/E ratio, 52-week high/low, sector average P/E — yfinance covers most
  of this
- **News/sentiment**: pull latest headlines via a news API (NewsAPI, Benzinga, or even RSS
  feeds), then call the Claude API to score tone and summarize the catalyst — this is the
  one step that should use an LLM rather than hardcoded rules

Output: a single function `analyze(ticker) -> dict` that returns everything the worksheet's
inputs needed, so it's a drop-in replacement for manual entry.

## Phase 2 — Port the scoring logic

Reuse the composite scoring rules from the prototype artifact (trend vs. moving averages,
RSI, EMA9 short-term trend, Bollinger Band position, sentiment, valuation vs. sector) — port
them from JS to Python as-is initially. Don't redesign them yet; the point of Phase 3 is to
find out if they're any good before you touch them further.

## Phase 3 — Backtest

Before trusting any live signal:

- Pull 1-2 years of historical price data for a basket of ~20 tickers
- Recompute the composite score at each historical point (using only data that would
  have been available at that time — no lookahead)
- Check whether "Bullish" periods actually outperformed "Bearish" periods going forward
  over reasonable holding windows (1 week, 1 month)
- This is the step that tells you whether the scoring weights are real or arbitrary — expect
  to revise them here

## Phase 4 — Output & cadence

- CLI tool first: `python analyze.py TICKER` → printed report
- Once that's solid, decide: scheduled daily scan of a watchlist (cron + email/notification)
  vs. on-demand lookup. Don't build scheduling until the CLI output is something you'd
  actually trust reading every day.

## Explicit non-goals for now

- No automated trade execution
- No public/shared deployment — personal use only
- Options recommendations stay a "worth a closer look" flag, not an auto-generated trade
  ticket, until backtested

## Reference

The interactive prototype (composite scoring formula, field list, UI layout) is attached as
`StockAnalyzer.jsx` — use its `useMemo` scoring block as the starting logic to port into
Python.
