"""End-to-end MEDHAALPHA study (blueprint §9 experiment sequence).

  python -m medhaalpha.run_study --stage all

Stages (each saves to data/medhaalpha/results/):
  1  entry study       every entry model x timeframe x side x score threshold, reference exit
  2  exit study        top entries (chosen on development data) x 32 exit models
  3  adaptive TF       5m vs noise-switched 5m/15m
  4  portfolio         ₹3L account, both engines, all risk rules; dev / walk-forward / holdout
  5  options           calls/puts/debit spreads on the final signals (strict & relaxed sizing)
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd

from medhaalpha import adaptive_tf, experiments as X
from medhaalpha.config import DEV_END, HOLDOUT_START, STUDY_END, STUDY_START, WALK_FORWARD
from medhaalpha.data import earnings, loader
from medhaalpha.features import market_regime_table
from medhaalpha.metrics import monthly_returns, portfolio_stats, summarize
from medhaalpha.paths import RESULTS_DIR
from medhaalpha.portfolio import PortfolioRules, run_portfolio, with_margin_reading
from medhaalpha.research import RunSpec, run_plan
from medhaalpha.signals import EntrySpec
from medhaalpha.simulate import ExitSpec

KEYS = ["engine", "tf", "entry", "side", "exit_spec", "daily_thr"]


def _log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def _save(df: pd.DataFrame, name: str):
    df.to_parquet(RESULTS_DIR / f"{name}.parquet", index=False)


def _load(name: str) -> pd.DataFrame:
    return pd.read_parquet(RESULTS_DIR / f"{name}.parquet")


def reading(t: pd.DataFrame, margin: bool) -> pd.DataFrame:
    """Select the per-trade economics of one ₹75k-cap reading."""
    if not margin:
        return t[t["qty"] > 0]
    t = t.dropna(subset=["R_net_m"]).copy()
    t["pnl_net"], t["R_net"], t["cost_R"] = t["pnl_net_m"], t["R_net_m"], t["cost_R_m"]
    return t


def summaries(t: pd.DataFrame, margin: bool) -> pd.DataFrame:
    t = reading(t, margin)
    parts = []
    for name, fn in (("dev", X.dev), ("holdout", X.holdout)):
        s = summarize(fn(t), KEYS)
        s.insert(0, "period", name)
        parts.append(s)
    out = pd.concat(parts, ignore_index=True)
    out["cap_reading"] = "margin" if margin else "notional"
    return out


def spec_from_row(row) -> RunSpec:
    """Rebuild a RunSpec from a summary row (entry label + exit label)."""
    lab = str(row["entry"])
    adaptive = lab.startswith("ADAPT")
    if lab == "A0":
        e = EntrySpec("A0")
    elif lab.startswith("C"):
        n, thr = lab[1:].split("_s")
        e = EntrySpec("C", thr=float(thr), n=int(n))
    elif adaptive:
        e = EntrySpec("ADAPT", thr=float(lab.split("_s")[1]), n=15)
    else:
        m, thr = lab.split("_s")
        e = EntrySpec(m, thr=float(thr))
    ex = parse_exit(str(row["exit_spec"]))
    return RunSpec(str(row["engine"]), str(row["tf"]), e, int(row["side"]), ex, float(row["daily_thr"]), 5, adaptive)


def parse_exit(label: str) -> ExitSpec:
    for ex in X.EXIT_GRID + [X.REF_EXIT]:
        if ex.label == label:
            return ex
    raise ValueError(label)


# ------------------------------------------------------------------ stage 1
def stage1():
    plan = X.stage1_plan(include_3m=True)
    _log(f"stage1: {len(plan)} runs per symbol")
    t = run_plan(plan, compact=True)
    _save(t, "stage1_trades")
    s = pd.concat([summaries(t, False), summaries(t, True)], ignore_index=True)
    _save(s, "stage1_summary")
    _log(f"stage1 done: {len(t)} trades")


def best_by_family(summary: pd.DataFrame, engine: str, reading_: str, min_trades=60) -> pd.DataFrame:
    s = summary[(summary["engine"] == engine) & (summary["cap_reading"] == reading_)]
    dev_s = s[s["period"] == "dev"].copy()
    dev_s["obj"] = X.objective(dev_s, min_trades)
    dev_s["family"] = dev_s["entry"].astype(str).str.extract(r"^(A0|A|B|C\d+|ADAPT)")[0].str.replace(r"C\d+", "C", regex=True)
    rows = []
    for (fam, side), g in dev_s.groupby(["family", "side"]):
        b = g.sort_values("obj", ascending=False).iloc[0]
        hold = s[(s["period"] == "holdout") & (s["tf"] == b["tf"]) & (s["entry"] == b["entry"]) & (s["side"] == side)
                 & (s["exit_spec"] == b["exit_spec"]) & (s["daily_thr"] == b["daily_thr"])]
        h = hold.iloc[0] if len(hold) else None
        rows.append({
            "family": fam, "side": side, "tf": b["tf"], "entry": b["entry"], "daily_thr": b["daily_thr"],
            "exit_spec": b["exit_spec"],
            "dev_trades": b["trades"], "dev_avg_R_net": b["avg_R_net"], "dev_t": b["t_stat_net"],
            "dev_pf": b["profit_factor"], "dev_win": b["win_rate"], "dev_cost_R": b["avg_cost_R"],
            "hold_trades": h["trades"] if h is not None else 0,
            "hold_avg_R_net": h["avg_R_net"] if h is not None else np.nan,
            "hold_pf": h["profit_factor"] if h is not None else np.nan,
        })
    return pd.DataFrame(rows)


# ------------------------------------------------------------------ stage 2
def stage2(top_k: int = 3):
    s = _load("stage1_summary")
    sel = []
    for engine, rd in (("intraday", "margin"), ("positional", "notional")):
        for side in (1, -1):
            d = s[(s["engine"] == engine) & (s["cap_reading"] == rd) & (s["period"] == "dev") & (s["side"] == side)].copy()
            d["obj"] = X.objective(d)
            d = d.sort_values("obj", ascending=False).head(top_k)
            sel += [spec_from_row(r) for _, r in d.iterrows()]
    plan = X.stage2_plan(sel)
    _log(f"stage2: {len(sel)} entries x {len(X.EXIT_GRID)} exits")
    t = run_plan(plan, compact=True)
    _save(t, "stage2_trades")
    out = pd.concat([summaries(t, False), summaries(t, True)], ignore_index=True)
    _save(out, "stage2_summary")
    _log("stage2 done")


# ------------------------------------------------------------------ stage 3
def stage3():
    t1 = _load("stage1_trades")
    flags = adaptive_tf.noise_flags(loader.canonical_symbols())
    _save(flags, "noise_flags")
    rows = []
    for entry in t1.loc[t1["engine"] == "intraday", "entry"].astype(str).unique():
        for side in (1, -1):
            for margin in (False, True):
                tt = reading(t1, margin)
                comb = adaptive_tf.combine(tt, flags, entry, side)
                fixed = tt[(tt["engine"] == "intraday") & (tt["entry"] == entry) & (tt["side"] == side) & (tt["tf"] == "5/15")]
                for label, frame in (("adaptive_tf", comb), ("fixed_5m", fixed)):
                    for per, fn in (("dev", X.dev), ("holdout", X.holdout)):
                        f = fn(frame)
                        if len(f) == 0:
                            continue
                        rows.append({"entry": entry, "side": side, "cap_reading": "margin" if margin else "notional",
                                     "variant": label, "period": per, "trades": len(f),
                                     "avg_R_net": float(f["R_net"].mean()), "net_pnl": float(f["pnl_net"].sum()),
                                     "win_rate": float((f["pnl_net"] > 0).mean())})
    _save(pd.DataFrame(rows), "stage3_adaptive_tf")
    _log("stage3 done")


# ------------------------------------------------------------------ stage 4: portfolio
def choose_final(summary: pd.DataFrame, engine: str, rd: str) -> list[pd.Series]:
    """Best development configuration per side (net-R t-statistic, >= 60 trades). Each pick carries
    `passes_gate` = positive development expectancy after costs. The blueprint's own rule is to trade only
    gated picks (otherwise stay in cash); ungated picks are simulated for information."""
    d = summary[(summary["engine"] == engine) & (summary["cap_reading"] == rd) & (summary["period"] == "dev")].copy()
    d["obj"] = X.objective(d)
    picks = []
    for side in (1, -1):
        g = d[(d["side"] == side) & np.isfinite(d["obj"])].sort_values("obj", ascending=False)
        if len(g):
            b = g.iloc[0].copy()
            b["passes_gate"] = bool(b["avg_R_net"] > 0)
            picks.append(b)
    return picks


def raw_trades(specs: list[RunSpec]) -> pd.DataFrame:
    if not specs:
        return pd.DataFrame()
    t = run_plan(specs, compact=False)
    t = t[t["fill_time"] >= STUDY_START]
    return t


def blackout(t: pd.DataFrame) -> pd.DataFrame:
    """Earnings blackout for the positional engine (blueprint: restrict new trades near announcements)."""
    w = earnings.blackout_windows()
    if w.empty or t.empty:
        return t
    pos = (t["engine"] == "positional").to_numpy()
    d = t["fill_time"].dt.normalize().to_numpy()
    sym = t["symbol"].astype(str).to_numpy()
    keep = np.ones(len(t), bool)
    for s_, g in w.groupby("symbol"):
        m = pos & (sym == s_)
        if not m.any():
            continue
        idx = np.flatnonzero(m)
        dd = d[idx]
        hit = np.zeros(len(idx), bool)
        for a, b in zip(g["start"].to_numpy(), g["end"].to_numpy()):
            hit |= (dd >= a) & (dd <= b)
        keep[idx[hit]] = False
    return t[keep]


def run_portfolio_periods(cands: pd.DataFrame, rules: PortfolioRules, label: str) -> tuple[list[dict], pd.DataFrame]:
    out = []
    accs = []
    for per, (a, b) in {"dev": (STUDY_START, DEV_END), "holdout": (HOLDOUT_START, STUDY_END),
                        "full": (STUDY_START, STUDY_END)}.items():
        c = X.in_window(cands, a, b) if not cands.empty else cands
        acc, rej = run_portfolio(c, rules)
        st = portfolio_stats(acc, a, b)
        st.update({"scenario": label, "period": per, "candidates": len(c),
                   "rejections": rej.set_index("reason")["count"].to_dict() if not rej.empty else {}})
        out.append(st)
        if per == "full" and not acc.empty:
            acc = acc.copy()
            acc["scenario"] = label
            accs.append(acc)
    return out, (pd.concat(accs, ignore_index=True) if accs else pd.DataFrame())


def _spec_mask(cand: pd.DataFrame, sp: RunSpec) -> pd.Series:
    return ((cand["engine"] == sp.engine) & (cand["tf"] == sp.tf) & (cand["entry"] == sp.key[2])
            & (cand["side"] == sp.side) & (cand["exit_spec"] == sp.exit.label) & (cand["daily_thr"] == sp.daily_thr))


def stage4():
    from dataclasses import replace

    s1 = _load("stage1_summary")
    s2 = _load("stage2_summary")
    allsum = pd.concat([s1, s2], ignore_index=True).drop_duplicates(
        subset=KEYS + ["period", "cap_reading"], keep="last")
    results, accs, chosen = [], [], {}
    for rd in ("notional", "margin"):
        picks = []
        for engine in ("intraday", "positional"):
            picks += choose_final(allsum, engine, rd)
        chosen[rd] = [{k: (r[k].item() if hasattr(r[k], "item") else r[k])
                       for k in KEYS + ["trades", "avg_R_gross", "avg_R_net", "t_stat_net", "profit_factor", "passes_gate"]}
                      for r in picks]
        specs = [spec_from_row(r) for r in picks]
        gated = [sp for sp, r in zip(specs, picks) if r["passes_gate"]]
        cands_all = raw_trades(specs)
        cands = blackout(cands_all)
        _save(cands, f"final_candidates_{rd}")
        base = PortfolioRules() if rd == "notional" else with_margin_reading(PortfolioRules())
        r, a = run_portfolio_periods(cands, base, f"best_{rd}")
        results += r
        accs.append(a)
        if gated:
            gm = np.zeros(len(cands), bool)
            for sp in gated:
                gm |= _spec_mask(cands, sp).to_numpy()
            r, a = run_portfolio_periods(cands[gm], base, f"gated_{rd}")
        else:
            r = [{"scenario": f"gated_{rd}", "period": per, "trades": 0, "net_profit": 0.0, "candidates": 0,
                  "rejections": {}, "note": "no configuration passed the gate: system stays in cash"}
                 for per in ("dev", "holdout", "full")]
        results += r
        for eng in ("intraday", "positional"):
            r, _ = run_portfolio_periods(cands[cands["engine"] == eng], base, f"best_{rd}_{eng}_only")
            results += r
        stress = replace(base, slip=replace(base.slip, equity_bps=base.slip.equity_bps * 2,
                                             stop_extra_bps=base.slip.stop_extra_bps * 2))
        r, _ = run_portfolio_periods(cands, stress, f"best_{rd}_slippage_x2")
        results += r
        loose = replace(base, max_intraday_per_day=99, risk=replace(base.risk, max_per_industry_direction=99))
        r, _ = run_portfolio_periods(cands, loose, f"best_{rd}_no_sector_or_count_cap")
        results += r
        r, _ = run_portfolio_periods(cands_all, base, f"best_{rd}_no_earnings_blackout")
        results += r
    # walk-forward (configs chosen per training window, applied to the next test window)
    wf_picks = []
    for rd in ("notional", "margin"):
        t1 = reading(_load("stage1_trades"), rd == "margin")
        oos = {"gated": [], "forced": []}
        for engine in ("intraday", "positional"):
            for side in (1, -1):
                pt = t1[(t1["engine"] == engine) & (t1["side"] == side)]
                picks, _ = X.walk_forward(pt, KEYS)
                if picks.empty:
                    continue
                picks["engine"], picks["side"], picks["cap_reading"] = engine, side, rd
                wf_picks.append(picks)
                for _, p in picks.iterrows():
                    sp = spec_from_row(p)
                    oos["forced"].append((sp, p["test"]))
                    if p["train_avg_R_net"] > 0:
                        oos["gated"].append((sp, p["test"]))
        uniq = {}
        for sp, win in oos["forced"]:
            uniq.setdefault(sp, set()).add(win)
        cand = raw_trades(list(uniq))
        base = PortfolioRules() if rd == "notional" else with_margin_reading(PortfolioRules())
        a0, b0 = WALK_FORWARD[0][2], WALK_FORWARD[-1][3]
        for mode in ("gated", "forced"):
            parts = []
            for sp, w in oos[mode]:
                a, b = w.split("..")
                if not cand.empty:
                    parts.append(X.in_window(cand[_spec_mask(cand, sp)], a, b))
            wf_c = blackout(pd.concat(parts, ignore_index=True)) if parts else pd.DataFrame()
            acc, rej = run_portfolio(wf_c, base) if not wf_c.empty else (pd.DataFrame(), pd.DataFrame())
            st = portfolio_stats(acc, a0, b0)
            st.update({"scenario": f"walk_forward_{mode}_{rd}", "period": "wf_oos", "candidates": len(wf_c),
                       "rejections": rej.set_index("reason")["count"].to_dict() if not rej.empty else {}})
            results.append(st)
            if mode == "forced" and not acc.empty:
                acc = acc.copy()
                acc["scenario"] = f"walk_forward_forced_{rd}"
                accs.append(acc)
    if wf_picks:
        _save(pd.concat(wf_picks, ignore_index=True), "walk_forward_picks")
    res = pd.DataFrame(results)
    res["rejections"] = res["rejections"].apply(lambda x: json.dumps(x) if isinstance(x, dict) else "{}")
    _save(res, "stage4_portfolio")
    good = [a for a in accs if a is not None and not a.empty]
    if good:
        acc_all = pd.concat(good, ignore_index=True)
        mr = market_regime_table()
        acc_all["day"] = acc_all["fill_time"].dt.normalize()
        acc_all = acc_all.merge(mr.rename(columns={"date": "day"}), on="day", how="left")
        keep = [c for c in acc_all.columns if acc_all[c].dtype != object or c in (
            "symbol", "industry", "engine", "tf", "entry", "exit_spec", "reason", "scenario", "market_regime", "model")]
        _save(acc_all[keep], "stage4_accepted_trades")
    (RESULTS_DIR / "final_configs.json").write_text(json.dumps(chosen, indent=2, default=str))
    _log("stage4 done")


# ------------------------------------------------------------------ stage 5: options
def stage5():
    from medhaalpha.options import build_option_trades, load_chains

    results, all_opt = [], []
    for rd in ("notional", "margin"):
        cands = _load(f"final_candidates_{rd}")
        if cands.empty:
            continue
        cands = cands[cands["fill_time"] <= STUDY_END + pd.Timedelta(days=1)]
        chains = load_chains(set(cands["symbol"].unique()))
        base = PortfolioRules() if rd == "notional" else with_margin_reading(PortfolioRules())
        built = {}
        for st in ("long", "spread"):
            o = build_option_trades(cands, chains, st)
            o["structure"] = st
            built[st] = o
            all_opt.append(o.assign(cap_reading=rd))
        for st in ("long", "spread"):
            o = built[st]
            ok = o[o["opt_status"] == "ok"].copy()
            for sizing in ("strict", "relaxed"):
                x = ok.copy()
                x["unit_risk"] = x[f"unit_risk_{sizing}"]
                if sizing == "relaxed":
                    x = x[x["unit_debit"] <= 30_000]
                x["instrument"] = "option"
                r, _ = run_portfolio_periods(x, base, f"options_{st}_{sizing}_{rd}")
                for q in r:
                    q["executable_share"] = float((ok["unit_risk_strict"] <= 3000).mean()) if sizing == "strict" else np.nan
                results += r
        # hybrid per blueprint §7: strict-executable spread -> long option -> equity -> skip
        sp, lg = built["spread"], built["long"]
        hyb = cands.copy()
        hyb["instrument"] = "equity"
        sp_ok = (sp["opt_status"] == "ok") & (sp["unit_risk_strict"] <= 3000)
        lg_ok = (lg["opt_status"] == "ok") & (lg["unit_risk_strict"] <= 3000)
        cols = ["unit_risk_strict", "unit_debit", "unit_pnl", "unit_spread_cost", "unit_buy_prem", "unit_sell_prem", "n_orders"]
        for c in cols:
            hyb[c] = np.where(sp_ok, sp[c], np.where(lg_ok, lg[c], np.nan))
        hyb.loc[sp_ok | lg_ok, "instrument"] = "option"
        hyb["unit_risk"] = hyb["unit_risk_strict"]
        bear_pos = (hyb["engine"] == "positional") & (hyb["side"] < 0) & (hyb["instrument"] == "equity")
        hyb = hyb[~bear_pos]
        r, _ = run_portfolio_periods(hyb, base, f"hybrid_strict_{rd}")
        results += r
    res = pd.DataFrame(results)
    res["rejections"] = res["rejections"].apply(lambda x: json.dumps(x) if isinstance(x, dict) else "{}")
    _save(res, "stage5_options")
    if all_opt:
        o = pd.concat(all_opt, ignore_index=True)
        keep = [c for c in o.columns if o[c].dtype != object or c in ("opt_status", "instrument", "symbol", "engine", "structure", "cap_reading", "reason")]
        _save(o[keep], "stage5_option_trades")
    _log("stage5 done")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", default="all")
    a = p.parse_args()
    stages = {"1": stage1, "2": stage2, "3": stage3, "4": stage4, "5": stage5}
    todo = list(stages) if a.stage == "all" else a.stage.split(",")
    for k in todo:
        stages[k]()
