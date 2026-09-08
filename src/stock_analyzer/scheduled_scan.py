"""CLI: `python scheduled_scan.py [TICKER ...] [--watchlist FILE] [--email]`.

This is the Phase 4 scheduled half PROJECT_BRIEF.md describes: "scheduled
daily scan of a watchlist (cron + email/notification)." It scans a
watchlist and prints — or, with --email, sends — a digest. That's the whole
job of this script; **it does not install, create, or manage any cron job,
systemd timer, or launchd agent itself.** Wiring an actual schedule is a
manual step you take on your own machine, deliberately: see README.md's
"Scheduling it yourself" section for a crontab line to add once you've:

  1. run `python backtest.py` for real (this dev sandbox can't — no network
     access to Yahoo Finance) and looked at whether Bullish periods actually
     outperformed Bearish ones, and
  2. decided, per the brief's own words, that the output is "something
     you'd actually trust reading every day."

Until then, run this by hand whenever you want a watchlist snapshot — it's
just `scan_watchlist()` plus a digest, nothing time-based about it on its
own.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from .backtest import DEFAULT_BASKET
from .notify import email_notifier_from_env
from .reporting import format_digest
from .watchlist import load_watchlist, scan_watchlist

# repo root: src/stock_analyzer/scheduled_scan.py -> src/stock_analyzer -> src -> repo root
DEFAULT_WATCHLIST_PATH = Path(__file__).resolve().parent.parent.parent / "watchlist.txt"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scheduled_scan",
        description=(
            "Scan a watchlist and print (or email) a digest. Meant to be run by cron/a task "
            "scheduler once you trust the output — this script does not schedule itself."
        ),
    )
    parser.add_argument(
        "tickers",
        nargs="*",
        metavar="TICKER",
        help="Extra tickers, combined with --watchlist / its default.",
    )
    parser.add_argument(
        "--watchlist",
        metavar="FILE",
        help=f"Watchlist file (default: {DEFAULT_WATCHLIST_PATH.name} in the repo root, if present).",
    )
    parser.add_argument(
        "--email",
        action="store_true",
        help="Send the digest via SMTP (see stock_analyzer.notify for the SMTP_* env vars) "
        "instead of only printing it.",
    )
    return parser


def _resolve_tickers(args: argparse.Namespace) -> list[str]:
    """Positional tickers + a watchlist file, combined and de-duplicated.
    Falls back to DEFAULT_BASKET if neither yields anything, so a
    misconfigured cron entry degrades to *something* useful rather than
    silently scanning zero tickers.
    """
    tickers = list(args.tickers)
    watchlist_path = args.watchlist or (DEFAULT_WATCHLIST_PATH if DEFAULT_WATCHLIST_PATH.exists() else None)
    if watchlist_path:
        tickers = list(dict.fromkeys(tickers + load_watchlist(watchlist_path)))
    return tickers or list(DEFAULT_BASKET)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        tickers = _resolve_tickers(args)
    except OSError as exc:
        print(f"error: could not read watchlist: {exc}", file=sys.stderr)
        return 1

    scan = scan_watchlist(tickers)
    digest = format_digest(scan)

    if not args.email:
        print(digest)
        return 0

    notifier = email_notifier_from_env()
    if notifier is None:
        print(
            "error: --email given but SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD/SMTP_FROM/"
            "SMTP_TO aren't all set (see stock_analyzer.notify). Printing the digest instead:\n",
            file=sys.stderr,
        )
        print(digest)
        return 1

    try:
        notifier(f"Stock watchlist scan — {date.today().isoformat()}", digest)
    except Exception as exc:
        print(f"error: failed to send email ({exc}). Digest below:\n", file=sys.stderr)
        print(digest)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
