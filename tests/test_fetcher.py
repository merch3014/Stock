"""Tests for stock_fetcher.fetcher, with yfinance mocked out.

No network access is used in these tests: yf.Ticker is monkeypatched so
the tests are fast and deterministic.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stock_fetcher import StockFetchError, fetch_stock_data


def _make_fake_ticker(fast_info: dict, info: dict) -> MagicMock:
    fake = MagicMock()
    fake.fast_info = fast_info
    fake.info = info
    return fake


@patch("stock_fetcher.fetcher.yf.Ticker")
def test_fetch_stock_data_happy_path(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_fake_ticker(
        fast_info={
            "lastPrice": 227.52,
            "previousClose": 225.91,
            "open": 226.10,
            "dayHigh": 228.05,
            "dayLow": 225.80,
            "lastVolume": 41234567,
            "marketCap": 3456789012345,
            "currency": "USD",
            "yearHigh": 237.23,
            "yearLow": 164.08,
        },
        info={
            "longName": "Apple Inc.",
            "trailingPE": 34.12,
            "trailingEps": 6.67,
            "dividendYield": 0.0044,
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "averageVolume": 52345678,
        },
    )

    data = fetch_stock_data("aapl")

    assert data["ticker"] == "AAPL"
    assert data["companyName"] == "Apple Inc."
    assert data["price"] == 227.52
    assert data["previousClose"] == 225.91
    assert data["change"] == pytest.approx(1.61, abs=0.01)
    assert data["changePercent"] == pytest.approx(0.71, abs=0.01)
    assert data["volume"] == 41234567
    assert data["marketCap"] == 3456789012345
    assert data["peRatio"] == 34.12
    assert data["sector"] == "Technology"
    assert data["industry"] == "Consumer Electronics"
    assert data["fiftyTwoWeekHigh"] == 237.23
    assert data["fiftyTwoWeekLow"] == 164.08
    assert "fetchedAt" in data


@patch("stock_fetcher.fetcher.yf.Ticker")
def test_fetch_stock_data_falls_back_to_info_when_fast_info_missing_price(
    mock_ticker_cls,
):
    mock_ticker_cls.return_value = _make_fake_ticker(
        fast_info={},
        info={"currentPrice": 100.0, "regularMarketPreviousClose": 90.0},
    )

    data = fetch_stock_data("XYZ")

    assert data["price"] == 100.0
    assert data["previousClose"] == 90.0
    assert data["change"] == 10.0


@patch("stock_fetcher.fetcher.yf.Ticker")
def test_fetch_stock_data_raises_when_no_price_found(mock_ticker_cls):
    mock_ticker_cls.return_value = _make_fake_ticker(fast_info={}, info={})

    with pytest.raises(StockFetchError, match="No price data found"):
        fetch_stock_data("BADTICKER")


def test_fetch_stock_data_rejects_empty_ticker():
    with pytest.raises(StockFetchError, match="non-empty string"):
        fetch_stock_data("   ")


@patch("stock_fetcher.fetcher.yf.Ticker")
def test_fetch_stock_data_wraps_network_errors(mock_ticker_cls):
    mock_ticker_cls.side_effect = RuntimeError("boom")

    with pytest.raises(StockFetchError, match="Failed to fetch data"):
        fetch_stock_data("AAPL")
