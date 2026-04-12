from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from app.models import SignalResult


def _insufficient_signal(name: str, reason: str, **metrics: Any) -> SignalResult:
    return SignalResult(
        name=name,
        status="insufficient_data",
        passed=False,
        explanation=reason,
        metrics=metrics,
    )


def _validated_history(df: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"datetime", "open", "high", "low", "close", "volume", "symbol"}
    if df.empty or not required_columns.issubset(df.columns):
        return pd.DataFrame(columns=sorted(required_columns))

    history = df.copy().sort_values("datetime").reset_index(drop=True)
    numeric_columns = ["open", "high", "low", "close", "volume"]
    for column in numeric_columns:
        history[column] = pd.to_numeric(history[column], errors="coerce")
    return history.dropna(subset=["datetime", "open", "high", "low", "close", "volume"])


def breakout_above_n_day_high(df: pd.DataFrame, n: int = 20) -> SignalResult:
    """Return the latest breakout status versus the previous n-day high."""

    history = _validated_history(df)
    if len(history) < n + 1:
        return _insufficient_signal(
            f"breakout_{n}",
            f"Need at least {n + 1} rows to evaluate an {n}-day breakout.",
            lookback=n,
            rows_available=len(history),
        )

    prior_high = history["high"].shift(1).rolling(window=n, min_periods=n).max()
    latest = history.iloc[-1]
    breakout_level = float(prior_high.iloc[-1])
    close = float(latest["close"])
    distance_pct = ((close / breakout_level) - 1.0) * 100 if breakout_level else np.nan

    if np.isnan(distance_pct):
        return _insufficient_signal(
            f"breakout_{n}",
            "Breakout level could not be computed safely.",
            lookback=n,
            breakout_level=None,
        )

    passed = close > breakout_level
    near_breakout = not passed and distance_pct >= -2.0
    status = "breakout" if passed else "near_breakout" if near_breakout else "below_breakout"
    explanation = (
        f"Close is {distance_pct:.2f}% above the prior {n}-day high."
        if passed
        else f"Close is {abs(distance_pct):.2f}% below the prior {n}-day high."
    )

    return SignalResult(
        name=f"breakout_{n}",
        status=status,
        passed=passed,
        explanation=explanation,
        metrics={
            "lookback": n,
            "breakout_level": round(breakout_level, 4),
            "close": round(close, 4),
            "distance_pct": round(distance_pct, 4),
            "near_breakout": near_breakout,
        },
    )


def volume_spike(df: pd.DataFrame, lookback: int = 20, multiple: float = 1.5) -> SignalResult:
    """Return the latest volume confirmation versus the recent average volume."""

    history = _validated_history(df)
    if len(history) < lookback + 1:
        return _insufficient_signal(
            "volume_spike",
            f"Need at least {lookback + 1} rows to evaluate volume confirmation.",
            lookback=lookback,
            rows_available=len(history),
        )

    average_volume = float(history["volume"].shift(1).rolling(lookback, min_periods=lookback).mean().iloc[-1])
    latest_volume = float(history["volume"].iloc[-1])
    volume_multiple = latest_volume / average_volume if average_volume else np.nan

    if np.isnan(volume_multiple):
        return _insufficient_signal(
            "volume_spike",
            "Average volume could not be computed safely.",
            lookback=lookback,
            average_volume=None,
        )

    passed = volume_multiple >= multiple
    status = "confirmed" if passed else "normal" if volume_multiple >= 1.0 else "weak"
    explanation = (
        f"Volume is running at {volume_multiple:.2f}x the {lookback}-day average."
    )

    return SignalResult(
        name="volume_spike",
        status=status,
        passed=passed,
        explanation=explanation,
        metrics={
            "lookback": lookback,
            "average_volume": round(average_volume, 2),
            "latest_volume": round(latest_volume, 2),
            "volume_multiple": round(volume_multiple, 4),
            "threshold_multiple": multiple,
        },
    )


def moving_average_filter(df: pd.DataFrame, short: int = 50, long: int = 200) -> SignalResult:
    """Return the latest moving-average trend alignment signal."""

    history = _validated_history(df)
    if len(history) < long:
        return _insufficient_signal(
            "moving_average_filter",
            f"Need at least {long} rows to evaluate the {short}/{long} DMA filter.",
            short_window=short,
            long_window=long,
            rows_available=len(history),
        )

    short_ma = float(history["close"].rolling(short, min_periods=short).mean().iloc[-1])
    long_ma = float(history["close"].rolling(long, min_periods=long).mean().iloc[-1])
    close = float(history["close"].iloc[-1])
    above_short = close > short_ma
    above_long = close > long_ma
    short_above_long = short_ma > long_ma
    passed = above_short and above_long and short_above_long

    if passed:
        status = "trend_aligned"
    elif above_long:
        status = "mixed"
    else:
        status = "weak"

    explanation = (
        f"Close is {'above' if above_short else 'below'} the {short} DMA and "
        f"{'above' if above_long else 'below'} the {long} DMA."
    )

    return SignalResult(
        name="moving_average_filter",
        status=status,
        passed=passed,
        explanation=explanation,
        metrics={
            "short_window": short,
            "long_window": long,
            "close": round(close, 4),
            "short_ma": round(short_ma, 4),
            "long_ma": round(long_ma, 4),
            "above_short_ma": above_short,
            "above_long_ma": above_long,
            "short_above_long": short_above_long,
        },
    )


def atr_expansion(
    df: pd.DataFrame,
    atr_lookback: int = 14,
    threshold_ratio: float = 1.2,
) -> SignalResult:
    """Return the latest ATR expansion or compression status."""

    history = _validated_history(df)
    if len(history) < atr_lookback * 2:
        return _insufficient_signal(
            "atr_expansion",
            f"Need at least {atr_lookback * 2} rows to evaluate ATR expansion.",
            atr_lookback=atr_lookback,
            rows_available=len(history),
        )

    previous_close = history["close"].shift(1)
    tr_components = pd.concat(
        [
            history["high"] - history["low"],
            (history["high"] - previous_close).abs(),
            (history["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    true_range = tr_components.max(axis=1)
    atr = true_range.rolling(atr_lookback, min_periods=atr_lookback).mean()
    latest_atr = float(atr.iloc[-1])
    atr_baseline = float(atr.shift(1).rolling(atr_lookback, min_periods=atr_lookback).mean().iloc[-1])
    atr_ratio = latest_atr / atr_baseline if atr_baseline else np.nan

    if np.isnan(atr_ratio):
        return _insufficient_signal(
            "atr_expansion",
            "ATR baseline could not be computed safely.",
            atr_lookback=atr_lookback,
            atr=None,
        )

    expanding = atr_ratio >= threshold_ratio
    compressed = atr_ratio <= 0.85
    status = "expanding" if expanding else "compressed" if compressed else "normal"
    explanation = f"ATR is at {atr_ratio:.2f}x its recent baseline."

    return SignalResult(
        name="atr_expansion",
        status=status,
        passed=expanding,
        explanation=explanation,
        metrics={
            "atr_lookback": atr_lookback,
            "latest_atr": round(latest_atr, 4),
            "atr_baseline": round(atr_baseline, 4),
            "atr_ratio": round(atr_ratio, 4),
            "threshold_ratio": threshold_ratio,
            "compressed": compressed,
        },
    )


def relative_strength_vs_benchmark(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    lookback: int = 20,
) -> SignalResult:
    """Return the latest relative-strength signal versus a benchmark."""

    stock_history = _validated_history(stock_df)
    benchmark_history = _validated_history(benchmark_df)
    if len(stock_history) < lookback + 1 or len(benchmark_history) < lookback + 1:
        return _insufficient_signal(
            "relative_strength",
            f"Need at least {lookback + 1} rows in both series for relative strength.",
            lookback=lookback,
            stock_rows=len(stock_history),
            benchmark_rows=len(benchmark_history),
        )

    stock_return = (float(stock_history["close"].iloc[-1]) / float(stock_history["close"].iloc[-lookback - 1]) - 1.0) * 100
    benchmark_return = (
        float(benchmark_history["close"].iloc[-1]) / float(benchmark_history["close"].iloc[-lookback - 1]) - 1.0
    ) * 100
    rs_spread = stock_return - benchmark_return
    status = "outperforming" if rs_spread > 2.0 else "inline" if rs_spread >= 0 else "lagging"
    explanation = (
        f"Stock return is {stock_return:.2f}% versus benchmark return of {benchmark_return:.2f}% "
        f"over the last {lookback} sessions."
    )

    return SignalResult(
        name="relative_strength",
        status=status,
        passed=rs_spread >= 0,
        explanation=explanation,
        metrics={
            "lookback": lookback,
            "stock_return_pct": round(stock_return, 4),
            "benchmark_return_pct": round(benchmark_return, 4),
            "relative_strength_spread_pct": round(rs_spread, 4),
        },
    )


def combine_latest_signals(
    symbol: str,
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame | None = None,
    *,
    sector: str | None = None,
    market_cap_bucket: str | None = None,
) -> dict[str, Any]:
    """Combine the latest breakout signals for one stock into a reusable dictionary."""

    history = _validated_history(stock_df)
    if history.empty:
        return {
            "symbol": symbol,
            "status": "no_data",
            "signal_state": "watch",
            "sector": sector or "Unknown",
            "market_cap_bucket": market_cap_bucket or "Unknown",
        }

    breakout_20 = breakout_above_n_day_high(history, n=20)
    breakout_55 = breakout_above_n_day_high(history, n=55)
    volume = volume_spike(history, lookback=20, multiple=1.5)
    trend = moving_average_filter(history, short=50, long=200)
    atr = atr_expansion(history, atr_lookback=14, threshold_ratio=1.2)
    rs = (
        relative_strength_vs_benchmark(history, benchmark_df, lookback=20)
        if benchmark_df is not None and not benchmark_df.empty
        else _insufficient_signal("relative_strength", "Benchmark data not supplied.")
    )

    close = float(history["close"].iloc[-1])
    as_of = pd.to_datetime(history["datetime"].iloc[-1]).to_pydatetime()
    average_turnover_20 = float((history["close"] * history["volume"]).tail(20).mean()) if len(history) >= 20 else 0.0
    liquidity_status = (
        "high"
        if average_turnover_20 >= 500_000_000
        else "medium"
        if average_turnover_20 >= 100_000_000
        else "low"
    )
    primary_breakout_level = (
        breakout_55.metrics.get("breakout_level")
        if breakout_55.passed
        else breakout_20.metrics.get("breakout_level")
    )
    distance_above_breakout_pct = (
        breakout_55.metrics.get("distance_pct")
        if breakout_55.passed
        else breakout_20.metrics.get("distance_pct")
    )
    volume_multiple = volume.metrics.get("volume_multiple")

    recent_breakout_level = history["high"].shift(1).rolling(window=20, min_periods=20).max()
    recent_breakout_flags = history["close"] > recent_breakout_level
    failed_breakout = bool(recent_breakout_flags.shift(1, fill_value=False).tail(5).any()) and not breakout_20.passed

    if failed_breakout:
        signal_state = "failed_breakout"
    elif breakout_20.passed or breakout_55.passed:
        signal_state = "breakout"
    elif bool(breakout_20.metrics.get("near_breakout")):
        signal_state = "near_breakout"
    else:
        signal_state = "watch"

    return {
        "symbol": symbol,
        "as_of": as_of,
        "close": round(close, 4),
        "status": "ready",
        "signal_state": signal_state,
        "sector": sector or "Unknown",
        "market_cap_bucket": market_cap_bucket or "Unknown",
        "breakout_20": breakout_20.to_dict(),
        "breakout_55": breakout_55.to_dict(),
        "volume": volume.to_dict(),
        "trend": trend.to_dict(),
        "atr": atr.to_dict(),
        "relative_strength": rs.to_dict(),
        "breakout_level": primary_breakout_level,
        "distance_above_breakout_pct": distance_above_breakout_pct,
        "volume_multiple": volume_multiple,
        "dma_50_status": "above" if trend.metrics.get("above_short_ma") else "below",
        "dma_200_status": "above" if trend.metrics.get("above_long_ma") else "below",
        "atr_status": atr.status,
        "relative_strength_status": rs.status,
        "liquidity_turnover_20": round(average_turnover_20, 2),
        "liquidity_status": liquidity_status,
        "failed_breakout": failed_breakout,
    }
