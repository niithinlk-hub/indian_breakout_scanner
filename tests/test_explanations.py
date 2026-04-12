from __future__ import annotations

from app.explanations.generator import generate_breakout_explanation
from app.scoring.engine import score_breakout_setup
from app.signals.breakout import combine_latest_signals


def test_generate_breakout_explanation_returns_template_output(breakout_stock_df, benchmark_df) -> None:
    combined = combine_latest_signals("RELIANCE", breakout_stock_df, benchmark_df)
    score = score_breakout_setup(combined)
    payload = {**combined, **score.to_dict()}
    explanation = generate_breakout_explanation(payload)

    assert explanation.trader_summary.startswith("RELIANCE:")
    assert explanation.explanation.count(".") >= 5
    assert isinstance(explanation.tags, list)
