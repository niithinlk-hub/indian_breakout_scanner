from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd

from app.stock_alerter.config import StockAlerterConfig
from app.stock_alerter.indicators import calculate_indicators
from app.stock_alerter.pattern_detectors import (
    detect_52week_high_breakout,
    detect_ascending_triangle,
    detect_bull_flag,
    detect_cup_handle,
    detect_major_swing_breakout,
    detect_range_breakout,
    detect_retest_confirmation,
)
from app.stock_alerter.scoring import format_signal_reasoning, score_signal
from app.stock_alerter.structure_logic import detect_bos, detect_bullish_fvg
from app.stock_alerter.utils import body_to_range_ratio, close_near_high, percent_distance, positive_slope, strip_exchange_suffix, upper_wick_ratio


def _trend_filter(frame: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    latest = frame.iloc[-1]
    ema20 = float(latest["ema20"])
    ema50 = float(latest["ema50"])
    close = float(latest["close"])
    status = close > ema20 and close > ema50 and ema20 > ema50 and positive_slope(frame["ema50"], periods=5)
    return status, {"ema20": round(ema20, 4), "ema50": round(ema50, 4), "ema_alignment_status": "aligned" if status else "not_aligned"}


def _momentum_filter(frame: pd.DataFrame, config: StockAlerterConfig) -> tuple[dict[str, bool], dict[str, Any]]:
    latest = frame.iloc[-1]
    rsi = float(latest["rsi14"])
    adx = float(latest["adx14"])
    atr = float(latest["atr14"])
    atr_baseline = float(latest["atr14_sma20"]) if pd.notna(latest["atr14_sma20"]) else None
    relative_strength = float(latest["relative_strength_spread"]) if pd.notna(latest["relative_strength_spread"]) else None
    flags = {
        "rsi_ok": config.rsi_lower <= rsi <= config.rsi_upper,
        "adx_ok": adx >= config.adx_threshold,
        "atr_expansion_ok": atr_baseline is not None and atr >= atr_baseline * config.atr_expansion_threshold,
        "relative_strength_ok": relative_strength is not None and relative_strength > 0,
    }
    return flags, {"rsi": round(rsi, 2), "adx": round(adx, 2), "atr": round(atr, 4), "relative_strength_spread": round(relative_strength, 4) if relative_strength is not None else None}


def _candle_quality(frame: pd.DataFrame) -> tuple[bool, dict[str, Any]]:
    latest = frame.iloc[-1]
    body_ratio = body_to_range_ratio(float(latest["open"]), float(latest["high"]), float(latest["low"]), float(latest["close"]))
    upper_wick = upper_wick_ratio(float(latest["open"]), float(latest["high"]), float(latest["close"]), float(latest["low"]))
    strong = close_near_high(float(latest["close"]), float(latest["high"]), float(latest["low"]), threshold=0.25) and body_ratio >= 0.45 and upper_wick <= 0.25
    return strong, {"body_ratio": body_ratio, "upper_wick_ratio": upper_wick, "close_near_high": close_near_high(float(latest["close"]), float(latest["high"]), float(latest["low"]))}


def _not_extended_from_ema20(frame: pd.DataFrame) -> bool:
    latest = frame.iloc[-1]
    ema20 = float(latest["ema20"])
    close = float(latest["close"])
    return close <= ema20 * 1.08 if ema20 else False


def _build_signal(
    symbol: str,
    company_name: str,
    pattern: dict[str, Any],
    indicators_frame: pd.DataFrame,
    trend_ok: bool,
    trend_metrics: dict[str, Any],
    momentum_flags: dict[str, bool],
    momentum_metrics: dict[str, Any],
    candle_ok: bool,
    candle_metrics: dict[str, Any],
    retest_result: dict[str, Any],
    bos_result: dict[str, Any],
    fvg_result: dict[str, Any],
    config: StockAlerterConfig,
) -> dict[str, Any]:
    latest = indicators_frame.iloc[-1]
    current_price = float(pattern["current_price"])
    volume_ratio = float(pattern["volume_ratio"]) if pattern.get("volume_ratio") is not None else None
    signal = {
        "symbol": strip_exchange_suffix(symbol),
        "company_name": company_name,
        "pattern_name": pattern["pattern_name"],
        "breakout_level": round(float(pattern["breakout_level"]), 4) if pattern.get("breakout_level") is not None else None,
        "breakout_buffered_level": round(float(pattern["breakout_buffered_level"]), 4)
        if pattern.get("breakout_buffered_level") is not None
        else None,
        "current_price": round(current_price, 4),
        "distance_from_breakout_pct": percent_distance(current_price, pattern.get("breakout_level")),
        "volume_ratio": round(volume_ratio, 4) if volume_ratio is not None else None,
        "rsi": momentum_metrics["rsi"],
        "adx": momentum_metrics["adx"],
        "atr": momentum_metrics["atr"],
        "ema20": trend_metrics["ema20"],
        "ema50": trend_metrics["ema50"],
        "ema_alignment_status": trend_metrics["ema_alignment_status"],
        "relative_strength_status": "positive" if momentum_flags["relative_strength_ok"] else "weak",
        "bos_status": "present" if bos_result["is_valid"] else "missing",
        "fvg_status": fvg_result.get("supporting_metrics", {}).get("fvg_status", "missing") if fvg_result else "missing",
        "retest_status": retest_result["status"],
        "invalidation_level": pattern.get("invalidation_level"),
        "supporting_metrics": {**pattern.get("supporting_metrics", {}), **trend_metrics, **momentum_metrics, **candle_metrics},
        "raw_pattern_features": pattern.get("raw_pattern_features", {}),
        "confidence_notes": list(pattern.get("confidence_notes", [])),
        "scan_timestamp": datetime.now(timezone.utc).isoformat(),
        "breakout_confirmed": bool(pattern.get("is_valid")),
        "volume_ok": volume_ratio is not None and volume_ratio >= config.minimum_volume_multiple,
        "ema_alignment_ok": trend_ok,
        "rsi_ok": momentum_flags["rsi_ok"],
        "adx_ok": momentum_flags["adx_ok"],
        "strong_candle_ok": candle_ok,
        "retest_ok": retest_result["is_valid"] if config.retest_required else (retest_result["is_valid"] or candle_ok),
        "bos_ok": bos_result["is_valid"],
        "fvg_ok": fvg_result["is_valid"],
        "relative_strength_ok": momentum_flags["relative_strength_ok"] or not config.relative_strength_filter,
        "atr_expansion_ok": momentum_flags["atr_expansion_ok"] if config.atr_expansion_required else True,
        "not_extended_ok": _not_extended_from_ema20(indicators_frame),
    }
    scored = score_signal(signal, config)
    signal.update(scored)
    signal["reasoning"] = format_signal_reasoning(signal)
    return signal


def scan_stock(
    df: pd.DataFrame,
    symbol: str,
    config: StockAlerterConfig,
    *,
    benchmark_df: pd.DataFrame | None = None,
    company_name: str | None = None,
) -> list[dict[str, Any]]:
    """Scan one stock and return high-quality bullish breakout signals."""

    if df.empty or len(df) < 80:
        return []

    frame = calculate_indicators(df, benchmark_df)
    if frame[["ema20", "ema50", "rsi14", "adx14", "atr14"]].dropna().empty:
        return []

    trend_ok, trend_metrics = _trend_filter(frame)
    momentum_flags, momentum_metrics = _momentum_filter(frame, config)
    candle_ok, candle_metrics = _candle_quality(frame)
    bos_result = detect_bos(frame, config)
    fvg_result = detect_bullish_fvg(frame, config)

    detectors = [
        detect_range_breakout(frame, config),
        detect_ascending_triangle(frame, config),
        detect_bull_flag(frame, config),
        detect_cup_handle(frame, config),
        detect_major_swing_breakout(frame, config),
    ]
    if config.require_52week_high_module:
        detectors.append(detect_52week_high_breakout(frame, config))
    detectors.extend([bos_result, fvg_result])

    if bos_result["is_valid"] and fvg_result["is_valid"]:
        combo_level = max(float(bos_result["breakout_level"]), float(fvg_result["breakout_level"]))
        combo_buffered = max(float(bos_result["breakout_buffered_level"]), float(fvg_result["breakout_buffered_level"]))
        detectors.append(
            {
                "is_valid": float(frame["close"].iloc[-1]) > combo_buffered,
                "pattern_name": "BOS + FVG continuation breakout",
                "breakout_level": combo_level,
                "breakout_buffered_level": combo_buffered,
                "current_price": float(frame["close"].iloc[-1]),
                "volume_ratio": float(frame["relative_volume"].iloc[-1]) if pd.notna(frame["relative_volume"].iloc[-1]) else None,
                "confidence_notes": ["Bullish BOS is aligned with a respected bullish FVG."],
                "supporting_metrics": {},
                "invalidation_level": min(float(bos_result["invalidation_level"] or combo_level), float(fvg_result["invalidation_level"] or combo_level)),
                "raw_pattern_features": {"bos": bos_result.get("raw_pattern_features", {}), "fvg": fvg_result.get("raw_pattern_features", {})},
            },
        )

    qualifying: list[dict[str, Any]] = []
    for pattern in detectors:
        if not pattern.get("is_valid"):
            continue

        retest_result = detect_retest_confirmation(frame, pattern.get("breakout_level"), config)
        if config.retest_required and not retest_result["is_valid"] and not candle_ok:
            continue
        if not trend_ok:
            continue
        if not momentum_flags["rsi_ok"] or not momentum_flags["adx_ok"]:
            continue
        if config.relative_strength_filter and not momentum_flags["relative_strength_ok"]:
            continue
        if config.bos_required and not bos_result["is_valid"]:
            continue
        if config.fvg_required and not fvg_result["is_valid"]:
            continue
        if config.atr_expansion_required and not momentum_flags["atr_expansion_ok"]:
            continue

        signal = _build_signal(
            symbol=symbol,
            company_name=company_name or strip_exchange_suffix(symbol),
            pattern=pattern,
            indicators_frame=frame,
            trend_ok=trend_ok,
            trend_metrics=trend_metrics,
            momentum_flags=momentum_flags,
            momentum_metrics=momentum_metrics,
            candle_ok=candle_ok,
            candle_metrics=candle_metrics,
            retest_result=retest_result,
            bos_result=bos_result,
            fvg_result=fvg_result,
            config=config,
        )
        if signal["category"] != "Reject / ignore":
            qualifying.append(signal)
    return qualifying


def scan_universe(
    history_map: dict[str, pd.DataFrame],
    config: StockAlerterConfig,
    *,
    benchmark_df: pd.DataFrame | None = None,
    company_names: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Scan a universe, rank valid signals, and return a results dataframe."""

    rows: list[dict[str, Any]] = []
    for symbol, history in history_map.items():
        rows.extend(
            scan_stock(
                history,
                symbol,
                config,
                benchmark_df=benchmark_df,
                company_name=(company_names or {}).get(symbol, symbol),
            ),
        )

    if not rows:
        return pd.DataFrame()
    results = pd.DataFrame(rows).sort_values(
        by=["score", "volume_ratio", "distance_from_breakout_pct"],
        ascending=[False, False, False],
        kind="mergesort",
    )
    return results.reset_index(drop=True)
