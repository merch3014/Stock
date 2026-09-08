# AI Stock Analyzer — Phase 1: Live Data Pipeline

Phase 1 of [`PROJECT_BRIEF.md`](./PROJECT_BRIEF.md): given a ticker, fetch live
technicals, options metrics, fundamentals, and a news-driven sentiment score,
and return them as a single dict shaped to exactly match every input field
[`reference/StockAnalyzer.jsx`](./reference/StockAnalyzer.jsx)'s worksheet
needs — a drop-in replacement for manual/screenshot entry.

See [`NOTES.md`](./NOTES.md) for the approximations made where free data
sources don't cover something exactly (IV rank, sector-average P/E) and how
to swap in a better source later.

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
from stock_analyzer import analyze

data = analyze("AAPL")
print(data["price"], data["rsi"], data["catalyst"])
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

Example report:

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
```

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

## Errors

An invalid/unknown ticker, or a total inability to fetch a price, raises
`stock_analyzer.StockAnalysisError` (library use) or prints `error: ...` to
stderr and exits non-zero (CLI use). Partial failures (e.g. can't compute
VWAP because markets are closed, no options listed, no Anthropic key) don't
raise — they fall back to a sensible default and are listed in the result's
`warnings`.

## Testing

```bash
pytest
```

Every test mocks `yfinance` and the Anthropic client — no network access or
API keys are required to run the suite.

## Project layout

```
analyze.py                   # `python analyze.py TICKER` (Phase 4 preview)
src/stock_analyzer/
  __init__.py                 # public API: analyze, StockAnalysisError
  analyzer.py                 # analyze(ticker) -> dict orchestrator
  technicals.py                # SMA/EMA/RSI/Bollinger Bands/VWAP
  options.py                   # IV rank/percentile + expected move
  fundamentals.py              # P/E, 52-week range, P/E vs. sector
  sentiment.py                 # headlines + Claude tone/catalyst scoring
  cli.py, __main__.py          # `python -m stock_analyzer TICKER [...]`
  exceptions.py                # StockAnalysisError
tests/
  test_technicals.py, test_options.py, test_fundamentals.py,
  test_sentiment.py, test_analyzer.py, test_cli.py
reference/
  StockAnalyzer.jsx            # the prototype worksheet this feeds (Phase 2 reference)
PROJECT_BRIEF.md               # the full build brief
NOTES.md                       # approximations made and what to revisit
```

## Next steps

- **Phase 2**: port `StockAnalyzer.jsx`'s `useMemo` composite-scoring block
  (trend/RSI/sentiment/valuation/EMA9/Bollinger position → 0-100 score) into
  Python, feeding it from this module's `analyze()` output.
- **Phase 3**: backtest the composite score against ~20 tickers' historical
  data (no lookahead) before trusting it.
- **Phase 4**: this repo's `analyze.py`/CLI is already a starting point;
  decide on scheduled watchlist scans once the output is trustworthy daily.
