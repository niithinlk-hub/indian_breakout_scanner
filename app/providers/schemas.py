from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

OHLCV_SCHEMA = ["datetime", "open", "high", "low", "close", "volume", "symbol"]


def empty_ohlcv_frame() -> pd.DataFrame:
    """Return an empty OHLCV frame in the canonical schema."""

    return pd.DataFrame(columns=OHLCV_SCHEMA)


def normalize_ohlcv_frame(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """Normalize raw provider output into the canonical OHLCV schema."""

    if df.empty:
        return empty_ohlcv_frame()

    normalized = df.copy()
    normalized.columns = [str(column).strip().lower() for column in normalized.columns]

    rename_map = {
        "timestamp": "datetime",
        "date": "datetime",
        "time": "datetime",
        "tradingsymbol": "symbol",
    }
    normalized = normalized.rename(columns=rename_map)

    missing_columns = [column for column in OHLCV_SCHEMA if column not in normalized.columns]
    if missing_columns:
        raise ValueError(f"Missing OHLCV columns: {missing_columns}")

    normalized["symbol"] = normalized["symbol"].fillna(symbol).astype(str)
    normalized["datetime"] = pd.to_datetime(normalized["datetime"], errors="coerce")
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    normalized = normalized.dropna(subset=["datetime", "open", "high", "low", "close", "volume"])
    normalized = normalized[OHLCV_SCHEMA].sort_values("datetime").reset_index(drop=True)
    return normalized


def ensure_quote_symbols(symbols: Iterable[str]) -> list[str]:
    """Normalize a quote request symbol list."""

    return [symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()]
