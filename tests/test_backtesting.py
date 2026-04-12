from __future__ import annotations

from app.backtesting.engine import EntryConfig, ExitConfig, run_breakout_backtest


def test_run_breakout_backtest_returns_summary_and_trades(breakout_stock_df) -> None:
    result = run_breakout_backtest(
        breakout_stock_df,
        symbol="RELIANCE",
        entry_config=EntryConfig(breakout_lookback=20, min_volume_multiple=1.5, require_above_200_dma=False),
        exit_config=ExitConfig(fixed_holding_period=5, stop_loss_pct=0.05, trailing_stop_pct=None),
    )

    assert set(result.summary).issuperset(
        {"total_trades", "win_rate", "average_return", "median_return", "max_drawdown", "expectancy"},
    )
    assert result.summary["symbol"] == "RELIANCE"
