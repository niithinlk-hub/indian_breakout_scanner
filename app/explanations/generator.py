from __future__ import annotations

from typing import Any, Protocol

from app.models import ExplanationResult


class ExplanationEnhancer(Protocol):
    """Optional interface for future LLM-based explanation enrichment."""

    def enhance(self, payload: dict[str, Any], base_result: ExplanationResult) -> ExplanationResult:
        """Return an enhanced explanation result."""


def _format_distance(distance_pct: float | None) -> str:
    if distance_pct is None:
        return "around"
    if distance_pct >= 0:
        return f"{distance_pct:.2f}% above"
    return f"{abs(distance_pct):.2f}% below"


def generate_breakout_explanation(
    payload: dict[str, Any],
    *,
    enhancer: ExplanationEnhancer | None = None,
) -> ExplanationResult:
    """Generate a deterministic, template-first breakout explanation."""

    symbol = str(payload.get("symbol", "UNKNOWN"))
    close = float(payload.get("close") or 0.0)
    breakout_level = float(payload.get("breakout_level") or 0.0)
    distance_pct = payload.get("distance_above_breakout_pct")
    volume_multiple = float(payload.get("volume_multiple") or 0.0)
    dma_50_status = str(payload.get("dma_50_status", "unknown"))
    dma_200_status = str(payload.get("dma_200_status", "unknown"))
    atr_status = str(payload.get("atr_status", "normal"))
    rs_status = str(payload.get("relative_strength_status", "inline"))
    total_score = float(payload.get("total_score") or 0.0)
    rating = str(payload.get("rating", "Reject"))
    signal_state = str(payload.get("signal_state", "watch"))

    tags: list[str] = []
    if signal_state == "breakout" and total_score >= 75 and (distance_pct or 0.0) <= 4.0:
        tags.append("clean breakout")
    if (distance_pct or 0.0) > 5.0:
        tags.append("extended")
    if total_score < 60 or volume_multiple < 1.2:
        tags.append("low conviction")
    if dma_50_status == "above" and dma_200_status == "above":
        tags.append("trend aligned")
    if volume_multiple >= 2.0:
        tags.append("high volume")
    if distance_pct is not None and -2.0 <= float(distance_pct) <= 1.0:
        tags.append("near trigger")
    if signal_state == "failed_breakout":
        tags.append("failed breakout")

    sentences = [
        f"{symbol} closed at {close:.2f}, {_format_distance(distance_pct if distance_pct is not None else None)} its breakout level of {breakout_level:.2f}.",
        f"Participation was {'strong' if volume_multiple >= 1.5 else 'average'} with volume at {volume_multiple:.2f}x the recent norm.",
        f"Trend structure is {'supportive' if dma_50_status == 'above' and dma_200_status == 'above' else 'mixed'}, with price {dma_50_status} the 50 DMA and {dma_200_status} the 200 DMA.",
        f"Volatility is {atr_status} while relative strength is {rs_status}, which helps frame the quality of follow-through from here.",
        f"The setup earns a total score of {total_score:.1f}/100 and lands in the {rating} bucket.",
    ]

    trader_summary = (
        f"{symbol}: {rating}-rated {signal_state.replace('_', ' ')} setup with "
        f"{volume_multiple:.2f}x volume and score {total_score:.1f}/100."
    )
    base_result = ExplanationResult(
        explanation=" ".join(sentences),
        trader_summary=trader_summary,
        tags=tags,
    )
    return enhancer.enhance(payload, base_result) if enhancer else base_result
