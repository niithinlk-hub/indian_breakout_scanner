from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.data_ingestion import MarketDataService

_DERIVATIVE_TYPES = {"CE", "PE", "FUT", "FUTSTK", "FUTIDX", "OPTSTK", "OPTIDX"}
_EXCLUDED_NAME_PATTERNS = ("ETF", "BEES", "INDEX", "GOLD", "SILVER")
_CASH_EQUITY_TYPES = {"EQ", "BE", "BZ", "SM", "ST"}


@dataclass(slots=True)
class UniverseResult:
    """Universe selection output."""

    symbols: list[str]
    metadata: dict[str, dict[str, str]]


def load_watchlist(path: Path) -> list[str]:
    """Load a manual symbol watchlist from disk."""

    if not path.exists():
        return []
    return [line.strip().upper() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def build_stock_universe(
    *,
    data_service: MarketDataService,
    mode: str,
    default_exchange: str,
    watchlist_path: Path | None = None,
    symbol_limit: int | None = None,
) -> UniverseResult:
    """Build the requested stock universe and attach lightweight metadata."""

    universe_mode = mode.strip().lower()
    if universe_mode == "watchlist":
        symbols = load_watchlist(watchlist_path or Path("config/watchlist.example.txt"))
        limited = symbols[:symbol_limit] if symbol_limit else symbols
        return UniverseResult(symbols=limited, metadata={symbol: {} for symbol in limited})

    if universe_mode != "nse_equities":
        raise ValueError(f"Unsupported universe mode '{mode}'.")

    instruments = data_service.get_instruments()
    if instruments.empty:
        return UniverseResult(symbols=[], metadata={})

    exchange = default_exchange.upper()
    filtered = instruments.copy()
    if "exchange" in filtered.columns:
        filtered = filtered.loc[filtered["exchange"].astype(str).str.upper().eq(exchange)]
    if "instrument_type" in filtered.columns:
        filtered = filtered.loc[~filtered["instrument_type"].fillna("").astype(str).str.upper().isin(_DERIVATIVE_TYPES)]
        instrument_types = filtered["instrument_type"].fillna("").astype(str).str.upper()
        filtered = filtered.loc[instrument_types.isin(_CASH_EQUITY_TYPES) | instrument_types.eq("")]
    if "trading_symbol" in filtered.columns:
        filtered = filtered.loc[filtered["trading_symbol"].fillna("").astype(str).str.len() > 0]
        filtered = filtered.loc[
            filtered["trading_symbol"].fillna("").astype(str).str.upper().str.fullmatch(r"[A-Z0-9]+")
        ]
    if "name" in filtered.columns:
        names = filtered["name"].fillna("").astype(str).str.upper()
        for pattern in _EXCLUDED_NAME_PATTERNS:
            filtered = filtered.loc[~names.str.contains(pattern, regex=False)]
            names = filtered["name"].fillna("").astype(str).str.upper()
    if "expiry" in filtered.columns:
        filtered = filtered.loc[filtered["expiry"].isna()]

    filtered = filtered.drop_duplicates(subset=["trading_symbol"]).sort_values("trading_symbol").reset_index(drop=True)
    if symbol_limit:
        filtered = filtered.head(symbol_limit)

    metadata: dict[str, dict[str, str]] = {}
    for _, row in filtered.iterrows():
        symbol = str(row.get("trading_symbol", "")).upper()
        if not symbol:
            continue
        metadata[symbol] = {
            "sector": str(row.get("sector", "Unknown") or "Unknown"),
            "market_cap_bucket": str(row.get("market_cap_bucket", "Unknown") or "Unknown"),
            "display_name": str(row.get("name", symbol) or symbol),
        }

    return UniverseResult(symbols=list(metadata.keys()), metadata=metadata)
