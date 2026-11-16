"""Build the HTML research report from data/medhaalpha/results/*.

  python -m medhaalpha.report --out <path.html>
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from medhaalpha import experiments as X
from medhaalpha.config import DEV_END, HOLDOUT_START, STUDY_END, STUDY_START
from medhaalpha.metrics import equity_curve, monthly_returns
from medhaalpha.paths import RESULTS_DIR
from medhaalpha.report_svg import bar_chart, esc, fmt_inr, line_chart

KEYS = ["engine", "tf", "entry", "side", "exit_spec", "daily_thr"]


def load(name):
    p = RESULTS_DIR / f"{name}.parquet"
    return pd.read_parquet(p) if p.exists() else pd.DataFrame()


# ------------------------------------------------------------------ formatting
def f_r(v, d=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:+.{d}f}R"


def f_num(v, d=2):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:,.{d}f}"


def f_pct(v, d=1):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:.{d}f}%"


def side_name(s):
    return "Long" if int(s) > 0 else "Short"


def cls_r(v):
    if v is None or not np.isfinite(v):
        return ""
    return "pos" if v > 0 else "neg"


def heat(v, scale=0.3):
    """Diverging cell background via CSS custom property (theme-aware colors in CSS)."""
    if v is None or not np.isfinite(v):
        return ""
    a = min(abs(v) / scale, 1.0)
    return f' style="--a:{a:.2f}" data-sign="{"p" if v > 0 else "n"}"'


def table(headers, rows, cls="") -> str:
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table></div>'


def td(text, klass="", extra=""):
    return f'<td class="{klass}"{extra}>{text}</td>'


ENTRY_NAMES = {
    "A0": "Baseline EMA 20/50 crossover (no filters)",
    "A": "Trend-filtered crossover",
    "B": "EMA 20 pullback continuation",
    "C": "Range breakout + volume",
    "ADAPT": "Regime-adaptive (B / C / A / none)",
    "RAND": "Random entries (control)",
}


def family(label: str) -> str:
    label = str(label)
    if label in ("A0", "RAND"):
        return label
    if label.startswith("ADAPT"):
        return "ADAPT"
    if label.startswith("C"):
        return "C"
    return label.split("_")[0]


def describe_cfg(row) -> str:
    lab = str(row["entry"])
    tf = str(row["tf"])
    tf_txt = {"60/D": "60-min entry, daily trend gate", "D/W": "daily signal, next-day open"}.get(
        tf, f"{tf.split('/')[0]}-min signal, {tf.split('/')[1]}-min confirmation" if "/" in tf else tf)
    thr = ""
    if "_s" in lab:
        thr = f", score ≥ {lab.split('_s')[1]}" if lab.split("_s")[1] != "0" else ", no score filter"
    if lab.startswith("C"):
        n = lab[1:].split("_")[0]
        thr = f", {n}-bar range" + thr
    dthr = float(row.get("daily_thr", 0) or 0)
    if dthr > 0:
        thr += f", daily score ≥ {int(dthr)}"
    return f"{side_name(row['side'])} · {tf_txt}{thr}"


# ------------------------------------------------------------------ sections
def experiment_sequence(s1: pd.DataFrame, engine: str, reading: str) -> tuple[str, pd.DataFrame]:
    s = s1[(s1["engine"] == engine) & (s1["cap_reading"] == reading)].copy()
    dev = s[s["period"] == "dev"].copy()
    dev["obj"] = X.objective(dev)
    dev["fam"] = dev["entry"].map(family)
    out = []
    for fam in ["RAND", "A0", "A", "B", "C", "ADAPT"]:
        for side in (1, -1):
            g = dev[(dev["fam"] == fam) & (dev["side"] == side)]
            if g.empty:
                continue
            if fam == "RAND":
                ref_tf = "15/60" if engine == "intraday" else "D/W"  # same timeframe as most chosen rows
                g2 = g[g["tf"] == ref_tf]
                b = (g2 if len(g2) else g).iloc[0]
            else:
                b = g.sort_values("obj", ascending=False).iloc[0]
            m = (s["period"] == "holdout")
            for k in ("tf", "entry", "side", "exit_spec", "daily_thr"):
                m &= s[k] == b[k]
            h = s[m]
            h = h.iloc[0] if len(h) else None
            out.append({
                "family": fam, "side": side, "cfg": describe_cfg(b), "tf": b["tf"], "entry": b["entry"],
                "daily_thr": b["daily_thr"], "exit_spec": b["exit_spec"],
                "dev_trades": int(b["trades"]), "dev_gross": b["avg_R_gross"], "dev_net": b["avg_R_net"],
                "dev_pf": b["profit_factor"], "dev_t": b["t_stat_net"], "dev_cost": b["avg_cost_R"],
                "hold_trades": int(h["trades"]) if h is not None else 0,
                "hold_gross": h["avg_R_gross"] if h is not None else np.nan,
                "hold_net": h["avg_R_net"] if h is not None else np.nan,
                "hold_pf": h["profit_factor"] if h is not None else np.nan,
            })
    df = pd.DataFrame(out)
    rows = []
    for r in df.itertuples():
        rows.append([
            f'<span class="fam">{esc(r.family)}</span> {esc(ENTRY_NAMES[r.family])}',
            esc(r.cfg),
            f_num(r.dev_trades, 0),
            td(f_r(r.dev_gross), cls_r(r.dev_gross)),
            td(f_r(r.dev_cost), "muted"),
            td(f_r(r.dev_net), cls_r(r.dev_net)),
            f_num(r.dev_pf),
            f_num(r.hold_trades, 0),
            td(f_r(r.hold_net), cls_r(r.hold_net)),
            f_num(r.hold_pf),
        ])
    html = table(["Model", "Best configuration (chosen on development data)", "Trades", "Gross R",
                  "Cost R", "Net R", "PF", "Holdout trades", "Holdout net R", "Holdout PF"], rows, "seq")
    return html, df


def grid_heatmap(s1: pd.DataFrame, engine="intraday", metric="avg_R_gross", reading="margin") -> str:
    s = s1[(s1["engine"] == engine) & (s1["cap_reading"] == reading) & (s1["period"] == "dev")]
    tfs = [t for t in ["3/15", "3/60", "5/15", "5/60", "15/60"] if t in set(s["tf"])]
    entries = [e for e in sorted(s["entry"].astype(str).unique(), key=lambda x: (family(x) != "RAND",
               ["RAND", "A0", "A", "B", "C", "ADAPT"].index(family(x)), x))]
    head = ["Entry"] + [f"{tf} {side_name(sd)[0]}" for tf in tfs for sd in (1, -1)]
    rows = []
    for e in entries:
        r = [f'<span class="mono">{esc(e)}</span>']
        for tf in tfs:
            for sd in (1, -1):
                g = s[(s["entry"] == e) & (s["tf"] == tf) & (s["side"] == sd)]
                v = float(g[metric].iloc[0]) if len(g) else np.nan
                r.append(td(f"{v:+.2f}" if np.isfinite(v) else "—", "hm", heat(v, 0.15)))
        rows.append(r)
    return table(head, rows, "heat")


def portfolio_table(p4: pd.DataFrame, scenarios: list[tuple[str, str, str]]) -> str:
    metrics = [
        ("trades", "Trades", lambda v: f_num(v, 0)),
        ("net_profit", "Net profit", fmt_inr),
        ("return_pct", "Return on ₹3L", f_pct),
        ("cagr_pct", "CAGR", f_pct),
        ("profit_factor", "Profit factor", f_num),
        ("max_drawdown", "Max drawdown (MTM)", fmt_inr),
        ("max_drawdown_pct", "Max drawdown %", f_pct),
        ("win_rate_pct", "Win rate", f_pct),
        ("realised_reward_risk", "Avg win / avg loss", f_num),
        ("expectancy_per_trade", "Expectancy per trade", fmt_inr),
        ("expectancy_R", "Expectancy (R)", f_r),
        ("avg_planned_risk", "Avg planned risk", fmt_inr),
        ("trades_per_day", "Trades per day", f_num),
        ("avg_hold_minutes", "Avg holding (min)", lambda v: f_num(v, 0)),
        ("longest_losing_streak", "Longest losing streak", lambda v: f_num(v, 0)),
        ("gross_pnl", "Gross P&L", fmt_inr),
        ("total_costs", "Charges & taxes", fmt_inr),
        ("total_slippage", "Slippage", fmt_inr),
        ("intraday_pnl", "Intraday P&L", fmt_inr),
        ("positional_pnl", "Positional P&L", fmt_inr),
        ("pnl_ex_top5pct", "P&L without top 5% trades", fmt_inr),
        ("sharpe_daily", "Sharpe (daily, ann.)", f_num),
    ]
    cols = []
    for scen, per, label in scenarios:
        r = p4[(p4["scenario"] == scen) & (p4["period"] == per)]
        cols.append((label, r.iloc[0] if len(r) else None))
    rows = []
    for key, lab, fmt in metrics:
        row = [esc(lab)]
        for _, r in cols:
            v = r.get(key) if r is not None else None
            v = None if v is None or (isinstance(v, float) and np.isnan(v)) else v
            txt = fmt(v) if v is not None else "—"
            klass = ""
            if key in ("net_profit", "gross_pnl", "intraday_pnl", "positional_pnl", "pnl_ex_top5pct",
                       "expectancy_per_trade", "expectancy_R", "return_pct", "cagr_pct") and v is not None:
                klass = cls_r(float(v))
            row.append(td(esc(txt), "num " + klass))
        rows.append(row)
    return table(["Metric"] + [c[0] for c in cols], rows, "metrics")


def _row(p, scen, per):
    r = p[(p["scenario"] == scen) & (p["period"] == per)]
    return r.iloc[0] if len(r) else None


def _chip(ok: bool | None, text_ok="Pass", text_bad="Fail") -> str:
    if ok is None:
        return '<span class="chip na">n/a</span>'
    return f'<span class="chip {"ok" if ok else "bad"}">{text_ok if ok else text_bad}</span>'


def promotion_table(p4: pd.DataFrame) -> str:
    cols = [
        ("Walk-forward OOS, gated", "walk_forward_gated_notional", "wf_oos"),
        ("Walk-forward OOS, best each window", "walk_forward_forced_notional", "wf_oos"),
        ("Holdout, best configs (spec cap)", "best_notional", "holdout"),
        ("Holdout, gated (MIS-margin cap)", "gated_margin", "holdout"),
    ]
    crit = [
        ("Out-of-sample profit factor > 1.25", lambda r: (r.get("profit_factor"), r.get("profit_factor", 0) > 1.25), f_num),
        ("Positive after all costs", lambda r: (r.get("net_profit"), r.get("net_profit", 0) > 0), fmt_inr),
        ("Max drawdown ≤ 10% of capital", lambda r: (r.get("max_drawdown_pct"), r.get("max_drawdown_pct", -100) >= -10), f_pct),
        ("Still positive without the top 5% of trades", lambda r: (r.get("pnl_ex_top5pct"), r.get("pnl_ex_top5pct", -1) > 0), fmt_inr),
    ]
    rows = []
    for name, fn, fmt in crit:
        row = [esc(name)]
        for _, scen, per in cols:
            r = _row(p4, scen, per)
            if r is None or not r.get("trades"):
                row.append(td('<span class="chip na">no trades</span>'))
                continue
            v, ok = fn(r)
            v = None if v is None or (isinstance(v, float) and not np.isfinite(v)) else v
            row.append(td(f'{_chip(bool(ok))} <span class="num">{esc(fmt(v)) if v is not None else "—"}</span>'))
        rows.append(row)
    trades = ["Trades"]
    for _, scen, per in cols:
        r = _row(p4, scen, per)
        trades.append(td(f_num(r.get("trades", 0), 0) if r is not None else "0", "num"))
    rows.insert(0, trades)
    return table(["Promotion criterion"] + [c[0] for c in cols], rows, "promo")


def exit_study_table(s2: pd.DataFrame) -> str:
    d = s2[(s2["period"] == "dev")]
    d = d[((d["engine"] == "intraday") & (d["cap_reading"] == "margin")) |
          ((d["engine"] == "positional") & (d["cap_reading"] == "notional"))].copy()
    h = s2[(s2["period"] == "holdout")]
    out = []
    for (eng, tf, entry, side, dthr), g in d.groupby(["engine", "tf", "entry", "side", "daily_thr"], observed=True):
        g = g.sort_values("avg_R_net", ascending=False)
        best, ref = g.iloc[0], g[g["exit_spec"] == "struct+tgt2R"]
        ref = ref.iloc[0] if len(ref) else None
        hm = h[(h["engine"] == eng) & (h["tf"] == tf) & (h["entry"] == entry) & (h["side"] == side) &
               (h["daily_thr"] == dthr) & (h["exit_spec"] == best["exit_spec"]) &
               (h["cap_reading"] == best["cap_reading"])]
        hb = hm.iloc[0] if len(hm) else None
        out.append([
            esc(eng.capitalize()), esc(describe_cfg(best)),
            td(f_r(ref["avg_R_net"]) if ref is not None else "—", cls_r(ref["avg_R_net"]) if ref is not None else ""),
            f'<span class="mono">{esc(best["exit_spec"])}</span>',
            td(f_r(best["avg_R_net"]), cls_r(best["avg_R_net"])), f_num(best["t_stat_net"]),
            td(f_r(hb["avg_R_net"]) if hb is not None else "—", cls_r(hb["avg_R_net"]) if hb is not None else ""),
        ])
    return table(["Engine", "Entry (top-3 per side on development data)", "Net R, reference exit",
                  "Best exit (development)", "Net R, best exit", "t-stat", "Holdout net R, best exit"], out, "exits")


def build(out_path: str) -> None:
    s1 = load("stage1_summary")
    s2 = load("stage2_summary")
    s3 = load("stage3_adaptive_tf")
    p4 = load("stage4_portfolio")
    acc = load("stage4_accepted_trades")
    p5 = load("stage5_options")
    o5 = load("stage5_option_trades")

    seq_i_html, seq_i = experiment_sequence(s1, "intraday", "notional")
    seq_im_html, _ = experiment_sequence(s1, "intraday", "margin")
    seq_p_html, seq_p = experiment_sequence(s1, "positional", "notional")

    # ---- headline aggregates
    dev = s1[(s1["period"] == "dev") & (s1["entry"] != "RAND")]
    hold = s1[(s1["period"] == "holdout") & (s1["entry"] != "RAND")]
    n_cfg = len(dev.drop_duplicates(KEYS))
    i_dev = dev[(dev["engine"] == "intraday")]
    p_dev = dev[(dev["engine"] == "positional") & (dev["cap_reading"] == "notional")]
    intraday_pos = int((i_dev["avg_R_net"] > 0).sum())
    pos_pos = int((p_dev["avg_R_net"] > 0).sum())
    i_n = i_dev[i_dev["cap_reading"] == "notional"]
    i_m = i_dev[i_dev["cap_reading"] == "margin"]

    def wavg(df, col):
        return float(np.average(df[col], weights=df["trades"])) if len(df) else np.nan

    gross_i = float(i_m["avg_R_gross"].median())
    cost_n = float(i_n["avg_cost_R"].median())
    cost_m = float(i_m["avg_cost_R"].median())
    rand = s1[(s1["entry"] == "RAND") & (s1["period"] == "dev") & (s1["cap_reading"] == "margin") & (s1["engine"] == "intraday")]
    rand_short = wavg(rand[rand["side"] < 0], "avg_R_gross")
    rand_long = wavg(rand[rand["side"] > 0], "avg_R_gross")
    sig_short = wavg(i_m[i_m["side"] < 0], "avg_R_gross")
    sig_long = wavg(i_m[i_m["side"] > 0], "avg_R_gross")
    s2d = s2[s2["period"] == "dev"]
    s2d = s2d[((s2d["engine"] == "intraday") & (s2d["cap_reading"] == "margin")) |
              ((s2d["engine"] == "positional") & (s2d["cap_reading"] == "notional"))]
    n_exit_pos = int((s2d["avg_R_net"] > 0).sum())
    n_exit = len(s2d)
    max_t = float(pd.concat([dev["t_stat_net"], s2d["t_stat_net"]]).max())
    n_all = n_cfg + len(s2d.drop_duplicates(KEYS))

    bn_full, bn_hold = _row(p4, "best_notional", "full"), _row(p4, "best_notional", "holdout")
    gm_full, gm_hold = _row(p4, "gated_margin", "full"), _row(p4, "gated_margin", "holdout")
    wf_g, wf_f = _row(p4, "walk_forward_gated_notional", "wf_oos"), _row(p4, "walk_forward_forced_notional", "wf_oos")

    # ---- adaptive TF
    x = s3[(s3["cap_reading"] == "margin")].pivot_table(index=["entry", "side", "period"], columns="variant", values="avg_R_net")
    ad_share = float((x["adaptive_tf"] > x["fixed_5m"]).mean()) if len(x) else np.nan
    ad_mean, fx_mean = float(x["adaptive_tf"].mean()), float(x["fixed_5m"].mean())
    ad_pos = int((x["adaptive_tf"] > 0).sum())

    # ---- options
    o = o5[o5["cap_reading"] == "notional"] if not o5.empty else o5
    ok = o[o["opt_status"] == "ok"] if not o.empty else o
    lg, sp = ok[ok["structure"] == "long"], ok[ok["structure"] == "spread"]
    exec_long = float((lg["unit_risk_strict"] <= 3000).mean()) if len(lg) else np.nan
    exec_sp = float((sp["unit_risk_strict"] <= 3000).mean()) if len(sp) else np.nan
    med_long, med_sp = float(lg["unit_risk_strict"].median()), float(sp["unit_risk_strict"].median())
    e = ok.dropna(subset=["eod_actual_unit_pnl", "eod_model_unit_pnl"]) if len(ok) else ok
    corr_long = float(np.corrcoef(e[e.structure == "long"].eod_actual_unit_pnl, e[e.structure == "long"].eod_model_unit_pnl)[0, 1]) if len(e) else np.nan
    corr_sp = float(np.corrcoef(e[e.structure == "spread"].eod_actual_unit_pnl, e[e.structure == "spread"].eod_model_unit_pnl)[0, 1]) if len(e) else np.nan
    ol_rel, os_rel = _row(p5, "options_long_relaxed_notional", "full"), _row(p5, "options_spread_relaxed_notional", "full")
    os_strict = _row(p5, "options_spread_strict_notional", "full")
    opt_rows = []
    for name, st, r in (("Long call / put", "long", ol_rel), ("Bull call / bear put debit spread", "spread", os_rel)):
        g = ok[ok["structure"] == st]
        opt_rows.append([
            esc(name), f_num(len(g), 0), f_pct(100 * float((g["unit_risk_strict"] <= 3000).mean())),
            esc(fmt_inr(float(g["unit_risk_strict"].median()))), f_num(float(g["lot"].median()), 0),
            f_num(float(g["days_to_expiry"].median()), 0), f_num(float(g["iv"].median()) * 100, 0) + "%",
            td(esc(fmt_inr(r["net_profit"])) if r is not None else "—", cls_r(r["net_profit"]) if r is not None else ""),
            f_num(r.get("trades", 0), 0) if r is not None else "0",
            f_num(r.get("profit_factor")) if r is not None else "—",
        ])
    opt_table = table(["Structure", "Signals mapped", "Within ₹3,000 max loss", "Median max loss / lot",
                       "Median lot", "Median days to expiry", "Median IV", "Relaxed sizing: net P&L",
                       "Trades", "PF"], opt_rows, "opts")

    # ---- equity curves (daily mark-to-market)
    curves = []
    labels = None
    for scen, cls_, name in (("best_notional", "s1", "Best development configs, spec cap (₹75k notional)"),
                             ("best_margin", "s2", "Best development configs, MIS-margin cap")):
        a = acc[acc["scenario"] == scen] if not acc.empty else acc
        ec = equity_curve(a, STUDY_START, STUDY_END, 300_000.0)
        curves.append({"name": name, "y": (ec["equity"] - 300_000).tolist(), "cls": cls_})
        labels = [d.strftime("%b %y") for d in ec["date"]]
    ec = equity_curve(acc[acc["scenario"] == "best_notional"], STUDY_START, STUDY_END, 300_000.0)
    hold_idx = int((ec["date"] < HOLDOUT_START).sum())
    eq_svg = line_chart(curves, x_labels=labels, title="Cumulative net P&L", marker_index=hold_idx,
                        marker_label="Holdout")
    mr = monthly_returns(acc[acc["scenario"] == "best_notional"]) if not acc.empty else pd.DataFrame()
    mr_svg = bar_chart([pd.Period(m).strftime("%b %y") for m in mr["month"]],
                       mr["net_pnl"].tolist(), title="Monthly net P&L", height=220) if len(mr) else ""

    # ---- regime split
    reg_rows = []
    b = acc[acc["scenario"] == "best_notional"] if not acc.empty else acc
    for (eng, rg), g in b.groupby(["engine", "market_regime"], observed=True):
        reg_rows.append([esc(eng.capitalize()), esc(rg.capitalize()), f_num(len(g), 0),
                         td(esc(fmt_inr(g["pnl_net"].sum())), "num " + cls_r(g["pnl_net"].sum())),
                         td(esc(fmt_inr(g["pnl_net"].mean())), "num " + cls_r(g["pnl_net"].mean())),
                         td(f_pct(100 * (g["pnl_net"] > 0).mean()), "num")])
    reg_table = table(["Engine", "NIFTY 50 regime (prior day)", "Trades", "Net P&L", "Per trade", "Win rate"], reg_rows)

    # ---- breakdown tables (trade-weighted, development period)
    def breakdown(df, by, label_fn):
        rows = []
        for k, g in df.groupby(by, observed=True):
            rows.append([esc(label_fn(k)), f_num(g["trades"].sum(), 0), td(f_r(wavg(g, "avg_R_gross"), 3), cls_r(wavg(g, "avg_R_gross"))),
                         td(f_r(wavg(g, "avg_cost_R"), 3), "muted"), td(f_r(wavg(g, "avg_R_net"), 3), cls_r(wavg(g, "avg_R_net")))])
        return rows

    tfmap = {"3/15": "3-min signal / 15-min confirm", "3/60": "3-min / 60-min", "5/15": "5-min / 15-min",
             "5/60": "5-min / 60-min", "15/60": "15-min / 60-min"}
    tf_rows = breakdown(i_m, "tf", lambda k: tfmap.get(k, k))
    thr = i_m.assign(thr=i_m["entry"].astype(str).str.extract(r"_s(\d+)")[0].fillna("—"))
    thr_rows = breakdown(thr[thr["thr"] != "—"], "thr", lambda k: "No score filter" if k == "0" else f"Score ≥ {k}")
    side_rows = breakdown(i_m, "side", side_name)
    rnd_rows = [[esc(f"Random entries, {side_name(sd).lower()}"), f_num(g["trades"].sum(), 0),
                 td(f_r(wavg(g, "avg_R_gross"), 3), cls_r(wavg(g, "avg_R_gross"))), td(f_r(wavg(g, "avg_cost_R"), 3), "muted"),
                 td(f_r(wavg(g, "avg_R_net"), 3), cls_r(wavg(g, "avg_R_net")))] for sd, g in rand.groupby("side")]
    bd_head = ["", "Trades", "Gross R / trade", "Cost R / trade", "Net R / trade"]

    # ---- portfolio tables
    port_main = portfolio_table(p4, [
        ("best_notional", "full", "Best configs · full 2y"),
        ("best_notional", "holdout", "Best configs · holdout"),
        ("gated_notional", "full", "Gated · full 2y"),
        ("gated_margin", "full", "Gated, MIS cap · full 2y"),
        ("gated_margin", "holdout", "Gated, MIS cap · holdout"),
        ("walk_forward_forced_notional", "wf_oos", "Walk-forward OOS"),
    ])
    sens_rows = []
    for scen, lab in (("best_notional", "Base case (spec rules)"), ("best_notional_intraday_only", "Intraday engine only"),
                      ("best_notional_positional_only", "Positional engine only"),
                      ("best_notional_slippage_x2", "Slippage doubled"),
                      ("best_notional_no_sector_or_count_cap", "No sector cap / no 6-per-day cap"),
                      ("best_notional_no_earnings_blackout", "No earnings blackout"),
                      ("best_margin", "₹75k read as MIS margin (₹3.75L exposure)")):
        r = _row(p4, scen, "full")
        if r is None:
            continue
        sens_rows.append([esc(lab), f_num(r["trades"], 0), td(esc(fmt_inr(r["net_profit"])), cls_r(r["net_profit"])),
                          f_num(r.get("profit_factor")), esc(fmt_inr(r.get("max_drawdown", 0))), f_num(r.get("trades_per_day"))])
    sens_table = table(["Scenario (full two years)", "Trades", "Net P&L", "PF", "Max drawdown", "Trades/day"], sens_rows)

    final_cfg = json.loads((RESULTS_DIR / "final_configs.json").read_text())
    cfg_rows = []
    for rd, items in final_cfg.items():
        for r in items:
            cfg_rows.append([esc("Spec (₹75k notional)" if rd == "notional" else "MIS margin"),
                             esc(describe_cfg(r)), f'<span class="mono">{esc(r["entry"])} · {esc(r["exit_spec"])}</span>',
                             f_num(r["trades"], 0), td(f_r(r["avg_R_net"], 3), cls_r(r["avg_R_net"])), f_num(r["t_stat_net"]),
                             _chip(bool(r["passes_gate"]), "Trades", "Cash")])
    cfg_table = table(["Cap reading", "Configuration", "Entry · exit", "Dev trades", "Dev net R", "t-stat", "Gate"], cfg_rows)

    ctx = dict(
        n_cfg=f"{n_cfg}", n_all=f"{n_all}", intraday_pos=f"{intraday_pos}", n_i=f"{len(i_dev.drop_duplicates(KEYS))}",
        pos_pos=f"{pos_pos}", n_p=f"{len(p_dev)}", gross_i=f"{gross_i:+.3f}R", cost_n=f"{cost_n:.2f}R", cost_m=f"{cost_m:.2f}R",
        rand_short=f"{rand_short:+.3f}R", rand_long=f"{rand_long:+.3f}R", sig_short=f"{sig_short:+.3f}R", sig_long=f"{sig_long:+.3f}R",
        n_exit_pos=f"{n_exit_pos}", n_exit=f"{n_exit}", max_t=f"{max_t:.2f}",
        bn_loss=fmt_inr(-bn_full["net_profit"]), wf_f_loss=fmt_inr(-wf_f["net_profit"]),
        gn_net=fmt_inr(_row(p4, "gated_notional", "full")["net_profit"]), wf_g_loss=fmt_inr(-wf_g["net_profit"]),
        bn_net=fmt_inr(bn_full["net_profit"]), bn_ret=f"{bn_full['return_pct']:.1f}%", bn_pf=f"{bn_full['profit_factor']:.2f}",
        bn_dd=f"{bn_full['max_drawdown_pct']:.1f}%", bn_hold=fmt_inr(bn_hold["net_profit"]), bn_tpd=f"{bn_full['trades_per_day']:.1f}",
        gm_net=fmt_inr(gm_full["net_profit"]), gm_ret=f"{gm_full['return_pct']:.1f}%", gm_pf=f"{gm_full['profit_factor']:.2f}",
        gm_hold=fmt_inr(gm_hold["net_profit"]), gm_hold_pf=f"{gm_hold['profit_factor']:.2f}", gm_dd=f"{gm_full['max_drawdown_pct']:.1f}%",
        wf_g=fmt_inr(wf_g["net_profit"]), wf_g_pf=f"{wf_g['profit_factor']:.2f}", wf_g_n=f"{int(wf_g['trades'])}",
        wf_f=fmt_inr(wf_f["net_profit"]), wf_f_pf=f"{wf_f['profit_factor']:.2f}",
        exec_long=f"{100 * exec_long:.1f}%", exec_sp=f"{100 * exec_sp:.1f}%", med_long=fmt_inr(med_long), med_sp=fmt_inr(med_sp),
        n_long=f"{len(lg):,}", n_sp=f"{len(sp):,}", sp_strict_n=f"{int(os_strict['trades']) if os_strict is not None else 0}",
        corr_long=f"{corr_long:.2f}", corr_sp=f"{corr_sp:.2f}",
        ad_share=f"{100 * ad_share:.0f}%", ad_mean=f"{ad_mean:+.2f}R", fx_mean=f"{fx_mean:+.2f}R", ad_pos=f"{ad_pos}",
        seq_i=seq_i_html, seq_im=seq_im_html, seq_p=seq_p_html,
        heat_gross=grid_heatmap(s1, "intraday", "avg_R_gross", "margin"),
        promo=promotion_table(p4), exits=exit_study_table(s2), opt_table=opt_table,
        eq_svg=eq_svg, mr_svg=mr_svg, reg_table=reg_table, port_main=port_main, sens_table=sens_table, cfg_table=cfg_table,
        tf_table=table(["Intraday timeframe"] + bd_head[1:], tf_rows), thr_table=table(["Trend-score filter"] + bd_head[1:], thr_rows),
        side_table=table(["Direction"] + bd_head[1:], side_rows + rnd_rows),
    )
    html = TEMPLATE
    for k, v in ctx.items():
        html = html.replace("{{" + k + "}}", v)
    with open(out_path, "w") as fh:
        fh.write(html)
    print("wrote", out_path)


from pathlib import Path  # noqa: E402

TEMPLATE = (Path(__file__).parent / "report_template.html").read_text()

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(RESULTS_DIR / "report.html"))
    build(ap.parse_args().out)
