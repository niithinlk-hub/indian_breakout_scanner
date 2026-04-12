from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_atr(df: pd.DataFrame, lookback: int = 14) -> pd.Series:
    """Calculate a simple ATR series."""

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    previous_close = history["close"].shift(1)
    true_range = pd.concat(
        [
            history["high"] - history["low"],
            (history["high"] - previous_close).abs(),
            (history["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(lookback, min_periods=lookback).mean()


def _mitigation_status(df: pd.DataFrame, index: int, direction: str, bottom: float, top: float) -> str:
    future = df.iloc[index + 1 :].copy()
    if future.empty:
        return "fresh"

    if direction == "bullish":
        future_lows = pd.to_numeric(future["low"], errors="coerce")
        if (future_lows <= bottom).any():
            return "fully filled"
        if (future_lows <= top).any():
            return "partially mitigated"
        return "fresh"

    future_highs = pd.to_numeric(future["high"], errors="coerce")
    if (future_highs >= top).any():
        return "fully filled"
    if (future_highs >= bottom).any():
        return "partially mitigated"
    return "fresh"


def detect_fvgs(
    df: pd.DataFrame,
    *,
    min_gap_size_pct: float = 0.2,
    use_atr_filter: bool = True,
    atr_gap_multiplier: float = 0.25,
) -> pd.DataFrame:
    """Detect three-candle bullish and bearish fair-value gaps."""

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    if len(history) < 3:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "direction",
                "top",
                "bottom",
                "midpoint",
                "size_points",
                "size_pct",
                "status",
            ],
        )

    atr = calculate_atr(history)
    rows: list[dict[str, Any]] = []
    for index in range(2, len(history)):
        candle1 = history.iloc[index - 2]
        candle3 = history.iloc[index]
        atr_value = float(atr.iloc[index]) if pd.notna(atr.iloc[index]) else None

        bullish_gap = float(candle3["low"]) - float(candle1["high"])
        if bullish_gap > 0:
            size_pct = (bullish_gap / float(candle1["high"])) * 100.0 if float(candle1["high"]) else 0.0
            if size_pct >= min_gap_size_pct and (not use_atr_filter or atr_value is None or bullish_gap >= atr_value * atr_gap_multiplier):
                bottom = float(candle1["high"])
                top = float(candle3["low"])
                rows.append(
                    {
                        "timestamp": candle3["datetime"],
                        "direction": "bullish",
                        "top": round(top, 4),
                        "bottom": round(bottom, 4),
                        "midpoint": round((top + bottom) / 2.0, 4),
                        "size_points": round(bullish_gap, 4),
                        "size_pct": round(size_pct, 4),
                        "status": _mitigation_status(history, index, "bullish", bottom, top),
                    },
                )

        bearish_gap = float(candle1["low"]) - float(candle3["high"])
        if bearish_gap > 0:
            size_pct = (bearish_gap / float(candle1["low"])) * 100.0 if float(candle1["low"]) else 0.0
            if size_pct >= min_gap_size_pct and (not use_atr_filter or atr_value is None or bearish_gap >= atr_value * atr_gap_multiplier):
                bottom = float(candle3["high"])
                top = float(candle1["low"])
                rows.append(
                    {
                        "timestamp": candle3["datetime"],
                        "direction": "bearish",
                        "top": round(top, 4),
                        "bottom": round(bottom, 4),
                        "midpoint": round((top + bottom) / 2.0, 4),
                        "size_points": round(bearish_gap, 4),
                        "size_pct": round(size_pct, 4),
                        "status": _mitigation_status(history, index, "bearish", bottom, top),
                    },
                )

    if not rows:
        return pd.DataFrame(columns=["timestamp", "direction", "top", "bottom", "midpoint", "size_points", "size_pct", "status"])
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
