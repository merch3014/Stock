from __future__ import annotations

import json
from unittest.mock import patch

import pandas as pd

from stock_analyzer.backtest_cli import main
from stock_analyzer.exceptions import StockAnalysisError

_SUMMARY = pd.DataFrame(
    [
        {"verdict": "Bullish", "n": 40, "n_1w": 40, "mean_1w": 0.012, "median_1w": 0.010, "win_rate_1w": 0.65,
         "n_1m": 40, "mean_1m": 0.03, "median_1m": 0.028, "win_rate_1m": 0.70},
        {"verdict": "Mildly Bullish", "n": 0, "n_1w": 0, "mean_1w": float("nan"), "median_1w": float("nan"),
         "win_rate_1w": float("nan"), "n_1m": 0, "mean_1m": float("nan"), "median_1m": float("nan"),
         "win_rate_1m": float("nan")},
        {"verdict": "Neutral", "n": 0, "n_1w": 0, "mean_1w": float("nan"), "median_1w": float("nan"),
         "win_rate_1w": float("nan"), "n_1m": 0, "mean_1m": float("nan"), "median_1m": float("nan"),
         "win_rate_1m": float("nan")},
        {"verdict": "Mildly Bearish", "n": 0, "n_1w": 0, "mean_1w": float("nan"), "median_1w": float("nan"),
         "win_rate_1w": float("nan"), "n_1m": 0, "mean_1m": float("nan"), "median_1m": float("nan"),
         "win_rate_1m": float("nan")},
        {"verdict": "Bearish", "n": 35, "n_1w": 35, "mean_1w": -0.011, "median_1w": -0.009, "win_rate_1w": 0.20,
         "n_1m": 35, "mean_1m": -0.025, "median_1m": -0.022, "win_rate_1m": 0.15},
    ]
)

_RESULT = {
    "per_ticker": {"AAPL": pd.DataFrame()},
    "combined": pd.DataFrame(),
    "summary": _SUMMARY,
    "edge": {
        "1w": {"bullish_mean": 0.012, "bearish_mean": -0.011, "edge": 0.023, "bullish_n": 40, "bearish_n": 35},
        "1m": {"bullish_mean": 0.03, "bearish_mean": -0.025, "edge": 0.055, "bullish_n": 40, "bearish_n": 35},
    },
    "warnings": ["No price history for FAKE; skipped."],
}


@patch("stock_analyzer.backtest_cli.run_backtest")
def test_main_report_mode(mock_run, capsys):
    mock_run.return_value = _RESULT

    exit_code = main(["AAPL", "MSFT"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Bullish" in captured.out
    assert "outperformed Bearish" in captured.out
    assert "FAKE" in captured.out  # warnings surfaced


@patch("stock_analyzer.backtest_cli.run_backtest")
def test_main_json_mode(mock_run, capsys):
    mock_run.return_value = _RESULT

    exit_code = main(["--json"])

    captured = capsys.readouterr()
    assert exit_code == 0
    parsed = json.loads(captured.out)
    assert parsed["edge"]["1w"]["edge"] == 0.023
    assert len(parsed["summary"]) == 5


@patch("stock_analyzer.backtest_cli.run_backtest")
def test_main_reports_error_and_nonzero_exit(mock_run):
    mock_run.side_effect = StockAnalysisError("No tickers produced usable backtest data.")

    exit_code = main(["BAD"])

    assert exit_code == 1


@patch("stock_analyzer.backtest_cli.run_backtest")
def test_main_passes_period_and_tickers_through(mock_run, capsys):
    mock_run.return_value = _RESULT

    main(["AAPL", "MSFT", "--period", "1y"])

    args, kwargs = mock_run.call_args
    assert args[0] == ["AAPL", "MSFT"]
    assert kwargs["period"] == "1y"


@patch("stock_analyzer.backtest_cli.run_backtest")
def test_main_defaults_to_none_tickers_when_omitted(mock_run, capsys):
    mock_run.return_value = _RESULT

    main([])

    args, kwargs = mock_run.call_args
    assert args[0] is None
