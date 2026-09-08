from __future__ import annotations

from stock_analyzer.reporting import format_digest, format_report, format_table

_DATA = {
    "ticker": "AAPL",
    "price": 150.0,
    "fetchedAt": "2026-09-08T00:00:00+00:00",
    "catalyst": "Strong earnings",
    "warnings": [],
    "score": {
        "composite": 61.5,
        "verdict": "Mildly Bullish",
        "verdictTone": "up",
        "targetLow": 148.0,
        "targetHigh": 156.0,
        "profitTake": 153.0,
        "stopLevel": 146.0,
        "stockAction": "Hold / Small Add",
        "optionsView": "Buy calls or call debit spreads.",
        "breakdown": [{"label": "Trend (price vs MAs)", "value": 5.0}],
    },
}


def test_format_report_includes_key_fields():
    text = format_report(_DATA)
    assert "AAPL" in text
    assert "Mildly Bullish" in text
    assert "Hold / Small Add" in text
    assert "Strong earnings" in text


def test_format_table_is_one_line_per_ticker():
    text = format_table([_DATA, {**_DATA, "ticker": "MSFT"}])
    lines = [l for l in text.splitlines() if l.strip()]
    assert any(l.startswith("AAPL") for l in lines)
    assert any(l.startswith("MSFT") for l in lines)
    assert "SMA 50" not in text  # table view, not the full report


def test_format_digest_includes_timestamp_table_and_warnings():
    scan = {"results": [_DATA], "warnings": ["Could not analyze BAD: no price data"]}
    text = format_digest(scan)
    assert "Stock watchlist scan" in text
    assert "AAPL" in text
    assert "Warnings:" in text
    assert "BAD" in text


def test_format_digest_handles_empty_results():
    text = format_digest({"results": [], "warnings": []})
    assert "No tickers produced usable results." in text
