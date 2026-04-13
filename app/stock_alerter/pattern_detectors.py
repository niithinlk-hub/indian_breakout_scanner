from __future__ import annotations

from typing import Any

import pandas as pd

from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.utils import compact_dict, percent_distance, rolling_pivots, safe_mean


def _base_response(df: pd.DataFrame, pattern_name: str) -> dict[str, Any]:
    current_price = float(df["close"].iloc[-1]) if not df.empty else None
    volume_ratio = float(df["relative_volume"].iloc[-1]) if "relative_volume" in df.columns and not df.empty else None
    return {
        "is_valid": False,
        "pattern_name": pattern_name,
        "breakout_level": None,
        "breakout_buffered_level": None,
        "current_price": current_price,
        "volume_ratio": volume_ratio,
        "confidence_notes": [],
        "supporting_metrics": {},
        "invalidation_level": None,
        "raw_pattern_features": {},
    }


def detect_range_breakout(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect range breakout from a tight sideways band."""

    result = _base_response(df, "Range breakout")
    if len(df) < config.range_lookback + 5:
        result["confidence_notes"] = ["Not enough history for range breakout."]
        return result

    window = df.iloc[-config.range_lookback - 1 : -1]
    resistance = float(window["high"].max())
    support = float(window["low"].min())
    width_pct = ((resistance / support) - 1.0) * 100.0 if support else None
    tests = int((window["high"] >= resistance * (1 - 0.003)).sum())
    buffered = resistance * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    is_valid = width_pct is not None and width_pct <= 12.0 and tests >= 2 and current_close > buffered

    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": resistance,
            "breakout_buffered_level": buffered,
            "invalidation_level": support,
            "confidence_notes": ["Sideways range with repeated resistance tests."] if is_valid else [],
            "supporting_metrics": compact_dict({"range_width_pct": round(width_pct, 4) if width_pct is not None else None, "resistance_tests": tests}),
            "raw_pattern_features": {"support": support, "resistance": resistance},
        },
    )
    return result


def detect_ascending_triangle(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect a flat-topped consolidation with rising lows."""

    result = _base_response(df, "Ascending triangle breakout")
    pivots = rolling_pivots(df.tail(max(config.range_lookback, 40)).reset_index(drop=True), left=2, right=2)
    highs = pivots.loc[pd.notna(pivots["pivot_high"]), "pivot_high"].tail(4).astype(float).tolist()
    lows = pivots.loc[pd.notna(pivots["pivot_low"]), "pivot_low"].tail(4).astype(float).tolist()
    if len(highs) < 2 or len(lows) < 2:
        result["confidence_notes"] = ["Not enough pivots for ascending triangle."]
        return result

    resistance = safe_mean(highs)
    tolerance_pct = max(config.triangle_tolerance_pct, 0.2)
    flat_resistance = max(highs) <= resistance * (1 + tolerance_pct / 100.0)
    rising_lows = all(lows[idx] > lows[idx - 1] for idx in range(1, len(lows)))
    buffered = resistance * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    is_valid = flat_resistance and rising_lows and current_close > buffered
    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": resistance,
            "breakout_buffered_level": buffered,
            "invalidation_level": min(lows),
            "confidence_notes": ["Flat resistance with rising lows resolved upward."] if is_valid else [],
            "supporting_metrics": {"high_points": len(highs), "low_points": len(lows)},
            "raw_pattern_features": {"highs": highs, "lows": lows},
        },
    )
    return result


def detect_bull_flag(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect impulse + shallow pullback + breakout above flag high."""

    result = _base_response(df, "Bull flag breakout")
    if len(df) < 30:
        result["confidence_notes"] = ["Not enough history for bull flag."]
        return result

    impulse = df.iloc[-25:-10]
    flag = df.iloc[-10:-1]
    impulse_gain_pct = ((float(impulse["close"].iloc[-1]) / float(impulse["close"].iloc[0])) - 1.0) * 100.0
    pullback_pct = ((float(flag["high"].max()) - float(flag["low"].min())) / float(flag["high"].max())) * 100.0
    flag_high = float(flag["high"].max())
    buffered = flag_high * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    is_valid = impulse_gain_pct >= 10.0 and pullback_pct <= config.flag_consolidation_depth_pct and current_close > buffered
    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": flag_high,
            "breakout_buffered_level": buffered,
            "invalidation_level": float(flag["low"].min()),
            "confidence_notes": ["Strong prior impulse followed by a shallow flag."] if is_valid else [],
            "supporting_metrics": {"impulse_gain_pct": round(impulse_gain_pct, 4), "pullback_pct": round(pullback_pct, 4)},
            "raw_pattern_features": {"flag_high": flag_high},
        },
    )
    return result


def detect_cup_handle(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Approximate cup-and-handle breakout near a prior rim."""

    result = _base_response(df, "Cup and handle breakout")
    if len(df) < 80:
        result["confidence_notes"] = ["Not enough history for cup-and-handle approximation."]
        return result

    window = df.iloc[-80:]
    left_half = window.iloc[:35]
    trough_zone = window.iloc[25:55]
    right_half = window.iloc[45:70]
    handle = window.iloc[70:-1]
    if handle.empty:
        result["confidence_notes"] = ["No handle window available."]
        return result

    left_rim = float(left_half["high"].max())
    trough = float(trough_zone["low"].min())
    right_rim = float(right_half["high"].max())
    rim_similarity = abs(right_rim - left_rim) / left_rim * 100.0 if left_rim else 100.0
    handle_depth_pct = ((right_rim - float(handle["low"].min())) / right_rim) * 100.0 if right_rim else 100.0
    breakout_level = max(left_rim, right_rim)
    buffered = breakout_level * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    is_valid = rim_similarity <= 6.0 and handle_depth_pct <= 8.0 and current_close > buffered and trough < left_rim * 0.9
    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": breakout_level,
            "breakout_buffered_level": buffered,
            "invalidation_level": float(handle["low"].min()),
            "confidence_notes": ["Rounded recovery into a shallow handle near prior highs."] if is_valid else [],
            "supporting_metrics": {"rim_similarity_pct": round(rim_similarity, 4), "handle_depth_pct": round(handle_depth_pct, 4)},
            "raw_pattern_features": {"left_rim": left_rim, "right_rim": right_rim, "trough": trough},
        },
    )
    return result


def detect_major_swing_breakout(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect close above a recent pivot high."""

    result = _base_response(df, "Major swing high breakout")
    pivots = rolling_pivots(df.tail(max(config.swing_lookback + 15, 30)).reset_index(drop=True), left=2, right=2)
    highs = pivots.loc[pd.notna(pivots["pivot_high"]), "pivot_high"].astype(float)
    if highs.empty:
        result["confidence_notes"] = ["No recent swing high found."]
        return result

    breakout_level = float(highs.iloc[-1])
    buffered = breakout_level * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    recent_low = float(df.tail(config.swing_lookback)["low"].min())
    is_valid = current_close > buffered
    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": breakout_level,
            "breakout_buffered_level": buffered,
            "invalidation_level": recent_low,
            "confidence_notes": ["Price closed above the latest meaningful pivot high."] if is_valid else [],
            "supporting_metrics": {"swing_lookback": config.swing_lookback},
            "raw_pattern_features": {"pivot_high": breakout_level},
        },
    )
    return result


def detect_52week_high_breakout(df: pd.DataFrame, config: StockAlerterConfig) -> dict[str, Any]:
    """Detect breakout above the rolling 252-session high excluding the current bar."""

    result = _base_response(df, "52-week high breakout")
    if len(df) < 253:
        result["confidence_notes"] = ["Not enough sessions for 52-week high breakout."]
        return result

    breakout_level = float(df["high"].shift(1).rolling(252, min_periods=252).max().iloc[-1])
    buffered = breakout_level * (1 + config.breakout_buffer_pct / 100.0)
    current_close = float(df["close"].iloc[-1])
    recent_low = float(df.tail(30)["low"].min())
    is_valid = current_close > buffered
    result.update(
        {
            "is_valid": is_valid,
            "breakout_level": breakout_level,
            "breakout_buffered_level": buffered,
            "invalidation_level": recent_low,
            "confidence_notes": ["Price closed above the prior rolling 252-session high."] if is_valid else [],
            "supporting_metrics": {"lookback_sessions": 252},
            "raw_pattern_features": {"rolling_high": breakout_level},
        },
    )
    return result


def detect_retest_confirmation(df: pd.DataFrame, breakout_level: float | None, config: StockAlerterConfig) -> dict[str, Any]:
    """Check whether the recent candles held above breakout after the move."""

    if breakout_level is None or len(df) < config.retest_candle_count + 1:
        return {"is_valid": False, "status": "not_available", "details": "No breakout level for retest logic."}

    recent = df.tail(config.retest_candle_count)
    held = bool((pd.to_numeric(recent["low"], errors="coerce") >= breakout_level).all())
    status = "confirmed" if held else "not_confirmed"
    return {
        "is_valid": held,
        "status": status,
        "details": f"Last {config.retest_candle_count} candles {'held' if held else 'did not hold'} above breakout level.",
    }
