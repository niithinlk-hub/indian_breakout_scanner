from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.universe import build_stock_universe


class DummyDataService:
    def __init__(self, instruments: pd.DataFrame) -> None:
        self._instruments = instruments

    def get_instruments(self) -> pd.DataFrame:
        return self._instruments.copy()


def test_build_watchlist_universe_respects_limit(tmp_path: Path) -> None:
    watchlist_path = tmp_path / "watchlist.txt"
    watchlist_path.write_text("RELIANCE\nTCS\nINFY\n", encoding="utf-8")

    universe = build_stock_universe(
        data_service=DummyDataService(pd.DataFrame()),
        mode="watchlist",
        default_exchange="NSE",
        watchlist_path=watchlist_path,
        symbol_limit=2,
    )

    assert universe.symbols == ["RELIANCE", "TCS"]


def test_build_nse_equities_universe_filters_derivatives_and_duplicates() -> None:
    instruments = pd.DataFrame(
        [
            {"exchange": "NSE", "trading_symbol": "RELIANCE", "name": "Reliance Industries", "instrument_type": "EQ"},
            {"exchange": "NSE", "trading_symbol": "RELIANCE", "name": "Reliance FUT", "instrument_type": "FUT", "expiry": "2026-05-28"},
            {"exchange": "NSE", "trading_symbol": "NIFTYBEES", "name": "Nifty Bees ETF", "instrument_type": "EQ"},
            {"exchange": "BSE", "trading_symbol": "SBIN", "name": "State Bank of India", "instrument_type": "EQ"},
            {"exchange": "NSE", "trading_symbol": "TCS", "name": "Tata Consultancy Services", "instrument_type": "EQ"},
        ],
    )

    universe = build_stock_universe(
        data_service=DummyDataService(instruments),
        mode="nse_equities",
        default_exchange="NSE",
        symbol_limit=None,
    )

    assert universe.symbols == ["RELIANCE", "TCS"]
    assert universe.metadata["RELIANCE"]["display_name"] == "Reliance Industries"
