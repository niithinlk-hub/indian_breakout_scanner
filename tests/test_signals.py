from __future__ import annotations

from app.signals.breakout import (
    atr_expansion,
    breakout_above_n_day_high,
    combine_latest_signals,
    moving_average_filter,
    relative_strength_vs_benchmark,
    volume_spike,
)


def test_breakout_signal_detects_latest_breakout(breakout_stock_df) -> None:
    result = breakout_above_n_day_high(breakout_stock_df, n=20)
    assert result.passed is True
    assert result.status == "breakout"
    assert result.metrics["distance_pct"] > 0


def test_volume_spike_detects_confirmation(breakout_stock_df) -> None:
    result = volume_spike(breakout_stock_df, lookback=20, multiple=1.5)
    assert result.passed is True
    assert result.metrics["volume_multiple"] >= 1.5


def test_trend_atr_and_relative_strength_are_available(breakout_stock_df, benchmark_df) -> None:
    trend = moving_average_filter(breakout_stock_df)
    atr = atr_expansion(breakout_stock_df)
    rs = relative_strength_vs_benchmark(breakout_stock_df, benchmark_df)

    assert trend.status in {"trend_aligned", "mixed"}
    assert atr.status in {"expanding", "compressed", "normal"}
    assert rs.status in {"outperforming", "inline", "lagging"}


def test_combine_latest_signals_returns_flattenable_payload(breakout_stock_df, benchmark_df) -> None:
    combined = combine_latest_signals("RELIANCE", breakout_stock_df, benchmark_df)
    assert combined["symbol"] == "RELIANCE"
    assert combined["signal_state"] in {"breakout", "near_breakout", "watch", "failed_breakout"}
    assert "breakout_20" in combined
    assert "volume_multiple" in combined
