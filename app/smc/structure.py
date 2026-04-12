from __future__ import annotations

from typing import Any

import pandas as pd


def detect_pivots(df: pd.DataFrame, left_bars: int = 3, right_bars: int = 3) -> pd.DataFrame:
    """Annotate pivot highs and lows using a left/right swing window."""

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    history["pivot_high"] = pd.NA
    history["pivot_low"] = pd.NA
    if history.empty:
        return history

    for index in range(left_bars, len(history) - right_bars):
        window = history.iloc[index - left_bars : index + right_bars + 1]
        current_high = float(history.at[index, "high"])
        current_low = float(history.at[index, "low"])
        if current_high >= float(window["high"].max()):
            history.at[index, "pivot_high"] = current_high
        if current_low <= float(window["low"].min()):
            history.at[index, "pivot_low"] = current_low
    return history


def extract_swings(pivot_frame: pd.DataFrame) -> pd.DataFrame:
    """Flatten pivot highs/lows into a swing table with HH/HL/LH/LL labels."""

    rows: list[dict[str, Any]] = []
    last_high: float | None = None
    last_low: float | None = None

    for _, row in pivot_frame.iterrows():
        if pd.notna(row.get("pivot_high")):
            price = float(row["pivot_high"])
            swing_label = "HH" if last_high is None or price > last_high else "LH"
            rows.append(
                {
                    "datetime": row["datetime"],
                    "swing_type": "high",
                    "price": price,
                    "classification": swing_label,
                },
            )
            last_high = price

        if pd.notna(row.get("pivot_low")):
            price = float(row["pivot_low"])
            swing_label = "HL" if last_low is None or price > last_low else "LL"
            rows.append(
                {
                    "datetime": row["datetime"],
                    "swing_type": "low",
                    "price": price,
                    "classification": swing_label,
                },
            )
            last_low = price

    if not rows:
        return pd.DataFrame(columns=["datetime", "swing_type", "price", "classification"])
    return pd.DataFrame(rows).sort_values("datetime").reset_index(drop=True)


def detect_structure_events(pivot_frame: pd.DataFrame) -> pd.DataFrame:
    """Detect BOS/CHoCH events on candle close against the latest swing levels."""

    events: list[dict[str, Any]] = []
    latest_high_level: float | None = None
    latest_low_level: float | None = None
    high_broken = False
    low_broken = False
    bias = "neutral"

    for _, row in pivot_frame.iterrows():
        if pd.notna(row.get("pivot_high")):
            latest_high_level = float(row["pivot_high"])
            high_broken = False
        if pd.notna(row.get("pivot_low")):
            latest_low_level = float(row["pivot_low"])
            low_broken = False

        close = float(row["close"])
        timestamp = row["datetime"]

        if latest_high_level is not None and not high_broken and close > latest_high_level:
            event_name = "Bullish CHoCH" if bias == "bearish" else "Bullish BOS"
            bias = "bullish"
            high_broken = True
            events.append(
                {
                    "datetime": timestamp,
                    "event": event_name,
                    "direction": "bullish",
                    "level": latest_high_level,
                    "close": close,
                },
            )

        if latest_low_level is not None and not low_broken and close < latest_low_level:
            event_name = "Bearish CHoCH" if bias == "bullish" else "Bearish BOS"
            bias = "bearish"
            low_broken = True
            events.append(
                {
                    "datetime": timestamp,
                    "event": event_name,
                    "direction": "bearish",
                    "level": latest_low_level,
                    "close": close,
                },
            )

    if not events:
        return pd.DataFrame(columns=["datetime", "event", "direction", "level", "close"])
    return pd.DataFrame(events).sort_values("datetime").reset_index(drop=True)


def analyze_structure(df: pd.DataFrame, left_bars: int = 3, right_bars: int = 3) -> dict[str, Any]:
    """Produce a structure summary used by both the screener and chart view."""

    pivots = detect_pivots(df, left_bars=left_bars, right_bars=right_bars)
    swings = extract_swings(pivots)
    events = detect_structure_events(pivots)

    latest_event = events.iloc[-1].to_dict() if not events.empty else {}
    latest_high = swings.loc[swings["swing_type"] == "high", "price"]
    latest_low = swings.loc[swings["swing_type"] == "low", "price"]

    if latest_event:
        latest_bias = str(latest_event["direction"])
    elif not swings.empty:
        last_label = str(swings.iloc[-1]["classification"])
        if last_label in {"HH", "HL"}:
            latest_bias = "bullish"
        elif last_label in {"LH", "LL"}:
            latest_bias = "bearish"
        else:
            latest_bias = "neutral"
    else:
        latest_bias = "neutral"

    return {
        "pivot_frame": pivots,
        "swings": swings,
        "events": events,
        "latest_bias": latest_bias,
        "latest_event": latest_event.get("event", "None"),
        "latest_event_time": latest_event.get("datetime"),
        "recent_swing_high": float(latest_high.iloc[-1]) if not latest_high.empty else None,
        "recent_swing_low": float(latest_low.iloc[-1]) if not latest_low.empty else None,
    }
