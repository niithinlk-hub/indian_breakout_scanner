from __future__ import annotations

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").ewm(span=span, adjust=False).mean()


def _rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = pd.to_numeric(series, errors="coerce").diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    return 100 - (100 / (1 + rs))


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    previous_close = pd.to_numeric(frame["close"], errors="coerce").shift(1)
    true_range = pd.concat(
        [
            pd.to_numeric(frame["high"], errors="coerce") - pd.to_numeric(frame["low"], errors="coerce"),
            (pd.to_numeric(frame["high"], errors="coerce") - previous_close).abs(),
            (pd.to_numeric(frame["low"], errors="coerce") - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def _adx(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    high = pd.to_numeric(frame["high"], errors="coerce")
    low = pd.to_numeric(frame["low"], errors="coerce")
    close = pd.to_numeric(frame["close"], errors="coerce")
    plus_dm = (high.diff()).where((high.diff() > low.shift(1) - low) & (high.diff() > 0), 0.0)
    minus_dm = (low.shift(1) - low).where((low.shift(1) - low > high.diff()) & (low.shift(1) - low > 0), 0.0)

    previous_close = close.shift(1)
    tr = pd.concat([(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(alpha=1 / window, min_periods=window, adjust=False).mean() / atr.replace(0.0, pd.NA))
    minus_di = 100 * (minus_dm.ewm(alpha=1 / window, min_periods=window, adjust=False).mean() / atr.replace(0.0, pd.NA))
    dx = ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, pd.NA)) * 100
    return dx.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()


def calculate_indicators(df: pd.DataFrame, benchmark_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Calculate trend, momentum, volume, and relative-strength indicators."""

    frame = df.copy().sort_values("datetime").reset_index(drop=True)
    frame["ema20"] = _ema(frame["close"], 20)
    frame["ema50"] = _ema(frame["close"], 50)
    frame["rsi14"] = _rsi(frame["close"], 14)
    frame["atr14"] = _atr(frame, 14)
    frame["adx14"] = _adx(frame, 14)
    frame["volume_sma20"] = pd.to_numeric(frame["volume"], errors="coerce").rolling(20, min_periods=20).mean()
    frame["atr14_sma20"] = frame["atr14"].rolling(20, min_periods=20).mean()
    frame["relative_volume"] = pd.to_numeric(frame["volume"], errors="coerce") / frame["volume_sma20"].replace(0.0, pd.NA)

    if benchmark_df is not None and not benchmark_df.empty and len(frame) >= 21 and len(benchmark_df) >= 21:
        benchmark = benchmark_df.copy().sort_values("datetime").reset_index(drop=True)
        stock_return = pd.to_numeric(frame["close"], errors="coerce").pct_change(20)
        benchmark_return = pd.to_numeric(benchmark["close"], errors="coerce").pct_change(20)
        aligned_benchmark = benchmark_return.reindex(range(len(stock_return))).ffill()
        frame["relative_strength_spread"] = (stock_return - aligned_benchmark) * 100.0
    else:
        frame["relative_strength_spread"] = pd.NA
    return frame
