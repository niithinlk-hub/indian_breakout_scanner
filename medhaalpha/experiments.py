"""Experiment plans (blueprint §9 sequence) and the walk-forward selection logic."""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from medhaalpha.config import DEV_END, HOLDOUT_START, STUDY_END, STUDY_START, WALK_FORWARD
from medhaalpha.metrics import non_overlapping, standalone_net, summarize
from medhaalpha.research import INTRADAY_COMBOS, RunSpec
from medhaalpha.signals import EntrySpec
from medhaalpha.simulate import ExitSpec

THRS = (0, 60, 70, 80)
REF_EXIT = ExitSpec()  # structure stop, 2R target, time exit


def entry_grid() -> list[EntrySpec]:
    out = [EntrySpec("A0")]
    out += [EntrySpec("A", thr=t) for t in THRS]
    out += [EntrySpec("B", thr=t) for t in THRS]
    out += [EntrySpec("C", thr=t, n=n) for n in (10, 15, 20) for t in THRS]
    return out


def stage1_plan(include_3m: bool = True) -> list[RunSpec]:
    """Entry study with the common reference exit (structure stop + 2R + time exit)."""
    plan = []
    combos = [c for c in INTRADAY_COMBOS if include_3m or c[0] != 3]
    for (stf, ctf), e, side in itertools.product(combos, entry_grid(), (1, -1)):
        plan.append(RunSpec("intraday", f"{stf}/{ctf}", e, side, REF_EXIT))
    for (stf, ctf), thr, side in itertools.product(combos, (0, 60, 70), (1, -1)):
        plan.append(RunSpec("intraday", f"{stf}/{ctf}", EntrySpec("ADAPT", thr=thr, n=15), side, REF_EXIT, adaptive=True))
    # random-entry control benchmark (same windows, stops and exits) — ~1 entry per stock per day
    for (stf, ctf), side in itertools.product(combos, (1, -1)):
        bars_per_day = {3: 125, 5: 75, 15: 25}[stf]
        plan.append(RunSpec("intraday", f"{stf}/{ctf}", EntrySpec("RAND", p=1.0 / bars_per_day), side, REF_EXIT))
    # positional: 60-minute entries gated by the prior session's daily trend score
    pos_entries = [EntrySpec("A"), EntrySpec("B"), EntrySpec("C", n=10), EntrySpec("C", n=15), EntrySpec("C", n=20)]
    for e, dthr, side in itertools.product(pos_entries, THRS, (1, -1)):
        plan.append(RunSpec("positional", "60/D", e, side, REF_EXIT, daily_thr=dthr))
    for dthr, side in itertools.product((0, 60, 70), (1, -1)):
        plan.append(RunSpec("positional", "60/D", EntrySpec("ADAPT", thr=0, n=15), side, REF_EXIT, daily_thr=dthr,
                            adaptive=True))
    # positional: daily-signal variants (enter next session open)
    for e, side in itertools.product([EntrySpec("A0")] + [EntrySpec(m, thr=t) for m in ("A", "B") for t in THRS]
                                     + [EntrySpec("C", thr=t, n=20) for t in THRS], (1, -1)):
        plan.append(RunSpec("positional", "D/W", e, side, REF_EXIT))
    for side in (1, -1):
        plan.append(RunSpec("positional", "60/D", EntrySpec("RAND", p=1.0 / 35), side, REF_EXIT))
        plan.append(RunSpec("positional", "D/W", EntrySpec("RAND", p=1.0 / 5), side, REF_EXIT))
    return plan


EXIT_GRID = [
    ExitSpec(stop_mode=sm, stop_k=k, target_r=tr, trail_k=tk, ema_mode=em, partial_r=pr)
    for (sm, k) in ((0, 0.0), (1, 1.0), (1, 1.5), (1, 2.0))
    for (tr, tk, em, pr) in (
        (1.5, 0, 0, 0),  # fixed 1.5R
        (2.0, 0, 0, 0),  # fixed 2R
        (0, 2.0, 0, 0),  # ATR trailing 2x
        (0, 3.0, 0, 0),  # ATR trailing 3x
        (0, 0, 1, 0),  # exit on confirmed EMA20 violation
        (0, 0, 2, 0),  # exit on EMA20/50 trend breakdown
        (0, 2.0, 0, 1.0),  # partial at 1R, breakeven, trail remainder
        (0, 0, 0, 0),  # time-based only (stop + EOD / 5 sessions)
    )
]


def stage2_plan(selected: list[RunSpec]) -> list[RunSpec]:
    plan = []
    for r in selected:
        for ex in EXIT_GRID:
            plan.append(RunSpec(r.engine, r.tf, r.entry, r.side, ex, r.daily_thr, r.max_sessions, r.adaptive))
    return plan


# ------------------------------------------------------------------ windows & selection
def in_window(t: pd.DataFrame, start, end, purge: bool = True) -> pd.DataFrame:
    """Trades filled inside [start, end]. With purge, trades whose exit falls after `end` are dropped, so
    a training/development window never uses prices from the following test/holdout window."""
    d = t["fill_time"].dt.normalize()
    m = (d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))
    if purge:
        m &= t["exit_time"] <= pd.Timestamp(end) + pd.Timedelta(hours=23, minutes=59)
    return t[m]


def dev(t):
    return in_window(t, STUDY_START, DEV_END)


def holdout(t):
    return in_window(t, HOLDOUT_START, STUDY_END)


def prepare(trades: pd.DataFrame, cap_is_margin: bool = False) -> pd.DataFrame:
    t = trades[trades["fill_time"].dt.normalize() >= STUDY_START]
    t = non_overlapping(t)
    return standalone_net(t, cap_is_margin=cap_is_margin)


def objective(summary: pd.DataFrame, min_trades: int = 60) -> pd.Series:
    """Selection score: net-R t-statistic (rewards both edge and sample size); ineligible if too few trades."""
    s = summary["t_stat_net"].where(summary["trades"] >= min_trades, -np.inf)
    s = s.where(summary["avg_R_net"] > 0, s - 100)  # never prefer a negative-expectancy config
    return s.where(summary["entry"].astype(str) != "RAND", -np.inf)  # the random control is never selectable


def walk_forward(prepared: pd.DataFrame, keys, min_trades: int = 60) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Choose the best config on each train window, record its next test-window trades."""
    picks, oos = [], []
    for tr_s, tr_e, te_s, te_e in WALK_FORWARD:
        tr = in_window(prepared, tr_s, tr_e)
        if tr.empty:
            continue
        sm = summarize(tr, keys)
        sm["obj"] = objective(sm, min_trades)
        best = sm.sort_values("obj", ascending=False).iloc[0]
        sel = np.ones(len(prepared), bool)
        for k in keys:
            sel &= (prepared[k] == best[k]).to_numpy()
        test = in_window(prepared[sel], te_s, te_e)
        picks.append({"train": f"{tr_s}..{tr_e}", "test": f"{te_s}..{te_e}", **{k: best[k] for k in keys},
                      "train_trades": int(best["trades"]), "train_avg_R_net": best["avg_R_net"],
                      "train_t": best["t_stat_net"], "test_trades": len(test),
                      "test_avg_R_net": float(test["R_net"].mean()) if len(test) else np.nan,
                      "test_net_pnl": float(test["pnl_net"].sum())})
        oos.append(test)
    return pd.DataFrame(picks), (pd.concat(oos, ignore_index=True) if oos else pd.DataFrame())
