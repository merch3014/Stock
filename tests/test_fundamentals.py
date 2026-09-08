from __future__ import annotations

from stock_analyzer.fundamentals import compute_fundamentals


def test_compute_fundamentals_happy_path():
    info = {"trailingPE": 30.0, "fiftyTwoWeekHigh": 200.0, "fiftyTwoWeekLow": 100.0, "sector": "Technology"}
    fast_info = {}

    result = compute_fundamentals(info, fast_info, fetch_etf_pe=lambda symbol: 25.0)

    assert result["peRatio"] == 30.0
    assert result["sectorAvgPE"] == 25.0
    assert result["peVsSector"] == 20.0  # (30-25)/25*100
    assert result["week52High"] == 200.0
    assert result["week52Low"] == 100.0
    assert result["warnings"] == []


def test_compute_fundamentals_falls_back_to_forward_pe():
    info = {"forwardPE": 40.0, "sector": "Energy"}
    result = compute_fundamentals(info, {}, fetch_etf_pe=lambda symbol: 15.0)
    assert result["peRatio"] == 40.0
    assert any("forwardPE" in w for w in result["warnings"])


def test_compute_fundamentals_defaults_pe_to_zero_when_missing():
    result = compute_fundamentals({}, {}, fetch_etf_pe=lambda symbol: None)
    assert result["peRatio"] == 0.0
    assert result["peVsSector"] == 0.0


def test_compute_fundamentals_unknown_sector_defaults_pe_vs_sector():
    info = {"trailingPE": 20.0, "sector": "Some Unmapped Sector"}
    result = compute_fundamentals(info, {}, fetch_etf_pe=lambda symbol: 99.0)
    assert result["sectorAvgPE"] is None
    assert result["peVsSector"] == 0.0
    assert any("unmapped" in w.lower() or "no sector etf mapping" in w.lower() for w in result["warnings"])


def test_compute_fundamentals_handles_etf_fetch_error():
    info = {"trailingPE": 20.0, "sector": "Technology"}

    def boom(symbol):
        raise RuntimeError("network down")

    result = compute_fundamentals(info, {}, fetch_etf_pe=boom)
    assert result["sectorAvgPE"] is None
    assert result["peVsSector"] == 0.0
    assert any("network down" in w for w in result["warnings"])


def test_compute_fundamentals_prefers_fast_info_range():
    info = {"trailingPE": 10.0, "fiftyTwoWeekHigh": 50.0, "fiftyTwoWeekLow": 10.0, "sector": "Technology"}
    fast_info = {"yearHigh": 55.0, "yearLow": 12.0}
    result = compute_fundamentals(info, fast_info, fetch_etf_pe=lambda s: 10.0)
    assert result["week52High"] == 55.0
    assert result["week52Low"] == 12.0
