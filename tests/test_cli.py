from __future__ import annotations

import json
from unittest.mock import patch

from stock_analyzer.cli import main
from stock_analyzer.exceptions import StockAnalysisError

_SAMPLE = {
    "ticker": "AAPL",
    "price": 150.0,
    "ma50": 145.0,
    "ma200": 140.0,
    "ema9": 149.0,
    "vwap": 150.5,
    "rsi": 60.0,
    "bbLower": 140.0,
    "bbMid": 150.0,
    "bbUpper": 160.0,
    "ivRank": 40.0,
    "ivPercentile": 45.0,
    "expectedMove": 6.0,
    "peRatio": 28.0,
    "peVsSector": 10.0,
    "week52High": 180.0,
    "week52Low": 120.0,
    "sentiment": 1,
    "catalyst": "Strong earnings",
    "fetchedAt": "2026-09-08T00:00:00+00:00",
    "warnings": [],
}


@patch("stock_analyzer.cli.analyze")
def test_main_json_single_ticker(mock_analyze, capsys):
    mock_analyze.return_value = _SAMPLE

    exit_code = main(["AAPL", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == _SAMPLE


@patch("stock_analyzer.cli.analyze")
def test_main_json_multiple_tickers_is_array(mock_analyze, capsys):
    mock_analyze.side_effect = [_SAMPLE, {**_SAMPLE, "ticker": "MSFT"}]

    exit_code = main(["AAPL", "MSFT", "--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    parsed = json.loads(captured.out)
    assert [item["ticker"] for item in parsed] == ["AAPL", "MSFT"]


@patch("stock_analyzer.cli.analyze")
def test_main_report_mode_prints_readable_output(mock_analyze, capsys):
    mock_analyze.return_value = _SAMPLE

    exit_code = main(["AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "AAPL" in captured.out
    assert "SMA 50" in captured.out
    assert "Strong earnings" in captured.out


@patch("stock_analyzer.cli.analyze")
def test_main_reports_error_and_nonzero_exit(mock_analyze, capsys):
    mock_analyze.side_effect = StockAnalysisError("No price data found for 'BAD'.")

    exit_code = main(["BAD"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No price data found" in captured.err
