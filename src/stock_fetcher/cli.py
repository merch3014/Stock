"""Command-line entry point: `python -m stock_fetcher TICKER [TICKER ...]`.

Prints one JSON object per ticker (or a JSON array for multiple tickers)
to stdout, so it's easy to pipe into another process (e.g. a Node
worksheet backend) or redirect to a file.
"""

from __future__ import annotations

import argparse
import json
import sys

from .exceptions import StockFetchError
from .fetcher import fetch_stock_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_fetcher",
        description="Fetch live stock data for one or more tickers.",
    )
    parser.add_argument(
        "tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more stock ticker symbols, e.g. AAPL MSFT GOOG",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent level for pretty-printing (default: 2). Use 0 for compact output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    indent = args.indent or None

    results = []
    exit_code = 0
    for ticker in args.tickers:
        try:
            results.append(fetch_stock_data(ticker))
        except StockFetchError as exc:
            print(f"error: {exc}", file=sys.stderr)
            exit_code = 1

    if len(args.tickers) == 1 and results:
        print(json.dumps(results[0], indent=indent))
    else:
        print(json.dumps(results, indent=indent))

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
