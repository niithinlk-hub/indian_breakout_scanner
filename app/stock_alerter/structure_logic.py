from __future__ import annotations

from typing import Any

import pandas as pd

from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.utils import rolling_pivots


def detect_bos(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect bullish break of structure above the latest pivot high."""

    pivots = rolling_pivots(df, left=3, right=3)
    swing_highs = pivots.loc[pd.notna(pivots["pivot_high"]), ["datetime", "pivot_high"]]
    if swing_highs.empty or len(df) < 5:
        return {
            "is_valid": False,
            "pattern_name": "Bullish BOS",
            "breakout_level": None,
            "breakout_buffered_level": None,
            "current_price": float(df["close"].iloc[-1]) if not df.empty else None,
            "volume_ratio": float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns and not df.empty else None,
            "confidence_notes": ["Insufficient swing structure for BOS."],
            "supporting_metrics": {},
            "invalidation_level": None,
            "raw_pattern_features": {},
        }

    latest_swing_high = float(swing_highs["pivot_high"].iloc[-1])
    latest_close = float(df["close"].iloc[-1])
    buffered = latest_swing_high * (1 + config.breakout_buffer_pct / 100.0)
    is_valid = latest_close > buffered
    invalidation = float(df["ema20"].iloc[-1]) if "ema20" in df.columns else latest_swing_high
    return {
        "is_valid": is_valid,
        "pattern_name": "Bullish BOS",
        "breakout_level": latest_swing_high,
        "breakout_buffered_level": buffered,
        "current_price": latest_close,
        "volume_ratio": float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns else None,
        "confidence_notes": ["Close broke above the most recent swing high on a closing basis."] if is_valid else [],
        "supporting_metrics": {"pivot_count": int(len(swing_highs))},
        "invalidation_level": invalidation,
        "raw_pattern_features": {"swing_high_datetime": swing_highs["datetime"].iloc[-1]},
    }


def detect_bullish_fvg(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect the latest valid bullish fair-value gap and whether price respected it."""

    if len(df) < 3:
        return {
            "is_valid": False,
            "pattern_name": "Bullish FVG",
            "breakout_level": None,
            "breakout_buffered_level": None,
            "current_price": float(df["close"].iloc[-1]) if not df.empty else None,
            "volume_ratio": float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns and not df.empty else None,
            "confidence_notes": ["Insufficient bars for FVG."],
            "supporting_metrics": {},
            "invalidation_level": None,
            "raw_pattern_features": {},
        }

    gaps: list[dict[str, Any]] = []
    for idx in range(2, len(df)):
        candle1 = df.iloc[idx - 2]
        candle3 = df.iloc[idx]
        if float(candle3["low"]) > float(candle1["high"]):
            bottom = float(candle1["high"])
            top = float(candle3["low"])
            midpoint = (bottom + top) / 2.0
            future_lows = pd.to_numeric(df.iloc[idx + 1 :]["low"], errors="coerce")
            if future_lows.empty:
                status = "fresh"
            elif (future_lows <= bottom).any():
                status = "invalidated"
            elif (future_lows <= top).any():
                status = "partially respected"
            else:
                status = "fresh"
            gaps.append(
                {
                    "timestamp": candle3["datetime"],
                    "bottom": bottom,
                    "top": top,
                    "midpoint": midpoint,
                    "status": status,
                },
            )

    if not gaps:
        return {
            "is_valid": False,
            "pattern_name": "Bullish FVG",
            "breakout_level": None,
            "breakout_buffered_level": None,
            "current_price": float(df["close"].iloc[-1]),
            "volume_ratio": float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns else None,
            "confidence_notes": ["No bullish FVG detected."],
            "supporting_metrics": {},
            "invalidation_level": None,
            "raw_pattern_features": {},
        }

    latest = gaps[-1]
    current_price = float(df["close"].iloc[-1])
    respected = latest["status"] in {"fresh", "partially respected"} and current_price >= latest["bottom"]
    return {
        "is_valid": respected,
        "pattern_name": "Bullish FVG",
        "breakout_level": latest["top"],
        "breakout_buffered_level": latest["top"],
        "current_price": current_price,
        "volume_ratio": float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns else None,
        "confidence_notes": [f"Latest bullish FVG is {latest['status']} around {latest['midpoint']:.2f}."],
        "supporting_metrics": {
            "fvg_status": latest["status"],
            "fvg_midpoint": latest["midpoint"],
            "fvg_bottom": latest["bottom"],
            "fvg_top": latest["top"],
        },
        "invalidation_level": latest["bottom"],
        "raw_pattern_features": latest,
    }
