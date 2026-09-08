"""Tests for stock_fetcher.cli."""

from __future__ import annotations

import json
from unittest.mock import patch

from stock_fetcher.cli import main
from stock_fetcher.exceptions import StockFetchError


@patch("stock_fetcher.cli.fetch_stock_data")
def test_main_single_ticker_prints_json_object(mock_fetch, capsys):
    mock_fetch.return_value = {"ticker": "AAPL", "price": 227.52}

    exit_code = main(["AAPL"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {"ticker": "AAPL", "price": 227.52}


@patch("stock_fetcher.cli.fetch_stock_data")
def test_main_multiple_tickers_prints_json_array(mock_fetch, capsys):
    mock_fetch.side_effect = [
        {"ticker": "AAPL", "price": 227.52},
        {"ticker": "MSFT", "price": 420.0},
    ]

    exit_code = main(["AAPL", "MSFT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    parsed = json.loads(captured.out)
    assert parsed == [
        {"ticker": "AAPL", "price": 227.52},
        {"ticker": "MSFT", "price": 420.0},
    ]


@patch("stock_fetcher.cli.fetch_stock_data")
def test_main_reports_error_and_nonzero_exit_for_bad_ticker(mock_fetch, capsys):
    mock_fetch.side_effect = StockFetchError("No price data found for 'BAD'.")

    exit_code = main(["BAD"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "No price data found" in captured.err
