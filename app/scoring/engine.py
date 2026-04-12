from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.models import ScoreResult


@dataclass(slots=True)
class BreakoutScoreWeights:
    """Configurable scoring weights that add up to 100."""

    breakout_strength: float = 25.0
    volume_confirmation: float = 20.0
    trend_alignment: float = 20.0
    relative_strength: float = 15.0
    volatility: float = 10.0
    liquidity_quality: float = 10.0

    def __post_init__(self) -> None:
        total = round(
            self.breakout_strength
            + self.volume_confirmation
            + self.trend_alignment
            + self.relative_strength
            + self.volatility
            + self.liquidity_quality,
            4,
        )
        if total != 100.0:
            raise ValueError(f"Scoring weights must add up to 100, received {total}.")


def _round_score(value: float) -> float:
    return round(max(value, 0.0), 2)


def _score_breakout_strength(signals: dict[str, Any], weight: float) -> float:
    breakout_20 = signals.get("breakout_20", {})
    breakout_55 = signals.get("breakout_55", {})
    distance_pct = float(signals.get("distance_above_breakout_pct") or 0.0)

    if signals.get("failed_breakout"):
        return 0.0

    if breakout_55.get("passed"):
        base_score = 0.95
    elif breakout_20.get("passed"):
        base_score = 0.80
    elif breakout_20.get("metrics", {}).get("near_breakout"):
        base_score = 0.45
    else:
        base_score = 0.10

    if distance_pct > 7.0:
        base_score -= 0.20
    elif distance_pct > 4.0:
        base_score -= 0.10

    return _round_score(weight * base_score)


def _score_volume_confirmation(signals: dict[str, Any], weight: float) -> float:
    volume_multiple = float(signals.get("volume_multiple") or 0.0)
    if volume_multiple <= 0:
        return 0.0

    normalized = min(volume_multiple / 2.5, 1.0)
    if volume_multiple < 1.0:
        normalized *= 0.5
    return _round_score(weight * normalized)


def _score_trend_alignment(signals: dict[str, Any], weight: float) -> float:
    trend = signals.get("trend", {})
    metrics = trend.get("metrics", {})
    checks = [
        bool(metrics.get("above_short_ma")),
        bool(metrics.get("above_long_ma")),
        bool(metrics.get("short_above_long")),
    ]
    return _round_score(weight * (sum(checks) / len(checks)))


def _score_relative_strength(signals: dict[str, Any], weight: float) -> float:
    rs = signals.get("relative_strength", {})
    metrics = rs.get("metrics", {})
    spread = float(metrics.get("relative_strength_spread_pct") or 0.0)

    if spread >= 5.0:
        multiplier = 1.0
    elif spread >= 2.0:
        multiplier = 0.8
    elif spread >= 0.0:
        multiplier = 0.55
    else:
        multiplier = 0.15

    return _round_score(weight * multiplier)


def _score_volatility(signals: dict[str, Any], weight: float) -> float:
    atr_status = str(signals.get("atr_status", "normal"))
    if atr_status in {"expanding", "compressed"}:
        multiplier = 1.0
    elif atr_status == "normal":
        multiplier = 0.5
    else:
        multiplier = 0.1
    return _round_score(weight * multiplier)


def _score_liquidity(signals: dict[str, Any], weight: float) -> float:
    status = str(signals.get("liquidity_status", "low"))
    if status == "high":
        multiplier = 1.0
    elif status == "medium":
        multiplier = 0.6
    else:
        multiplier = 0.2
    return _round_score(weight * multiplier)


def _rating_bucket(total_score: float) -> str:
    if total_score >= 80:
        return "A"
    if total_score >= 65:
        return "B"
    if total_score >= 50:
        return "C"
    return "Reject"


def score_breakout_setup(
    combined_signals: dict[str, Any],
    *,
    weights: BreakoutScoreWeights | None = None,
) -> ScoreResult:
    """Score one stock's combined breakout signals out of 100."""

    score_weights = weights or BreakoutScoreWeights()
    component_scores = {
        "breakout_strength": _score_breakout_strength(combined_signals, score_weights.breakout_strength),
        "volume_confirmation": _score_volume_confirmation(combined_signals, score_weights.volume_confirmation),
        "trend_alignment": _score_trend_alignment(combined_signals, score_weights.trend_alignment),
        "relative_strength": _score_relative_strength(combined_signals, score_weights.relative_strength),
        "volatility": _score_volatility(combined_signals, score_weights.volatility),
        "liquidity_quality": _score_liquidity(combined_signals, score_weights.liquidity_quality),
    }
    total_score = _round_score(sum(component_scores.values()))
    return ScoreResult(
        total_score=total_score,
        component_scores=component_scores,
        rating=_rating_bucket(total_score),
    )


def rank_stocks_by_score(results_df: pd.DataFrame) -> pd.DataFrame:
    """Rank stocks using total score, volume multiple, and breakout distance."""

    if results_df.empty:
        return results_df.copy()

    return (
        results_df.sort_values(
            by=["total_score", "volume_multiple", "distance_above_breakout_pct"],
            ascending=[False, False, False],
            kind="mergesort",
        )
        .reset_index(drop=True)
        .assign(rank=lambda frame: frame.index + 1)
    )
