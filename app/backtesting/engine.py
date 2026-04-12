from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd


@dataclass(slots=True)
class EntryConfig:
    """Entry conditions for a breakout strategy."""

    breakout_lookback: int = 20
    min_volume_multiple: float = 2.0
    require_above_200_dma: bool = True


@dataclass(slots=True)
class ExitConfig:
    """Exit conditions for a breakout strategy."""

    fixed_holding_period: int | None = 10
    stop_loss_pct: float | None = 0.05
    trailing_stop_pct: float | None = 0.08
    close_below_moving_average: int | None = None


@dataclass(slots=True)
class BacktestResult:
    """Trade log and summary metrics."""

    trades: pd.DataFrame
    summary: dict[str, Any]


def _prepare_backtest_frame(df: pd.DataFrame, entry_config: EntryConfig, exit_config: ExitConfig) -> pd.DataFrame:
    history = df.copy().sort_values("datetime").reset_index(drop=True)
    history["breakout_level"] = history["high"].shift(1).rolling(entry_config.breakout_lookback).max()
    history["avg_volume"] = history["volume"].shift(1).rolling(20).mean()
    history["volume_multiple"] = history["volume"] / history["avg_volume"]
    history["dma_200"] = history["close"].rolling(200).mean()
    if exit_config.close_below_moving_average:
        history[f"exit_ma_{exit_config.close_below_moving_average}"] = history["close"].rolling(
            exit_config.close_below_moving_average,
        ).mean()
    return history


def _calculate_expectancy(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    winners = trades.loc[trades["return_pct"] > 0, "return_pct"]
    losers = trades.loc[trades["return_pct"] <= 0, "return_pct"]
    win_rate = len(winners) / len(trades)
    loss_rate = len(losers) / len(trades)
    average_win = winners.mean() if not winners.empty else 0.0
    average_loss = losers.mean() if not losers.empty else 0.0
    return float((win_rate * average_win) + (loss_rate * average_loss))


def _calculate_max_drawdown(trades: pd.DataFrame) -> float:
    if trades.empty:
        return 0.0
    equity_curve = (1 + trades["return_pct"] / 100.0).cumprod()
    running_peak = equity_curve.cummax()
    drawdown = equity_curve / running_peak - 1.0
    return float(drawdown.min() * 100)


def run_breakout_backtest(
    df: pd.DataFrame,
    *,
    symbol: str,
    entry_config: EntryConfig | None = None,
    exit_config: ExitConfig | None = None,
) -> BacktestResult:
    """Backtest a configurable daily breakout strategy on OHLCV data."""

    effective_entry = entry_config or EntryConfig()
    effective_exit = exit_config or ExitConfig()
    history = _prepare_backtest_frame(df, effective_entry, effective_exit)
    trades: list[dict[str, Any]] = []

    position: dict[str, Any] | None = None
    for index, row in history.iterrows():
        if pd.isna(row.get("breakout_level")) or pd.isna(row.get("volume_multiple")):
            continue

        if position is None:
            above_200_dma = not effective_entry.require_above_200_dma or (
                pd.notna(row.get("dma_200")) and row["close"] > row["dma_200"]
            )
            entry_signal = (
                row["close"] > row["breakout_level"]
                and row["volume_multiple"] >= effective_entry.min_volume_multiple
                and above_200_dma
            )
            if entry_signal:
                position = {
                    "entry_index": index,
                    "entry_date": row["datetime"],
                    "entry_price": float(row["close"]),
                    "highest_close": float(row["close"]),
                    "breakout_level": float(row["breakout_level"]),
                }
            continue

        position["highest_close"] = max(position["highest_close"], float(row["close"]))
        holding_period = index - int(position["entry_index"])
        exit_reason: str | None = None
        exit_price = float(row["close"])

        if effective_exit.stop_loss_pct is not None:
            stop_price = float(position["entry_price"]) * (1 - effective_exit.stop_loss_pct)
            if float(row["low"]) <= stop_price:
                exit_reason = "stop_loss"
                exit_price = stop_price

        if exit_reason is None and effective_exit.trailing_stop_pct is not None:
            trailing_stop = float(position["highest_close"]) * (1 - effective_exit.trailing_stop_pct)
            if float(row["low"]) <= trailing_stop:
                exit_reason = "trailing_stop"
                exit_price = trailing_stop

        if exit_reason is None and effective_exit.close_below_moving_average is not None:
            moving_average = row.get(f"exit_ma_{effective_exit.close_below_moving_average}")
            if pd.notna(moving_average) and float(row["close"]) < float(moving_average):
                exit_reason = f"close_below_ma_{effective_exit.close_below_moving_average}"

        if exit_reason is None and effective_exit.fixed_holding_period is not None:
            if holding_period >= effective_exit.fixed_holding_period:
                exit_reason = "time_exit"

        if exit_reason is None:
            continue

        entry_price = float(position["entry_price"])
        return_pct = ((exit_price / entry_price) - 1.0) * 100
        trades.append(
            {
                "symbol": symbol,
                "entry_date": position["entry_date"],
                "exit_date": row["datetime"],
                "entry_price": round(entry_price, 4),
                "exit_price": round(exit_price, 4),
                "return_pct": round(return_pct, 4),
                "holding_days": holding_period,
                "exit_reason": exit_reason,
                "breakout_level": round(float(position["breakout_level"]), 4),
            },
        )
        position = None

    trades_df = pd.DataFrame(trades)
    summary = {
        "symbol": symbol,
        "total_trades": int(len(trades_df)),
        "win_rate": round(float((trades_df["return_pct"] > 0).mean() * 100), 2) if not trades_df.empty else 0.0,
        "average_return": round(float(trades_df["return_pct"].mean()), 4) if not trades_df.empty else 0.0,
        "median_return": round(float(trades_df["return_pct"].median()), 4) if not trades_df.empty else 0.0,
        "max_drawdown": round(_calculate_max_drawdown(trades_df), 4),
        "expectancy": round(_calculate_expectancy(trades_df), 4),
        "entry_config": asdict(effective_entry),
        "exit_config": asdict(effective_exit),
    }
    return BacktestResult(trades=trades_df, summary=summary)
