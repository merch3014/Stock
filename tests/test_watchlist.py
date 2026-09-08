from __future__ import annotations

import pytest

from stock_analyzer.exceptions import StockAnalysisError
from stock_analyzer.watchlist import load_watchlist, scan_watchlist


def test_load_watchlist_parses_comments_blanks_case_and_dedup(tmp_path):
    path = tmp_path / "watchlist.txt"
    path.write_text(
        "\n".join(
            [
                "# Personal research watchlist",
                "aapl",
                "",
                "  MSFT  # mega-cap tech",
                "# NVDA is commented out entirely",
                "AAPL",  # duplicate, different case already seen
                "goog",
            ]
        )
    )

    assert load_watchlist(path) == ["AAPL", "MSFT", "GOOG"]


def test_load_watchlist_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        load_watchlist(tmp_path / "does-not-exist.txt")


def _fake_result(ticker: str, composite: float) -> dict:
    return {"ticker": ticker, "score": {"composite": composite}}


def test_scan_watchlist_sorts_by_composite_descending():
    def fake_analyzer(ticker, **kwargs):
        return _fake_result(ticker, {"AAPL": 40.0, "MSFT": 90.0, "NVDA": 65.0}[ticker])

    result = scan_watchlist(["AAPL", "MSFT", "NVDA"], analyzer=fake_analyzer)

    assert [r["ticker"] for r in result["results"]] == ["MSFT", "NVDA", "AAPL"]
    assert result["warnings"] == []


def test_scan_watchlist_skips_failures_with_a_warning():
    def fake_analyzer(ticker, **kwargs):
        if ticker == "BAD":
            raise StockAnalysisError("No price data found for 'BAD'.")
        return _fake_result(ticker, 50.0)

    result = scan_watchlist(["AAPL", "BAD", "MSFT"], analyzer=fake_analyzer)

    assert [r["ticker"] for r in result["results"]] == ["AAPL", "MSFT"]
    assert len(result["warnings"]) == 1
    assert "BAD" in result["warnings"][0]


def test_scan_watchlist_passes_through_extra_kwargs():
    seen_kwargs = {}

    def fake_analyzer(ticker, **kwargs):
        seen_kwargs.update(kwargs)
        return _fake_result(ticker, 50.0)

    scan_watchlist(["AAPL"], analyzer=fake_analyzer, anthropic_api_key="fake-key")

    assert seen_kwargs == {"anthropic_api_key": "fake-key"}
