"""Command-line entry point: `python -m stock_analyzer TICKER [TICKER ...]`.

Two output modes:
- default: a short human-readable report per ticker (Phase 4 preview)
- --json: raw `analyze(ticker)` output, one JSON object (or array for
  multiple tickers), for piping into another process
"""

from __future__ import annotations

import argparse
import json
import sys

from .analyzer import analyze
from .exceptions import StockAnalysisError

_REPORT_FIELDS = [
    ("price", "Price"),
    ("ma50", "SMA 50"),
    ("ma200", "SMA 200"),
    ("ema9", "EMA 9"),
    ("vwap", "VWAP"),
    ("rsi", "RSI (14)"),
    ("bbLower", "BB lower"),
    ("bbMid", "BB mid"),
    ("bbUpper", "BB upper"),
    ("ivRank", "IV rank"),
    ("ivPercentile", "IV percentile"),
    ("expectedMove", "Expected move %"),
    ("peRatio", "P/E ratio"),
    ("peVsSector", "P/E vs sector %"),
    ("week52High", "52-week high"),
    ("week52Low", "52-week low"),
    ("sentiment", "Sentiment (-2..2)"),
    ("catalyst", "Catalyst"),
]


def _format_report(data: dict) -> str:
    lines = [f"=== {data['ticker']} ===", f"Fetched: {data['fetchedAt']}", ""]
    for key, label in _REPORT_FIELDS:
        lines.append(f"{label:<20} {data.get(key)}")
    if data.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in data["warnings"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_analyzer",
        description="Fetch live technicals/options/fundamentals/sentiment for one or more tickers.",
    )
    parser.add_argument(
        "tickers",
        nargs="+",
        metavar="TICKER",
        help="One or more stock ticker symbols, e.g. AAPL MSFT GOOG",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw analyze() JSON instead of a formatted report.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent level when --json is used (default: 2; 0 for compact).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    results = []
    exit_code = 0
    for ticker in args.tickers:
        try:
            results.append(analyze(ticker))
        except StockAnalysisError as exc:
            print(f"error: {exc}", file=sys.stderr)
            exit_code = 1

    if args.json:
        indent = args.indent or None
        if len(args.tickers) == 1 and results:
            print(json.dumps(results[0], indent=indent))
        else:
            print(json.dumps(results, indent=indent))
    else:
        for data in results:
            print(_format_report(data))
            print()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
