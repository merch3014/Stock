"""Command-line entry point: `python backtest.py [TICKER ...]` (Phase 3).

Backtests the composite score's verdict buckets against actual forward
returns over a basket of tickers, and reports whether Bullish-flagged
periods actually outperformed Bearish-flagged ones.
"""

from __future__ import annotations

import argparse
import json
import sys

from .backtest import DEFAULT_BASKET, HOLDING_WINDOWS, run_backtest
from .exceptions import StockAnalysisError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stock_analyzer.backtest",
        description=(
            "Backtest the composite score's verdict buckets against what actually "
            "happened next, per PROJECT_BRIEF.md's Phase 3."
        ),
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        metavar="TICKER",
        help=f"Tickers to backtest (default: a {len(DEFAULT_BASKET)}-ticker basket; see backtest.DEFAULT_BASKET).",
    )
    parser.add_argument(
        "--period",
        default="2y",
        help="yfinance history period to pull per ticker (default: 2y).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the summary + edge as JSON instead of a formatted report.",
    )
    return parser


def _fmt_pct(x: float) -> str:
    return "  n/a " if x != x else f"{x * 100:+6.2f}%"  # x != x is a fast NaN check


def _format_report(result: dict) -> str:
    lines = ["=== Backtest: verdict vs. actual forward return ===", ""]

    header = f"{'Verdict':<16}{'N':>6}"
    for label in HOLDING_WINDOWS:
        header += f"{'mean ' + label:>12}{'win% ' + label:>10}"
    lines.append(header)

    for _, row in result["summary"].iterrows():
        line = f"{row['verdict']:<16}{row['n']:>6}"
        for label in HOLDING_WINDOWS:
            line += f"{_fmt_pct(row[f'mean_{label}']):>12}{_fmt_pct(row[f'win_rate_{label}']):>10}"
        lines.append(line)

    lines.append("")
    lines.append("Bullish (+Mildly Bullish) vs. Bearish (+Mildly Bearish), forward return:")
    for label, stats in result["edge"].items():
        verdict_line = (
            f"  {label}: bullish {_fmt_pct(stats['bullish_mean'])} (n={stats['bullish_n']}) vs. "
            f"bearish {_fmt_pct(stats['bearish_mean'])} (n={stats['bearish_n']})  "
            f"-> edge {_fmt_pct(stats['edge'])}"
        )
        lines.append(verdict_line)
        if stats["edge"] == stats["edge"]:  # not NaN
            verdict_word = "outperformed" if stats["edge"] > 0 else "did NOT outperform"
            lines.append(f"    Bullish periods {verdict_word} Bearish periods over {label}.")

    if result["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in result["warnings"])

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = run_backtest(args.tickers or None, period=args.period)
    except StockAnalysisError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        payload = {
            "summary": result["summary"].to_dict(orient="records"),
            "edge": result["edge"],
            "warnings": result["warnings"],
        }
        print(json.dumps(payload, indent=2, default=str))
    else:
        print(_format_report(result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
