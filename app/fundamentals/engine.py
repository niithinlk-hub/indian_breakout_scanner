from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.models import CompositeScoreResult, ScoreResult


@dataclass(slots=True)
class FundamentalScoreWeights:
    """Configurable weights for fundamentals scoring."""

    growth_quality: float = 25.0
    return_ratios: float = 20.0
    balance_sheet: float = 15.0
    profitability: float = 15.0
    ownership_quality: float = 10.0
    scale_quality: float = 15.0

    def __post_init__(self) -> None:
        total = round(
            self.growth_quality
            + self.return_ratios
            + self.balance_sheet
            + self.profitability
            + self.ownership_quality
            + self.scale_quality,
            4,
        )
        if total != 100.0:
            raise ValueError(f"Fundamental weights must add up to 100, received {total}.")


@dataclass(slots=True)
class CompositeScoreWeights:
    """Relative weighting between technical and fundamental scores."""

    technical: float = 0.6
    fundamental: float = 0.4

    def __post_init__(self) -> None:
        total = round(self.technical + self.fundamental, 6)
        if total != 1.0:
            raise ValueError(f"Composite weights must add up to 1.0, received {total}.")


def _round_score(value: float) -> float:
    return round(max(value, 0.0), 2)


def _rating_bucket(total_score: float) -> str:
    if total_score >= 80:
        return "A"
    if total_score >= 65:
        return "B"
    if total_score >= 50:
        return "C"
    return "Reject"


def _normalize_higher_better(value: float | None, thresholds: tuple[float, float, float]) -> float:
    if value is None or pd.isna(value):
        return 0.0
    low, medium, high = thresholds
    if value >= high:
        return 1.0
    if value >= medium:
        return 0.8
    if value >= low:
        return 0.55
    return 0.2


def _normalize_lower_better(value: float | None, thresholds: tuple[float, float, float]) -> float:
    if value is None or pd.isna(value):
        return 0.0
    low, medium, high = thresholds
    if value <= low:
        return 1.0
    if value <= medium:
        return 0.8
    if value <= high:
        return 0.55
    return 0.2


def _scale_bucket_score(bucket: str | None) -> float:
    value = str(bucket or "").strip().lower()
    mapping = {
        "mega": 1.0,
        "mega_cap": 1.0,
        "large": 0.9,
        "large_cap": 0.9,
        "mid": 0.7,
        "mid_cap": 0.7,
        "small": 0.45,
        "small_cap": 0.45,
        "micro": 0.2,
        "micro_cap": 0.2,
    }
    return mapping.get(value, 0.4 if value else 0.0)


def score_fundamentals(
    snapshot: dict[str, Any],
    *,
    weights: FundamentalScoreWeights | None = None,
) -> ScoreResult:
    """Score one stock's fundamentals out of 100."""

    score_weights = weights or FundamentalScoreWeights()
    revenue_growth = snapshot.get("revenue_growth_pct")
    eps_growth = snapshot.get("eps_growth_pct")
    growth_multiplier = (
        _normalize_higher_better(revenue_growth, (5.0, 10.0, 15.0))
        + _normalize_higher_better(eps_growth, (8.0, 15.0, 20.0))
    ) / 2

    roe = snapshot.get("roe_pct")
    roce = snapshot.get("roce_pct")
    return_multiplier = (
        _normalize_higher_better(roe, (10.0, 15.0, 20.0))
        + _normalize_higher_better(roce, (10.0, 15.0, 20.0))
    ) / 2

    debt_to_equity = snapshot.get("debt_to_equity")
    net_margin = snapshot.get("net_margin_pct")
    promoter_holding = snapshot.get("promoter_holding_pct")
    market_cap_bucket = snapshot.get("market_cap_bucket")

    component_scores = {
        "growth_quality": _round_score(score_weights.growth_quality * growth_multiplier),
        "return_ratios": _round_score(score_weights.return_ratios * return_multiplier),
        "balance_sheet": _round_score(
            score_weights.balance_sheet * _normalize_lower_better(debt_to_equity, (0.3, 0.6, 1.0)),
        ),
        "profitability": _round_score(
            score_weights.profitability * _normalize_higher_better(net_margin, (8.0, 12.0, 18.0)),
        ),
        "ownership_quality": _round_score(
            score_weights.ownership_quality * _normalize_higher_better(promoter_holding, (35.0, 50.0, 65.0)),
        ),
        "scale_quality": _round_score(score_weights.scale_quality * _scale_bucket_score(market_cap_bucket)),
    }
    total_score = _round_score(sum(component_scores.values()))
    return ScoreResult(
        total_score=total_score,
        component_scores=component_scores,
        rating=_rating_bucket(total_score),
    )


def combine_scores(
    technical_score: ScoreResult,
    fundamental_score: ScoreResult,
    *,
    weights: CompositeScoreWeights | None = None,
) -> CompositeScoreResult:
    """Combine technical and fundamental scores into a composite score."""

    composite_weights = weights or CompositeScoreWeights()
    total_score = _round_score(
        (technical_score.total_score * composite_weights.technical)
        + (fundamental_score.total_score * composite_weights.fundamental),
    )
    component_scores = {
        "technical_score": technical_score.total_score,
        "fundamental_score": fundamental_score.total_score,
    }
    return CompositeScoreResult(
        total_score=total_score,
        technical_score=technical_score.total_score,
        fundamental_score=fundamental_score.total_score,
        component_scores=component_scores,
        rating=_rating_bucket(total_score),
    )


def rank_stocks_by_score(results_df: pd.DataFrame) -> pd.DataFrame:
    """Rank stocks using composite, technical, and fundamental scores."""

    if results_df.empty:
        return results_df.copy()

    return (
        results_df.sort_values(
            by=["total_score", "technical_score", "fundamental_score", "volume_multiple", "distance_above_breakout_pct"],
            ascending=[False, False, False, False, False],
            kind="mergesort",
        )
        .reset_index(drop=True)
        .assign(rank=lambda frame: frame.index + 1)
    )
