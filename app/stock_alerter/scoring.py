from __future__ import annotations

from typing import Any

from app.stock_alerter.config import StockAlerterConfig


def categorize_signal(score: int, config: StockAlerterConfig) -> str:
    """Map a numeric score into a signal bucket."""

    if score >= config.category_aplus_min:
        return "A+ Breakout"
    if score >= config.category_a_min:
        return "A Breakout"
    if score >= config.category_watch_min:
        return "Watchlist"
    return "Reject / ignore"


def score_signal(signal: dict[str, Any], config: StockAlerterConfig) -> dict[str, Any]:
    """Score a valid signal using configurable weighted confirmations."""

    weights = config.signal_weights
    confirmations: dict[str, bool] = {
        "breakout_confirmed": bool(signal.get("breakout_confirmed")),
        "volume_expansion": bool(signal.get("volume_ok")),
        "ema_trend_alignment": bool(signal.get("ema_alignment_ok")),
        "rsi_bullish": bool(signal.get("rsi_ok")),
        "adx_trend_strength": bool(signal.get("adx_ok")),
        "strong_candle": bool(signal.get("strong_candle_ok")),
        "retest_confirmation": bool(signal.get("retest_ok")),
        "bos_present": bool(signal.get("bos_ok")),
        "bullish_fvg_present": bool(signal.get("fvg_ok")),
        "relative_strength_positive": bool(signal.get("relative_strength_ok")),
        "atr_expansion": bool(signal.get("atr_expansion_ok")),
        "not_extended_from_ema20": bool(signal.get("not_extended_ok")),
    }
    score = sum(int(weights.get(name, 0)) for name, passed in confirmations.items() if passed)
    missing = [name for name, passed in confirmations.items() if not passed]
    satisfied = [name for name, passed in confirmations.items() if passed]
    return {
        "score": score,
        "category": categorize_signal(score, config),
        "satisfied_confirmations": satisfied,
        "missing_confirmations": missing,
        "confirmation_matrix": confirmations,
    }


def format_signal_reasoning(signal: dict[str, Any]) -> str:
    """Create a structured, trader-friendly explanation for one signal."""

    satisfied = ", ".join(signal.get("satisfied_confirmations", [])) or "none"
    missing = ", ".join(signal.get("missing_confirmations", [])) or "none"
    invalidation = signal.get("invalidation_level")
    distance = signal.get("distance_from_breakout_pct")
    return (
        f"{signal['pattern_name']} used breakout level {signal.get('breakout_level')} with current price "
        f"{signal.get('current_price')}. Confirmations satisfied: {satisfied}. Missing items: {missing}. "
        f"Assigned score {signal.get('score')} -> {signal.get('category')}. "
        f"Distance from breakout is {distance if distance is not None else 'NA'}%. "
        f"Setup invalidation reference is {invalidation if invalidation is not None else 'NA'}."
    )
