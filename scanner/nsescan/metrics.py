"""Trade metrics, breakdowns and month-block bootstrap confidence intervals.

Every figure is computed from closed trades (right-censored OPEN trades excluded),
equal weight per trade, net of the cost and slippage assumptions in config.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

PCTS = (10, 25, 50, 75, 90)
EXIT_REASONS = ("STOP", "STOP_GAP", "BREAKEVEN_STOP", "BREAKEVEN_STOP_GAP", "FAILED_BREAKOUT", "TRAIL_EMA", "STALL",
                "TIME", "TARGET")


def _pct(series: pd.Series) -> dict[str, float]:
    values = series.dropna().to_numpy()
    if not len(values):
        return {f"p{q}": None for q in PCTS}
    return {f"p{q}": float(np.percentile(values, q)) for q in PCTS}


def trade_metrics(trades: pd.DataFrame) -> dict[str, Any]:
    """Headline metrics for closed trades (rows with status == CLOSED)."""

    closed = trades.loc[trades["status"].eq("CLOSED")]
    n = len(closed)
    if n == 0:
        return {"n": 0}
    ret, r = closed["ret_net"], closed["r_net"]
    wins, losses = ret > 0, ret <= 0
    gross_win, gross_loss = ret[wins].sum(), -ret[losses].sum()
    labelled = closed["label"].dropna()
    touched = closed["touched_upper"].dropna()
    months = closed["signal_date"].dt.to_period("M").nunique()
    return {
        "n": int(n),
        "months": int(months),
        "trades_per_month": float(n / months) if months else None,
        "win_rate": float(wins.mean()),
        "avg_win_r": float(r[wins].mean()) if wins.any() else None,
        "avg_loss_r": float(r[losses].mean()) if losses.any() else None,
        "avg_win_pct": float(ret[wins].mean()) if wins.any() else None,
        "avg_loss_pct": float(ret[losses].mean()) if losses.any() else None,
        "expectancy_r": float(r.mean()),
        "expectancy_pct": float(ret.mean()),
        "expectancy_pct_gross": float(closed["ret_gross"].mean()),
        "median_stop_pct": float(closed["stop_pct_entry"].median()),
        "median_ret_pct": float(ret.median()),
        "profit_factor": float(gross_win / gross_loss) if gross_loss > 0 else None,
        "hit_upper_first": float((labelled == 1).mean()) if len(labelled) else None,
        "hit_lower_first": float((labelled == -1).mean()) if len(labelled) else None,
        "vertical_first": float((labelled == 0).mean()) if len(labelled) else None,
        "touched_upper_20": float(touched.mean()) if len(touched) else None,
        "avg_sessions": float(closed["sessions"].mean()),
        "exit_mix": {k: float(v) for k, v in closed["exit_reason"].value_counts(normalize=True).items()},
        "mfe_pct": _pct(closed["mfe_pct"]),
        "mae_pct": _pct(closed["mae_pct"]),
        "mfe_r": _pct(closed["mfe_pct"] * closed["entry_fill"] / (closed["entry_fill"] - closed["stop"])),
        "mae_r": _pct(closed["mae_pct"] * closed["entry_fill"] / (closed["entry_fill"] - closed["stop"])),
    }


def bootstrap_ci(trades: pd.DataFrame, reps: int, seed: int, level: float = 0.95) -> dict[str, list[float]]:
    """Percentile CIs for expectancy (R, %) and hit rate, resampling calendar months of
    signal dates with replacement (trades in the same month move together)."""

    closed = trades.loc[trades["status"].eq("CLOSED")]
    if closed.empty:
        return {}
    month = closed["signal_date"].dt.to_period("M")
    grouped = pd.DataFrame({
        "n": closed.groupby(month).size(),
        "sum_r": closed.groupby(month)["r_net"].sum(),
        "sum_ret": closed.groupby(month)["ret_net"].sum(),
        "n_lab": closed.groupby(month)["label"].count(),
        "n_hit": closed.assign(hit=closed["label"].eq(1)).groupby(month)["hit"].sum(),
    })
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(grouped), size=(reps, len(grouped)))
    values = grouped.to_numpy(dtype=float)
    sums = values[idx].sum(axis=1)  # reps x columns
    n, sum_r, sum_ret, n_lab, n_hit = sums.T
    alpha = (1.0 - level) / 2.0

    def ci(x: np.ndarray) -> list[float]:
        return [float(np.nanquantile(x, alpha)), float(np.nanquantile(x, 1.0 - alpha))]

    with np.errstate(invalid="ignore", divide="ignore"):
        return {"expectancy_r": ci(sum_r / n), "expectancy_pct": ci(sum_ret / n), "hit_upper_first": ci(n_hit / n_lab)}


def breakdown(trades: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    """Compact per-group table (closed trades)."""

    closed = trades.loc[trades["status"].eq("CLOSED")]
    rows = []
    for key, group in closed.groupby(by, observed=True):
        m = trade_metrics(group)
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(by, key)), "n": m["n"], "win_rate": m["win_rate"], "expectancy_r": m["expectancy_r"],
                     "expectancy_pct": m["expectancy_pct"], "profit_factor": m["profit_factor"],
                     "hit_upper_first": m["hit_upper_first"], "touched_upper_20": m["touched_upper_20"],
                     "avg_win_r": m["avg_win_r"], "avg_loss_r": m["avg_loss_r"]})
    return pd.DataFrame(rows)
