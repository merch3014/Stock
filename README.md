# Stock — Phase 1: Live Data Fetcher

> **Note**: This scaffold was built without access to `PROJECT_BRIEF.md` or
> `StockAnalyzer.jsx` — the repository was empty when this was written. See
> [`ASSUMPTIONS.md`](./ASSUMPTIONS.md) for what was assumed and what to
> reconcile once those files exist.

Phase 1 fetches live stock data for a ticker and returns it as a flat,
JSON-serializable object shaped for a front-end "worksheet" to consume.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # or requirements.txt for runtime only
pip install -e .
```

## Usage

### As a library

```python
from stock_fetcher import fetch_stock_data

data = fetch_stock_data("AAPL")
print(data["price"], data["changePercent"])
```

### As a CLI

```bash
python -m stock_fetcher AAPL
python -m stock_fetcher AAPL MSFT GOOG   # multiple tickers -> JSON array
python -m stock_fetcher AAPL --indent 0  # compact JSON, good for piping
```

Example output:

```json
{
  "ticker": "AAPL",
  "companyName": "Apple Inc.",
  "currency": "USD",
  "price": 227.52,
  "previousClose": 225.91,
  "open": 226.10,
  "dayHigh": 228.05,
  "dayLow": 225.80,
  "change": 1.61,
  "changePercent": 0.71,
  "volume": 41234567,
  "averageVolume": 52345678,
  "marketCap": 3456789012345,
  "peRatio": 34.12,
  "eps": 6.67,
  "dividendYield": 0.44,
  "fiftyTwoWeekHigh": 237.23,
  "fiftyTwoWeekLow": 164.08,
  "sector": "Technology",
  "industry": "Consumer Electronics",
  "fetchedAt": "2026-09-08T12:00:00+00:00"
}
```

## Errors

An invalid or unknown ticker raises `stock_fetcher.StockFetchError` (library
use) or prints `error: ...` to stderr and exits non-zero (CLI use).

## Testing

```bash
pytest
```

Tests mock `yfinance.Ticker` — no network access or live market data is
required to run the suite.

## Project layout

```
src/stock_fetcher/
  __init__.py     # public API: fetch_stock_data, StockFetchError
  fetcher.py       # core fetch + field-mapping logic
  cli.py           # `python -m stock_fetcher TICKER [TICKER ...]`
  __main__.py      # CLI entry point
  exceptions.py    # StockFetchError
tests/
  test_fetcher.py
  test_cli.py
```

## Next steps (once the real brief/worksheet contract is available)

1. Reconcile the field names/shape in `fetcher.py` against what
   `StockAnalyzer.jsx` actually expects.
2. Confirm the data provider (`yfinance` vs. a paid/rate-limited API) meets
   the brief's latency/accuracy/rate-limit requirements.
3. Decide how Phase 2 wires this into the worksheet (HTTP endpoint,
   subprocess call, scheduled cache refresh, etc.).
