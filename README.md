# AI Stock Analyzer — Phase 1 + 2 + 3

Implements the first three phases of [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md):

- **Phase 1 — live data pipeline**: given a ticker, fetch live technicals,
  options metrics, fundamentals, and a news-driven sentiment score, and
  return them as a single dict shaped to exactly match every input field
  [`reference/StockAnalyzer.jsx`](./reference/StockAnalyzer.jsx)'s worksheet
  needs — a drop-in replacement for manual/screenshot entry.
- **Phase 2 — composite scoring**: `StockAnalyzer.jsx`'s `useMemo` scoring
  block (trend vs. moving averages, RSI, sentiment, valuation vs. sector,
  EMA9 short-term trend, Bollinger Band position → a 0-100 composite,
  verdict, price targets, and options stance), ported to Python **as-is**,
  per the brief: "Don't redesign them yet; the point of Phase 3 is to find
  out if they're any good before you touch them further."
- **Phase 3 — backtest**: walks 1-2 years of daily history for a ~20-ticker
  basket, recomputing the composite score at each historical date from only
  the data available *as of* that date (no lookahead), then checks whether
  dates the score called "Bullish" actually outperformed dates it called
  "Bearish" over the following 1 week / 1 month.

See [`NOTES.md`](./NOTES.md) for the approximations made where free data
sources don't cover something exactly (IV rank, sector-average P/E, and what
the Phase 3 backtest can and can't reconstruct historically) and how to swap
in a better source later.

> **This environment can't run a real backtest.** Its network policy blocks
> outbound access to Yahoo Finance, so `stock_analyzer/backtest.py` was built
> and tested against synthetic, deterministic price series only (see
> `tests/test_backtest.py`) — correct math, no real market conclusions yet.
> Run `python backtest.py` on a machine with normal internet access for
> actual results.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # or requirements.txt for runtime only
pip install -e .
```

News/sentiment scoring calls the Claude API — set `ANTHROPIC_API_KEY` in your
environment to use it. Without a key, `analyze()` still works and returns a
neutral sentiment plus the raw top headline as the catalyst instead.

## Usage

### As a library

```python
from stock_analyzer import analyze, score, analyze_and_score, run_backtest

data = analyze("AAPL")               # Phase 1 only: live worksheet inputs
result = score(data)                  # Phase 2 only: composite score from those inputs
combined = analyze_and_score("AAPL")  # both: combined["score"] == score(combined)

print(data["price"], data["rsi"], data["catalyst"])
print(result["composite"], result["verdict"], result["stockAction"])

backtest = run_backtest(["AAPL", "MSFT", "NVDA"])  # Phase 3: needs real network access
print(backtest["edge"])  # bullish vs. bearish mean forward return, per holding window
```

### As a CLI

Per the brief's Phase 4 target, `python analyze.py TICKER` works directly
from the repo root (no install needed):

```bash
python analyze.py AAPL
python analyze.py AAPL --json   # raw analyze() dict as JSON
```

Or, once installed, the same via the package:

```bash
python -m stock_analyzer AAPL MSFT GOOG   # multiple tickers
python -m stock_analyzer AAPL --json --indent 0
```

Example report (now including the Phase 2 composite score):

```
=== AAPL ===
Fetched: 2026-09-08T12:00:00+00:00

Price                227.52
SMA 50               219.30
SMA 200              205.11
EMA 9                225.80
VWAP                 226.94
RSI (14)             61.20
BB lower             210.40
BB mid               219.30
BB upper             228.20
IV rank              38.50
IV percentile        42.10
Expected move %      6.80
P/E ratio            34.12
P/E vs sector %      12.40
52-week high         237.23
52-week low          164.08
Sentiment (-2..2)    1
Catalyst             Beat on earnings, raised full-year guidance

Composite: 65 (Mildly Bullish)
Stock action:  Hold / Small Add
Options view:  Buy calls or call debit spreads — cheap premium, favorable trend.
Price target:  $230.10 - $242.80  (profit-take $238.40, stop $220.10)
Breakdown:
  Trend (price vs MAs)         +9
  Momentum (RSI)               +7
  News / sentiment             +12
  Valuation vs sector          -6
  Short-term trend (EMA9)      +2
  Band position (BB20)         +1
```

### Backtest (Phase 3)

```bash
python backtest.py                          # default ~20-ticker basket, 2y of history
python backtest.py AAPL MSFT NVDA --period 1y
python backtest.py --json
```

Example report:

```
=== Backtest: verdict vs. actual forward return ===

Verdict              N     mean 1w   win% 1w     mean 1m   win% 1m
Bullish            412      +0.68%   +58.98%      +2.10%   +61.41%
Mildly Bullish     530      +0.31%   +54.15%      +1.05%   +55.66%
Neutral            301      -0.02%   +49.83%      -0.12%   +48.17%
Mildly Bearish     288      -0.24%   +45.14%      -1.03%   +42.71%
Bearish            190      -0.61%   +40.53%      -2.44%   +38.42%

Bullish (+Mildly Bullish) vs. Bearish (+Mildly Bearish), forward return:
  1w: bullish  +0.47% (n=942) vs. bearish  -0.39% (n=478)  -> edge  +0.86%
    Bullish periods outperformed Bearish periods over 1w.
  1m: bullish  +1.51% (n=942) vs. bearish  -1.58% (n=478)  -> edge  +3.09%
    Bullish periods outperformed Bearish periods over 1m.
```

(Illustrative numbers — this environment can't reach Yahoo Finance to
produce real ones; see the warning at the top of this file.) A negative or
near-zero edge would mean the weights in `scoring.py` aren't actually
predictive and are due for revision — that's the judgment call this phase
exists to inform, not something this repo should decide for you.

## Output shape

`analyze(ticker) -> dict` returns exactly the fields `StockAnalyzer.jsx`'s
`useState` inputs need (see its `FIELD_META` list), plus a few diagnostic
extras the worksheet can ignore:

| Key | Source |
|---|---|
| `ticker`, `price` | live quote (yfinance) |
| `ma50`, `ma200`, `ema9`, `vwap`, `rsi`, `bbLower`, `bbMid`, `bbUpper` | computed from yfinance daily/intraday history |
| `ivRank`, `ivPercentile`, `expectedMove` | yfinance options chain (approximated — see NOTES.md) |
| `peRatio`, `peVsSector`, `week52High`, `week52Low` | yfinance fundamentals + sector-ETF P/E proxy |
| `sentiment`, `catalyst` | yfinance headlines scored by the Claude API |
| `fetchedAt` | UTC timestamp of the fetch |
| `sectorAvgPE`, `warnings` | diagnostics: the sector ETF's P/E used, and any fallbacks that were triggered |

`score(data) -> dict` (Phase 2) takes that same shape and returns the
composite: `composite` (0-100), `verdict`/`verdictTone`, `stockAction`,
`optionsView`, `targetLow`/`targetHigh`/`profitTake`/`stopLevel`, and a
`breakdown` list of each sub-score's `{label, value}` — a direct port of
`StockAnalyzer.jsx`'s `result` object, weights and all.

`analyze_and_score(ticker) -> dict` is `analyze()`'s dict with `["score"]`
set to `score(...)` of itself — what the CLI uses.

`run_backtest(tickers=None) -> dict` (Phase 3) returns `{"per_ticker": {...},
"combined": DataFrame, "summary": DataFrame, "edge": {...}, "warnings":
[...]}`. `summary` has one row per verdict bucket (n, mean/median/win-rate
forward return per holding window); `edge` is the Bullish-vs-Bearish
comparison itself — the number that answers the brief's Phase 3 question.

## Errors

An invalid/unknown ticker, or a total inability to fetch a price, raises
`stock_analyzer.StockAnalysisError` (library use) or prints `error: ...` to
stderr and exits non-zero (CLI use). Partial failures (e.g. can't compute
VWAP because markets are closed, no options listed, no Anthropic key) don't
raise — they fall back to a sensible default and are listed in the result's
`warnings`. `run_backtest` raises the same way only if *every* requested
ticker fails to fetch; a single bad ticker in a basket is skipped with a
warning instead.

## Testing

```bash
pytest
```

Every test mocks `yfinance` and the Anthropic client — no network access or
API keys are required to run the suite. The backtest tests use synthetic,
deterministic price series (a straight uptrend/downtrend) rather than real
history, including a dedicated test that mutates future prices and asserts a
historical date's score doesn't change — the no-lookahead guarantee Phase 3
depends on.

## Project layout

```
analyze.py                   # `python analyze.py TICKER` (Phase 4 preview)
backtest.py                  # `python backtest.py [TICKER ...]` (Phase 3)
src/stock_analyzer/
  __init__.py                 # public API: analyze, score, analyze_and_score, run_backtest, StockAnalysisError
  analyzer.py                 # analyze(ticker) -> dict orchestrator + analyze_and_score()
  technicals.py                # SMA/EMA/RSI/Bollinger Bands/VWAP
  options.py                   # IV rank/percentile + expected move
  fundamentals.py              # P/E, 52-week range, P/E vs. sector
  sentiment.py                 # headlines + Claude tone/catalyst scoring
  scoring.py                   # Phase 2: composite score, ported as-is from StockAnalyzer.jsx
  backtest.py                   # Phase 3: verdict-vs-forward-return backtest engine
  backtest_cli.py                # `python backtest.py [...]` implementation
  cli.py, __main__.py          # `python -m stock_analyzer TICKER [...]`
  exceptions.py                # StockAnalysisError
tests/
  test_technicals.py, test_options.py, test_fundamentals.py,
  test_sentiment.py, test_scoring.py, test_backtest.py, test_backtest_cli.py,
  test_analyzer.py, test_cli.py
reference/
  StockAnalyzer.jsx            # the prototype this pipeline replaces / scoring is ported from
PROJECT_BRIEF.md               # the full build brief
NOTES.md                       # approximations made (Phase 1 data + Phase 3 backtest inputs) and what to revisit
```

## Next steps

- **Run the real backtest**: this environment can't reach Yahoo Finance (see
  the warning above) — run `python backtest.py` yourself and look at the
  `edge` numbers. If Bullish periods didn't clearly outperform Bearish ones
  over 1 week/1 month, that's the signal to revisit `scoring.py`'s weights
  (which is exactly the point of having built Phase 2 as a straight,
  unmodified port rather than tuning blind).
- **Phase 4**: this repo's `analyze.py`/CLI already prints a full report
  (data + composite score); decide on scheduled watchlist scans once the
  output is trustworthy daily.
