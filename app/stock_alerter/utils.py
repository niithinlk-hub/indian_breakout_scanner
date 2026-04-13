from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def normalize_nse_symbol(symbol: str) -> str:
    cleaned = str(symbol).strip().upper()
    if not cleaned:
        return ""
    if cleaned.startswith("^") or cleaned.endswith(".NS"):
        return cleaned
    return f"{cleaned}.NS"


def strip_exchange_suffix(symbol: str) -> str:
    cleaned = str(symbol).strip().upper()
    return cleaned[:-3] if cleaned.endswith(".NS") else cleaned


def parse_symbol_input(raw: str) -> list[str]:
    return [normalize_nse_symbol(item) for item in str(raw).replace("\n", ",").split(",") if str(item).strip()]


def ensure_ohlcv_schema(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume", "symbol"])
    frame = df.reset_index().rename(
        columns={
            "Date": "datetime",
            "Datetime": "datetime",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
        },
    )
    frame["datetime"] = pd.to_datetime(frame["datetime"], errors="coerce")
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["symbol"] = strip_exchange_suffix(symbol)
    return frame[["datetime", "open", "high", "low", "close", "volume", "symbol"]].dropna(
        subset=["datetime", "open", "high", "low", "close"],
    )


def percent_distance(current_price: float | None, level: float | None) -> float | None:
    if current_price is None or level in {None, 0}:
        return None
    return round(((current_price / level) - 1.0) * 100.0, 4)


def positive_slope(series: pd.Series, periods: int = 5) -> bool:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if len(cleaned) < periods + 1:
        return False
    return float(cleaned.iloc[-1]) > float(cleaned.iloc[-periods - 1])


def close_near_high(close: float, high: float, low: float, threshold: float = 0.25) -> bool:
    total_range = high - low
    if total_range <= 0:
        return False
    return ((high - close) / total_range) <= threshold


def body_to_range_ratio(open_: float, high: float, low: float, close: float) -> float:
    total_range = high - low
    if total_range <= 0:
        return 0.0
    return round(abs(close - open_) / total_range, 4)


def upper_wick_ratio(open_: float, high: float, close: float, low: float) -> float:
    total_range = high - low
    if total_range <= 0:
        return 1.0
    body_top = max(open_, close)
    return round((high - body_top) / total_range, 4)


def rolling_pivots(df: pd.DataFrame, left: int = 3, right: int = 3) -> pd.DataFrame:
    frame = df.copy().sort_values("datetime").reset_index(drop=True)
    frame["pivot_high"] = pd.NA
    frame["pivot_low"] = pd.NA
    for idx in range(left, len(frame) - right):
        window = frame.iloc[idx - left : idx + right + 1]
        high = float(frame.at[idx, "high"])
        low = float(frame.at[idx, "low"])
        if high >= float(window["high"].max()):
            frame.at[idx, "pivot_high"] = high
        if low <= float(window["low"].min()):
            frame.at[idx, "pivot_low"] = low
    return frame


def safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return float(np.mean(values))


def compact_dict(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}
