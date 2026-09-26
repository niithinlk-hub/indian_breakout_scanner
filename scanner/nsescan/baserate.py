"""Benchmark (a): random entries on names passing only the liquidity gate.

Every (symbol, day T) that passes data QA and the liquidity gate is an entry, which
is the exact expectation of drawing entry dates uniformly at random (no sampling
noise). The trade plan is section 4 with the analogs a random entry needs:
  * stop = min(low of T, lowest low of the 5 sessions before T)
    (`plan.stop_base_lookback`; day T stands in for the breakout day);
  * no failed-breakout exit, because a random entry has no pivot;
  * every other rule, cost and slippage assumption exactly as in `simulate`.
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .config import SEGMENTS, Config
from .gates import liquidity_gate
from .metrics import bootstrap_ci, breakdown, trade_metrics
from .panel import Panel, panel_from_store
from .qa import qa_metrics, qa_pass_mask
from .regime import compute_regime
from .simulate import PlanParams, Trade, ema_series, simulate_trade

LOGGER = logging.getLogger(__name__)
TRADE_FIELDS = list(Trade._fields)


def simulate_events(panel: Panel, events: pd.DataFrame, cfg: Config, big: pd.DataFrame) -> pd.DataFrame:
    """Simulate events (symbol, signal_date, stop, pivot) with the section-4 plan."""

    params = {segment: PlanParams.from_config(cfg, segment) for segment in SEGMENTS}
    span = int(cfg["plan.trail_ema"])
    frames = []
    for symbol, group in events.groupby("symbol", sort=True):
        has = panel.has_bar[symbol].to_numpy()
        dates = panel.dates[has]
        o = panel.open[symbol].to_numpy()[has].tolist()
        h = panel.high[symbol].to_numpy()[has].tolist()
        l = panel.low[symbol].to_numpy()[has].tolist()
        c_arr = panel.close[symbol].to_numpy()[has]
        c = c_arr.tolist()
        trail = ema_series(c_arr, span).tolist()
        bigs = big[symbol].to_numpy()[has].tolist()
        position = pd.Series(np.arange(len(dates)), index=dates)
        ts = position.reindex(pd.DatetimeIndex(group["signal_date"])).to_numpy()
        plan = params[panel.segment[symbol]]
        pivots = group["pivot"].to_numpy() if "pivot" in group else np.full(len(group), np.nan)
        rows = []
        for t, stop, pivot in zip(ts, group["stop"].to_numpy(), pivots):
            rows.append(simulate_trade(o, h, l, c, trail, bigs, int(t), float(stop),
                                       None if np.isnan(pivot) else float(pivot), plan))
        frame = pd.DataFrame(rows, columns=TRADE_FIELDS)
        frame.insert(0, "symbol", symbol)
        frame.insert(1, "segment", panel.segment[symbol])
        frame.insert(2, "industry", panel.industry[symbol])
        frame.insert(3, "signal_date", dates[frame["signal_idx"].to_numpy()])
        frame["entry_date"] = [dates[i] if i >= 0 else pd.NaT for i in frame["entry_idx"]]
        frame["exit_date"] = [dates[i] if i >= 0 else pd.NaT for i in frame["exit_idx"]]
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["symbol", *TRADE_FIELDS])


def base_rate_events(panel: Panel, eligible: pd.DataFrame, cfg: Config, start: pd.Timestamp | None,
                     end: pd.Timestamp | None) -> pd.DataFrame:
    lookback = int(cfg["plan.stop_base_lookback"])
    parts = []
    for symbol in panel.symbols:
        has = panel.has_bar[symbol].to_numpy()
        dates = panel.dates[has]
        lows = pd.Series(panel.low[symbol].to_numpy()[has])
        stop = lows.rolling(lookback + 1, min_periods=lookback + 1).min().to_numpy()  # T and the N bars before
        ok = eligible[symbol].to_numpy()[has] & ~np.isnan(stop)
        if start is not None:
            ok &= dates >= start
        if end is not None:
            ok &= dates <= end
        if ok.any():
            parts.append(pd.DataFrame({"symbol": symbol, "signal_date": dates[ok], "stop": stop[ok], "pivot": np.nan}))
    return pd.concat(parts, ignore_index=True)


def _git_sha() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_baserate(store, cfg: Config, out_dir: Path, start: str | None = None, end: str | None = None) -> list[Path]:
    from .reports import baserate_markdown

    panel = panel_from_store(store, cfg)
    metrics = qa_metrics(panel, cfg)
    qa_ok = qa_pass_mask(panel, cfg, metrics)
    liq = liquidity_gate(panel, cfg)
    eligible = qa_ok & liq.passed
    regime = compute_regime(panel, store.read_benchmarks(), cfg)
    events = base_rate_events(panel, eligible, cfg, pd.Timestamp(start) if start else None,
                              pd.Timestamp(end) if end else None)
    LOGGER.info("simulating %d base-rate entries", len(events))
    trades = simulate_events(panel, events, cfg, metrics["big"])
    trades["year"] = trades["signal_date"].dt.year
    trades["regime"] = regime["state"].reindex(trades["signal_date"]).to_numpy()

    seed, reps = int(cfg["backtest.seed"]), int(cfg["backtest.bootstrap_reps"])
    result: dict[str, Any] = {"segments": {}, "sensitivity_excl_big_move": {}, "skips": {}, "eligible_per_day": {}}
    for segment in SEGMENTS:
        seg = trades.loc[trades["segment"].eq(segment)]
        headline = trade_metrics(seg)
        headline["ci95"] = bootstrap_ci(seg, reps, seed)
        result["segments"][segment] = headline
        result["sensitivity_excl_big_move"][segment] = {
            "excluded_trades": int((seg["status"].eq("CLOSED") & seg["spans_big_move"]).sum()),
            **{k: v for k, v in trade_metrics(seg.loc[~seg["spans_big_move"]]).items()
               if k in ("n", "expectancy_r", "expectancy_pct", "win_rate", "hit_upper_first")},
        }
        result["skips"][segment] = {
            "entries_considered": int(len(seg)),
            "closed": int(seg["status"].eq("CLOSED").sum()),
            "open_censored": int(seg["status"].eq("OPEN").sum()),
            **{k: int(v) for k, v in seg.loc[seg["status"].eq("SKIPPED"), "skip_reason"].value_counts().items()},
        }
        cols = panel.symbols_in(segment)
        per_day = eligible[cols].sum(axis=1)
        per_day = per_day.loc[per_day.index >= trades["signal_date"].min()]
        result["eligible_per_day"][segment] = {int(y): float(v) for y, v in per_day.groupby(per_day.index.year).mean().items()}
    trades["stop_bucket"] = pd.cut(trades["stop_pct_entry"], [0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08],
                                   labels=["0-1%", "1-2%", "2-3%", "3-4%", "4-5%", "5-6%", "6-8%"])
    by_stop = breakdown(trades, ["segment", "stop_bucket"])
    result["by_stop_distance"] = by_stop.to_dict(orient="records")
    by_year = breakdown(trades, ["segment", "year"])
    by_regime = breakdown(trades, ["segment", "regime"])
    result["by_year"] = by_year.to_dict(orient="records")
    result["by_regime"] = by_regime.to_dict(orient="records")

    data_asof = panel.dates[-1].date().isoformat()
    window = [trades["signal_date"].min().date().isoformat(), trades["signal_date"].max().date().isoformat()]
    params = {"config": cfg.snapshot(), "window": window, "data_asof": data_asof,
              "definition": "all QA+liquidity-eligible (symbol, day) entries; stop=min(low T..T-5); no pivot exit"}
    git_sha = _git_sha()
    report = baserate_markdown(result, by_year, by_regime, by_stop, cfg, window, data_asof, git_sha)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "step2_baserate.md"
    json_path = out_dir / "step2_baserate.json"
    md_path.write_text(report, encoding="utf-8")
    json_path.write_text(json.dumps({"params": {k: v for k, v in params.items() if k != "config"},
                                     "config_hash": cfg.hash, "git_sha": git_sha, "metrics": result},
                                    indent=1, default=str), encoding="utf-8")
    store.save_backtest_run("baserate", params, result, report, cfg.hash, data_asof, git_sha)
    if hasattr(store, "root"):
        trades.drop(columns=["stop_bucket"]).to_parquet(store.root / "baserate_trades.parquet", index=False)
    return [md_path, json_path]
