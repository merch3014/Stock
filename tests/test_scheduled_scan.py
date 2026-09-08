from __future__ import annotations

from unittest.mock import MagicMock, patch

import stock_analyzer.scheduled_scan as ss_mod
from stock_analyzer.scheduled_scan import main


def _sample_scan(tickers=("AAPL",)):
    return {
        "results": [
            {
                "ticker": t,
                "price": 150.0,
                "catalyst": "Great quarter",
                "warnings": [],
                "score": {"composite": 70.0, "verdict": "Bullish", "stockAction": "Add / Initiate"},
            }
            for t in tickers
        ],
        "warnings": [],
    }


# -- _resolve_tickers ---------------------------------------------------

def test_resolve_tickers_combines_positional_and_explicit_watchlist(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "unused.txt")
    watchlist = tmp_path / "wl.txt"
    watchlist.write_text("MSFT\nNVDA\n")

    args = ss_mod.build_parser().parse_args(["AAPL", "--watchlist", str(watchlist)])
    assert ss_mod._resolve_tickers(args) == ["AAPL", "MSFT", "NVDA"]


def test_resolve_tickers_falls_back_to_default_watchlist_path(tmp_path, monkeypatch):
    default_watchlist = tmp_path / "watchlist.txt"
    default_watchlist.write_text("AAPL\nMSFT\n")
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", default_watchlist)

    args = ss_mod.build_parser().parse_args([])
    assert ss_mod._resolve_tickers(args) == ["AAPL", "MSFT"]


def test_resolve_tickers_combines_positional_with_default_watchlist(tmp_path, monkeypatch):
    default_watchlist = tmp_path / "watchlist.txt"
    default_watchlist.write_text("MSFT\n")
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", default_watchlist)

    args = ss_mod.build_parser().parse_args(["AAPL"])
    assert ss_mod._resolve_tickers(args) == ["AAPL", "MSFT"]


def test_resolve_tickers_falls_back_to_default_basket_when_nothing_available(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")

    args = ss_mod.build_parser().parse_args([])
    assert ss_mod._resolve_tickers(args) == list(ss_mod.DEFAULT_BASKET)


# -- main() ---------------------------------------------------------------

@patch("stock_analyzer.scheduled_scan.scan_watchlist")
def test_main_prints_digest_by_default(mock_scan, capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")
    mock_scan.return_value = _sample_scan()

    exit_code = main(["AAPL"])

    out = capsys.readouterr().out
    assert exit_code == 0
    assert "AAPL" in out
    assert "Bullish" in out


@patch("stock_analyzer.scheduled_scan.email_notifier_from_env")
@patch("stock_analyzer.scheduled_scan.scan_watchlist")
def test_main_email_mode_sends_via_notifier(mock_scan, mock_env_notifier, tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")
    mock_scan.return_value = _sample_scan()
    fake_notifier = MagicMock()
    mock_env_notifier.return_value = fake_notifier

    exit_code = main(["AAPL", "--email"])

    assert exit_code == 0
    fake_notifier.assert_called_once()
    subject, body = fake_notifier.call_args[0]
    assert "Stock watchlist scan" in subject
    assert "AAPL" in body


@patch("stock_analyzer.scheduled_scan.email_notifier_from_env")
@patch("stock_analyzer.scheduled_scan.scan_watchlist")
def test_main_email_mode_falls_back_to_printing_when_smtp_not_configured(
    mock_scan, mock_env_notifier, capsys, tmp_path, monkeypatch
):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")
    mock_scan.return_value = _sample_scan()
    mock_env_notifier.return_value = None

    exit_code = main(["AAPL", "--email"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "SMTP" in captured.err


@patch("stock_analyzer.scheduled_scan.email_notifier_from_env")
@patch("stock_analyzer.scheduled_scan.scan_watchlist")
def test_main_email_mode_handles_send_failure(mock_scan, mock_env_notifier, capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")
    mock_scan.return_value = _sample_scan()
    failing_notifier = MagicMock(side_effect=RuntimeError("smtp down"))
    mock_env_notifier.return_value = failing_notifier

    exit_code = main(["AAPL", "--email"])

    err = capsys.readouterr().err
    assert exit_code == 1
    assert "smtp down" in err


def test_main_errors_on_missing_explicit_watchlist_file(tmp_path, monkeypatch):
    monkeypatch.setattr(ss_mod, "DEFAULT_WATCHLIST_PATH", tmp_path / "does-not-exist.txt")

    exit_code = main(["--watchlist", str(tmp_path / "also-missing.txt")])

    assert exit_code == 1
