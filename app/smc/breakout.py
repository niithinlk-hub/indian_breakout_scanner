from __future__ import annotations

from typing import Any

import pandas as pd


def calculate_relative_volume(df: pd.DataFrame, lookback: int = 20) -> float | None:
    """Return latest volume divided by the previous lookback average."""

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    if len(history) < lookback + 1:
        return None
    average_volume = pd.to_numeric(history["volume"], errors="coerce").shift(1).rolling(lookback).mean().iloc[-1]
    latest_volume = pd.to_numeric(history["volume"], errors="coerce").iloc[-1]
    if pd.isna(average_volume) or not average_volume:
        return None
    return round(float(latest_volume / average_volume), 4)


def _resolve_range_levels(df: pd.DataFrame, breakout_lookback: int) -> tuple[float | None, float | None]:
    history = df.copy().sort_values("datetime").reset_index(drop=True)
    if len(history) < breakout_lookback + 1:
        return None, None
    prior = history.iloc[:-1].tail(breakout_lookback)
    return float(prior["high"].max()), float(prior["low"].min())


def analyze_breakout(
    df: pd.DataFrame,
    *,
    breakout_lookback: int = 20,
    close_confirmation: bool = True,
    buffer_pct: float = 0.3,
    near_threshold_pct: float = 1.0,
) -> dict[str, Any]:
    """Analyze bullish/bearish breakout state against recent range levels."""

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    latest = history.iloc[-1].to_dict() if not history.empty else {}
    swing_high, swing_low = _resolve_range_levels(history, breakout_lookback)
    if not latest or swing_high is None or swing_low is None:
        return {
            "status": "Insufficient Data",
            "breakout_level": None,
            "breakdown_level": None,
            "retest_possible": False,
            "distance_to_breakout_pct": None,
            "distance_to_breakdown_pct": None,
            "relative_volume": calculate_relative_volume(history),
        }

    close = float(latest["close"])
    high = float(latest["high"])
    low = float(latest["low"])
    price_for_upside = close if close_confirmation else high
    price_for_downside = close if close_confirmation else low

    bullish_trigger = swing_high * (1 + buffer_pct / 100.0)
    bearish_trigger = swing_low * (1 - buffer_pct / 100.0)
    bullish_breakout = price_for_upside > bullish_trigger
    bearish_breakdown = price_for_downside < bearish_trigger

    distance_to_breakout_pct = ((close / swing_high) - 1.0) * 100.0 if swing_high else None
    distance_to_breakdown_pct = ((close / swing_low) - 1.0) * 100.0 if swing_low else None
    near_bullish = not bullish_breakout and distance_to_breakout_pct is not None and distance_to_breakout_pct >= -near_threshold_pct
    near_bearish = not bearish_breakdown and distance_to_breakdown_pct is not None and distance_to_breakdown_pct <= near_threshold_pct

    if bullish_breakout:
        status = "Bullish Breakout"
    elif bearish_breakdown:
        status = "Bearish Breakdown"
    elif near_bullish:
        status = "Near Bullish Breakout"
    elif near_bearish:
        status = "Near Bearish Breakdown"
    else:
        status = "In Range"

    retest_possible = False
    if bullish_breakout and distance_to_breakout_pct is not None:
        retest_possible = distance_to_breakout_pct <= near_threshold_pct
    if bearish_breakdown and distance_to_breakdown_pct is not None:
        retest_possible = abs(distance_to_breakdown_pct) <= near_threshold_pct

    return {
        "status": status,
        "breakout_level": round(swing_high, 4),
        "breakdown_level": round(swing_low, 4),
        "retest_possible": retest_possible,
        "distance_to_breakout_pct": round(distance_to_breakout_pct, 4) if distance_to_breakout_pct is not None else None,
        "distance_to_breakdown_pct": round(distance_to_breakdown_pct, 4)
        if distance_to_breakdown_pct is not None
        else None,
        "relative_volume": calculate_relative_volume(history),
    }
