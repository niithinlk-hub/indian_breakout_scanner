from __future__ import annotations

import pandas as pd

from app.scoring.engine import BreakoutScoreWeights, rank_stocks_by_score, score_breakout_setup
from app.signals.breakout import combine_latest_signals


def test_score_breakout_setup_returns_bucketed_score(breakout_stock_df, benchmark_df) -> None:
    combined = combine_latest_signals("RELIANCE", breakout_stock_df, benchmark_df)
    result = score_breakout_setup(combined, weights=BreakoutScoreWeights())
    assert 0 <= result.total_score <= 100
    assert result.rating in {"A", "B", "C", "Reject"}
    assert set(result.component_scores) == {
        "breakout_strength",
        "volume_confirmation",
        "trend_alignment",
        "relative_strength",
        "volatility",
        "liquidity_quality",
    }


def test_rank_stocks_by_score_orders_descending() -> None:
    frame = pd.DataFrame(
        [
            {"symbol": "A", "total_score": 70, "volume_multiple": 1.8, "distance_above_breakout_pct": 1.0},
            {"symbol": "B", "total_score": 85, "volume_multiple": 1.2, "distance_above_breakout_pct": 0.5},
            {"symbol": "C", "total_score": 85, "volume_multiple": 2.1, "distance_above_breakout_pct": 0.2},
        ],
    )
    ranked = rank_stocks_by_score(frame)
    assert ranked.loc[0, "symbol"] == "C"
    assert ranked.loc[1, "symbol"] == "B"
