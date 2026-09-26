"""Data QA, computed point-in-time: the pass mask at date T uses bars dated <= T only.

Checks (thresholds per segment in config; MICRO250 is stricter):
  insufficient_history  bars so far < qa.min_bars
  missing_sessions      share of NSE sessions without a bar in the last
                        qa.lookback_sessions (counted from the first bar) > qa.max_missing_pct
  zero_volume           zero/null-volume bars in the window > qa.max_zero_volume_days
  big_move              |close / previous bar close - 1| > qa.big_move_threshold;
                        excluded if count in window > qa.max_big_moves (null = flag only)
  no_data               in the universe but no bars at all
  stale (info)          no bar on the latest session

The live scan uses the last row of the same mask the backtest uses, so both apply
identical rules. `issues` holds the rows for the `data_quality` table as of the
latest session; a symbol is excluded exactly when it has a blocking row.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import SEGMENTS, Config
from .panel import Panel, panel_from_store

ISSUE_COLUMNS = ["symbol", "date", "segment", "issue", "blocking", "detail"]


@dataclass
class QAResult:
    metrics: dict[str, pd.DataFrame]
    passed: pd.DataFrame  # bool (dates x symbols)
    issues: pd.DataFrame
    summary: pd.DataFrame
    asof: pd.Timestamp


def qa_metrics(panel: Panel, cfg: Config) -> dict[str, pd.DataFrame]:
    window = int(cfg["qa.lookback_sessions"])
    has = panel.has_bar
    listed = has.cummax()  # on or after the first bar
    expected = listed.rolling(window, min_periods=1).sum()
    present = has.rolling(window, min_periods=1).sum()
    missing_pct = ((expected - present) / expected.where(expected > 0)).fillna(0.0)
    zero = has & panel.volume.fillna(0).eq(0)
    prev_close = panel.close.ffill().shift(1)
    ret = (panel.close / prev_close - 1.0).where(has)
    big = has & ret.abs().gt(float(cfg["qa.big_move_threshold"]))
    return {
        "bars": has.cumsum(),
        "missing_pct": missing_pct,
        "missing_n": expected - present,
        "expected_n": expected,
        "zero": zero,
        "zero_n": zero.rolling(window, min_periods=1).sum(),
        "ret": ret,
        "big": big,
        "big_n": big.rolling(window, min_periods=1).sum(),
    }


def qa_fail_masks(panel: Panel, metrics: dict[str, pd.DataFrame], cfg: Config) -> dict[str, pd.DataFrame]:
    """Per check: True where the check blocks the symbol on that date."""

    fails = {name: pd.DataFrame(False, index=panel.dates, columns=panel.symbols) for name in
             ("insufficient_history", "missing_sessions", "zero_volume", "big_move")}
    for segment in SEGMENTS:
        cols = panel.symbols_in(segment)
        fails["insufficient_history"][cols] = metrics["bars"][cols].lt(int(cfg.seg("qa.min_bars", segment)))
        fails["missing_sessions"][cols] = metrics["missing_pct"][cols].gt(float(cfg.seg("qa.max_missing_pct", segment)))
        fails["zero_volume"][cols] = metrics["zero_n"][cols].gt(int(cfg.seg("qa.max_zero_volume_days", segment)))
        max_big = cfg.seg("qa.max_big_moves", segment)
        if max_big is not None:
            fails["big_move"][cols] = metrics["big_n"][cols].gt(int(max_big))
    return fails


def qa_pass_mask(panel: Panel, cfg: Config, metrics: dict[str, pd.DataFrame] | None = None) -> pd.DataFrame:
    metrics = metrics or qa_metrics(panel, cfg)
    fails = qa_fail_masks(panel, metrics, cfg)
    blocked = fails["insufficient_history"] | fails["missing_sessions"] | fails["zero_volume"] | fails["big_move"]
    return panel.has_bar & ~blocked


def _row(symbol: str, date: pd.Timestamp, segment: str, issue: str, blocking: bool, **detail) -> dict:
    return {
        "symbol": symbol,
        "date": pd.Timestamp(date).date().isoformat(),
        "segment": segment,
        "issue": issue,
        "blocking": bool(blocking),
        "detail": json.dumps(detail, default=float),
    }


def latest_issues(panel: Panel, metrics: dict[str, pd.DataFrame], cfg: Config, universe: pd.DataFrame) -> pd.DataFrame:
    asof = panel.dates[-1]
    window = int(cfg["qa.lookback_sessions"])
    recent = panel.dates[-window:]
    fails = {name: frame.loc[asof] for name, frame in qa_fail_masks(panel, metrics, cfg).items()}
    rows: list[dict] = []
    for symbol in sorted(set(universe["symbol"]) - set(panel.symbols)):
        segment = universe.set_index("symbol").at[symbol, "segment"]
        rows.append(_row(symbol, asof, segment, "no_data", True))
    for symbol in panel.symbols:
        segment = panel.segment[symbol]
        bars = int(metrics["bars"].at[asof, symbol])
        if fails["insufficient_history"][symbol]:
            rows.append(_row(symbol, asof, segment, "insufficient_history", True, bars=bars,
                             min_bars=int(cfg.seg("qa.min_bars", segment))))
        if metrics["missing_n"].at[asof, symbol] > 0 and fails["missing_sessions"][symbol]:
            missing_dates = panel.has_bar.loc[recent, symbol]
            missing_dates = missing_dates.index[~missing_dates & panel.has_bar[symbol].cummax().loc[recent]]
            rows.append(_row(symbol, asof, segment, "missing_sessions", True,
                             missing_pct=round(float(metrics["missing_pct"].at[asof, symbol]), 4),
                             missing=int(metrics["missing_n"].at[asof, symbol]),
                             expected=int(metrics["expected_n"].at[asof, symbol]),
                             last_missing=[d.date().isoformat() for d in missing_dates[-5:]]))
        zero_dates = recent[metrics["zero"].loc[recent, symbol].to_numpy()]
        for day in zero_dates:
            rows.append(_row(symbol, day, segment, "zero_volume", fails["zero_volume"][symbol],
                             count_in_window=int(metrics["zero_n"].at[asof, symbol]),
                             max_allowed=int(cfg.seg("qa.max_zero_volume_days", segment))))
        big_dates = recent[metrics["big"].loc[recent, symbol].to_numpy()]
        for day in big_dates:
            prev = panel.close[symbol].loc[:day].dropna()
            rows.append(_row(symbol, day, segment, "big_move", fails["big_move"][symbol],
                             ret=round(float(metrics["ret"].at[day, symbol]), 4),
                             prev_close=float(prev.iloc[-2]) if len(prev) > 1 else None,
                             close=float(panel.close.at[day, symbol])))
        if not panel.has_bar.at[asof, symbol] and bars:
            last_bar = panel.has_bar[symbol][panel.has_bar[symbol]].index.max()
            rows.append(_row(symbol, asof, segment, "stale", False, last_bar=last_bar.date().isoformat()))
    issues = pd.DataFrame(rows, columns=ISSUE_COLUMNS)
    return issues.sort_values(["segment", "symbol", "date", "issue"]).reset_index(drop=True)


def summarize(panel: Panel, passed_now: pd.Series, issues: pd.DataFrame, universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for segment in SEGMENTS:
        seg_universe = universe.loc[universe["segment"].eq(segment), "symbol"]
        seg_issues = issues.loc[issues["segment"].eq(segment)]
        blocking = seg_issues.loc[seg_issues["blocking"]]
        row = {
            "segment": segment,
            "universe": len(seg_universe),
            "with_data": int(panel.segment.eq(segment).sum()),
            "qa_pass_today": int(passed_now[panel.symbols_in(segment)].sum()),
            "excluded": int(blocking["symbol"].nunique()),
        }
        for issue in ("no_data", "insufficient_history", "missing_sessions", "zero_volume", "big_move", "stale"):
            row[f"sym_{issue}"] = int(seg_issues.loc[seg_issues["issue"].eq(issue), "symbol"].nunique())
            row[f"blk_{issue}"] = int(blocking.loc[blocking["issue"].eq(issue), "symbol"].nunique())
        rows.append(row)
    return pd.DataFrame(rows).set_index("segment")


def run_qa(store, cfg: Config, panel: Panel | None = None) -> QAResult:
    panel = panel or panel_from_store(store, cfg)
    universe = store.read_universe()
    metrics = qa_metrics(panel, cfg)
    passed = qa_pass_mask(panel, cfg, metrics)
    issues = latest_issues(panel, metrics, cfg, universe)
    asof = panel.dates[-1]
    # consistency: excluded today <=> has a blocking issue row (symbols with a bar today)
    blocked_rows = set(issues.loc[issues["blocking"], "symbol"])
    with_bar = panel.has_bar.loc[asof]
    excluded_mask = set(with_bar.index[with_bar & ~passed.loc[asof]])
    if excluded_mask - blocked_rows:
        raise AssertionError(f"QA mask excludes symbols without blocking rows: {sorted(excluded_mask - blocked_rows)}")
    summary = summarize(panel, passed.loc[asof], issues, universe)
    return QAResult(metrics=metrics, passed=passed, issues=issues, summary=summary, asof=asof)
