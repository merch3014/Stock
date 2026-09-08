"""Fundamentals: P/E ratio, 52-week high/low, P/E vs. sector average.

yfinance doesn't expose a "sector average P/E" field directly, so this
approximates it using the trailing P/E of a representative sector ETF (a
common, free proxy). Swap SECTOR_ETF_MAP or this whole approach out if a
real sector-average data source becomes available.
"""

from __future__ import annotations

from typing import Any, Callable

SECTOR_ETF_MAP: dict[str, str] = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financial Services": "XLF",
    "Financial": "XLF",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Basic Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}


def compute_fundamentals(
    info: dict[str, Any],
    fast_info: dict[str, Any],
    fetch_etf_pe: Callable[[str], float | None],
) -> dict:
    """Derive P/E, 52-week range, and P/E-vs-sector from `info`/`fast_info`.

    `fetch_etf_pe(etf_symbol)` is injected so tests can stub out the extra
    network call for the sector ETF's trailing P/E.
    """
    warnings: list[str] = []

    pe_ratio = info.get("trailingPE")
    if pe_ratio is None:
        pe_ratio = info.get("forwardPE")
        if pe_ratio is not None:
            warnings.append("trailingPE unavailable; used forwardPE instead.")
    if pe_ratio is None:
        warnings.append("No P/E ratio available (e.g. unprofitable company); defaulted to 0.")
        pe_ratio = 0.0

    week52_high = fast_info.get("yearHigh") or info.get("fiftyTwoWeekHigh")
    week52_low = fast_info.get("yearLow") or info.get("fiftyTwoWeekLow")
    if week52_high is None or week52_low is None:
        warnings.append("52-week high/low unavailable.")

    sector = info.get("sector")
    sector_avg_pe = None
    if sector in SECTOR_ETF_MAP:
        try:
            sector_avg_pe = fetch_etf_pe(SECTOR_ETF_MAP[sector])
        except Exception as exc:
            warnings.append(f"Could not fetch sector-average P/E for '{sector}': {exc}")
    else:
        warnings.append(f"No sector ETF mapping for sector '{sector}'; peVsSector defaulted to 0.")

    if sector_avg_pe:
        pe_vs_sector = (pe_ratio - sector_avg_pe) / sector_avg_pe * 100
    else:
        pe_vs_sector = 0.0

    return {
        "peRatio": round(pe_ratio, 2),
        "peVsSector": round(pe_vs_sector, 2),
        "sectorAvgPE": round(sector_avg_pe, 2) if sector_avg_pe else None,
        "week52High": round(week52_high, 2) if week52_high is not None else None,
        "week52Low": round(week52_low, 2) if week52_low is not None else None,
        "warnings": warnings,
    }
