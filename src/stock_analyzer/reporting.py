"""Text formatting shared by the interactive CLI (`cli.py`) and the
scheduled-scan digest (`scheduled_scan.py`) — one place for what a report
looks like, so the two don't drift.
"""

from __future__ import annotations

from datetime import datetime, timezone

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


def format_report(data: dict) -> str:
    """Full per-ticker report: every worksheet field plus the composite score."""
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


def format_table(results: list[dict]) -> str:
    """One compact row per ticker — the "scan a watchlist at a glance" view."""
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


def format_digest(scan: dict, *, title: str = "Stock watchlist scan") -> str:
    """A print/email-ready digest for a `scan_watchlist()` result: a header
    with a UTC timestamp, the compact table, and any per-ticker warnings.
    """
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [f"{title} — {timestamp}", ""]
    if scan["results"]:
        lines.append(format_table(scan["results"]))
    else:
        lines.append("No tickers produced usable results.")
    if scan["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        lines.extend(f"  - {w}" for w in scan["warnings"])
    return "\n".join(lines)
