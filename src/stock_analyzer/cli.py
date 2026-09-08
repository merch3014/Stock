"""Command-line entry point: `python -m stock_analyzer TICKER [TICKER ...]`.

Output modes:
- default: a full human-readable report per ticker (Phase 4 preview),
  including the Phase 2 composite score
- --table: one compact row per ticker, sorted most-bullish-first — the
  on-demand "scan a watchlist" view (default when --watchlist is used)
- --json: raw analyze_and_score() output per ticker (a list, sorted the same
  way as --table when --watchlist is used), for piping into another process

Tickers can be given positionally, loaded from a --watchlist file, or both
(combined and de-duplicated). See stock_analyzer.watchlist for the file
format and for why this is on-demand only — no scheduling yet.
"""

from __future__ import annotations

import argparse
import json
import sys

from .exceptions import StockAnalysisError
from .watchlist import load_watchlist, scan_watchlist

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

    score = data.get("score")
    if score:
        lines.append("")
        lines.append(f"Composite: {round(score['composite'])} ({score['verdict']})")
        lines.append(f"Stock action:  {score['stockAction']}")
        lines.append(f"Options view:  {score['optionsView']}")
        lines.append(
            f"Price target:  ${score['targetLow']:.2f} - ${score['targetHigh']:.2f}  "
            f"(profit-take ${score['profitTake']:.2f}, stop ${score['stopLevel']:.2f})"
        )
        lines.append("Breakdown:")
        for row in score["breakdown"]:
            sign = "+" if row["value"] >= 0 else ""
            lines.append(f"  {row['label']:<28} {sign}{row['value']:.0f}")

    if data.get("warnings"):
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in data["warnings"])
    return "\n".join(lines)


def _format_table(results: list[dict]) -> str:
    header = f"{'Ticker':<8}{'Price':>10}{'Composite':>11}  {'Verdict':<16}{'Action':<18}Catalyst"
    lines = [header, "-" * len(header)]
    for data in results:
        score = data.get("score", {})
        catalyst = (data.get("catalyst") or "")[:40]
        lines.append(
            f"{data['ticker']:<8}{data['price']:>10.2f}{round(score.get('composite', 50)):>9}  "
            f"{score.get('verdict', ''):<16}{score.get('stockAction', ''):<18}{catalyst}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_analyzer",
        description="Fetch live technicals/options/fundamentals/sentiment for one or more tickers.",
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        metavar="TICKER",
        help="Stock ticker symbols, e.g. AAPL MSFT GOOG. Optional if --watchlist is given.",
    )
    parser.add_argument(
        "--watchlist",
        metavar="FILE",
        help="Load tickers from a file (one per line, '#' comments), combined with any given positionally.",
    )
    parser.add_argument(
        "--table",
        action="store_true",
        help="Compact one-row-per-ticker table instead of a full report each (default when --watchlist is used).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Force full per-ticker reports even when --watchlist is used.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw analyze_and_score() JSON instead of a formatted report.",
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

    tickers = list(args.tickers)
    if args.watchlist:
        try:
            watchlist_tickers = load_watchlist(args.watchlist)
        except OSError as exc:
            print(f"error: could not read watchlist '{args.watchlist}': {exc}", file=sys.stderr)
            return 1
        tickers = list(dict.fromkeys(tickers + watchlist_tickers))  # combine, dedupe, keep order

    if not tickers:
        parser.error("no tickers given: pass TICKER(s) and/or --watchlist FILE")

    scan = scan_watchlist(tickers)
    results, scan_warnings = scan["results"], scan["warnings"]
    for warning in scan_warnings:
        print(f"error: {warning}", file=sys.stderr)
    exit_code = 1 if scan_warnings else 0

    use_table = args.table or (bool(args.watchlist) and not args.full and not args.json)

    if args.json:
        indent = args.indent or None
        if len(tickers) == 1 and results:
            print(json.dumps(results[0], indent=indent))
        else:
            print(json.dumps(results, indent=indent))
    elif use_table:
        print(_format_table(results))
    else:
        for data in results:
            print(_format_report(data))
            print()

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
