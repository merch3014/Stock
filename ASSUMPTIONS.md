# Assumptions for Phase 1

This task asked me to read `PROJECT_BRIEF.md` and `StockAnalyzer.jsx` before
scaffolding Phase 1. Neither file exists: the `merch3014/Stock` repository
(both on GitHub and in this checkout) had zero commits and zero files at the
start of this task — it was a brand-new, empty repo.

Since there was nothing to read, this scaffold was built on reasonable
defaults instead of an actual brief/worksheet contract:

- **Data source**: [`yfinance`](https://pypi.org/project/yfinance/) — free,
  no API key required, widely used for live/near-live quote + fundamentals
  data. Swap this out in `src/stock_fetcher/fetcher.py` if the real brief
  specifies a different provider (Alpha Vantage, IEX, Polygon, etc.).
- **Output shape**: a flat JSON-serializable dict using `camelCase` keys
  (see `README.md`), since the consumer is presumably a `.jsx` React
  component ("StockAnalyzer") that would naturally expect camelCase fields.
  Field names (`price`, `changePercent`, `marketCap`, `peRatio`, ...) are a
  best guess at a common "stock worksheet" shape — adjust
  `stock_fetcher/fetcher.py::fetch_stock_data` and the matching test
  fixtures once the actual `StockAnalyzer.jsx` is available, so the shape
  matches exactly what the component destructures.
- **Interface**: both a Python function (`fetch_stock_data(ticker)`) and a
  CLI (`python -m stock_fetcher AAPL`) that prints JSON to stdout, so it can
  be wired into a Node/Electron worksheet process, a REST endpoint, or a
  scheduled job without knowing yet which of those Phase 2 will pick.

**Next step**: once `PROJECT_BRIEF.md` and `StockAnalyzer.jsx` are pushed to
the repo, re-run this scaffolding pass (or hand me the files directly) so
the field names and behavior can be reconciled against the real spec.
