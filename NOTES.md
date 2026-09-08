# Implementation notes: approximations & what to revisit

`PROJECT_BRIEF.md` explicitly anticipates that a couple of Phase 1 data
points can't be sourced exactly from free APIs yet. This documents the
approximations made and how to tell if/when they need upgrading.

## IV rank / IV percentile (`stock_analyzer/options.py`)

True IV rank/percentile need a 52-week history of a stock's *implied*
volatility, which yfinance doesn't provide (it only exposes a live options
chain). As the brief suggests ("yfinance's options chain can approximate IV
rank if nothing else is available yet"), this implementation:

1. Reads the ATM (closest-strike) implied volatility from the nearest listed
   expiration.
2. Ranks that value against the stock's own trailing-1-year **realized**
   volatility distribution (rolling 30-day annualized stdev of returns),
   rather than a true historical IV series.

This is a reasonable proxy for "is volatility pricing rich or cheap right
now relative to this stock's usual regime," but it is not the same number a
broker's IV rank widget shows. **Revisit** by wiring in Tradier's sandbox API
or CBOE data (as the brief names) once available — `compute_options_metrics`
is isolated in `options.py` specifically so this swap doesn't touch the rest
of the pipeline.

## Sector average P/E (`stock_analyzer/fundamentals.py`)

yfinance has no "sector average P/E" field. This approximates it using the
trailing P/E of a representative sector-tracking ETF (e.g. Technology →
`XLK`), via `SECTOR_ETF_MAP`. This is a real, live, free number, but it's an
ETF's blended P/E, not a computed average of true sector peers — closer for
concentrated sectors (Tech's mega-caps dominate `XLK`) than a peer-average
would be. **Revisit** if this drifts noticeably from what you'd expect for a
given sector, or if a real peer-comparison data source becomes available.

## Sentiment / catalyst (`stock_analyzer/sentiment.py`)

Headlines come from `yfinance.Ticker.news` (free, no separate key), which
occasionally returns sparse, syndicated, or only loosely-relevant articles —
there's no guaranteed depth or recency here, unlike a paid news API
(Benzinga, NewsAPI). Tone scoring and catalyst summarization are one Claude
API call per ticker (model: `claude-sonnet-5`); the prompt asks it to
default to sentiment `0` when headlines are sparse/irrelevant, rather than
force a reading if there is nothing there.

Without `ANTHROPIC_API_KEY` set, or if the call fails for any reason
(network, rate limit, malformed response), this falls back to
`sentiment=0` and the raw top headline as `catalyst` — `analyze()` never
raises because of this step. **Revisit**: swap to a dedicated news API if
`yfinance.news` proves too sparse for tickers you actually watch.

## VWAP (`stock_analyzer/technicals.py`)

VWAP is fundamentally an intraday metric. This computes it from the current
session's 5-minute bars (`yfinance` `period="1d", interval="5m"`), which is
only available while/after that session has traded. Outside market hours
with no intraday bars yet (or for tickers with sparse intraday data),
it falls back to the most recent daily bar's typical price
`(High+Low+Close)/3`, which is a coarser stand-in, not a true VWAP. This
fallback is recorded in the result's `warnings`.

## Backtest inputs (`stock_analyzer/backtest.py`, Phase 3)

The composite score's `sentiment` and `peVsSector` inputs come from live news
and a live sector-ETF lookup — neither has a free, reliable *historical*
source, so the backtest holds both at neutral (`sentiment=0`, `peVsSector=0`)
at every historical point. This means Phase 3 backtests the **technicals-only
reduction** of the composite (trend vs. moving averages, RSI, EMA9 short-term
trend, Bollinger Band position) — not the full live score, which can also
move on news/valuation. `ivRank`/`expectedMove` aren't part of the composite
formula at all (they only drive the options-stance text and price targets),
so the backtest skips them entirely rather than fabricating history for them.

**Revisit** if you find or pay for a historical news-sentiment or
sector-P/E feed — plug it into `backtest_ticker()`'s per-date `score(...)`
call the same way `sentiment=0`/`peVsSector=0` are set now.

This environment's outbound network policy blocks Yahoo Finance
(`query1.finance.yahoo.com`), so the backtest engine here was built and
tested entirely against synthetic, deterministic price series (a straight
uptrend/downtrend) rather than real history — see `tests/test_backtest.py`.
Run `python backtest.py` on a machine with normal internet access to get
real results.

## What did NOT need approximating

- **Price, SMA50/200, EMA9, RSI(14), Bollinger Bands(20)**: computed
  directly from yfinance's real daily OHLCV history — no proxy needed once
  ~200 days of history exist for the ticker (the code falls back to the
  current price for these too if history is unexpectedly short, e.g. a very
  recent IPO — also recorded in `warnings`).
- **P/E ratio, 52-week high/low**: straight from yfinance's `info`/`fast_info`.
- **Expected move**: standard ATM-straddle-over-price approximation, which
  is the same method most retail platforms use — not a proxy specific to
  this project.
