# Feature snapshot for every A/B signal in the scanner's six-month file, rebuilt with the scanner's own feature
# code at the signal minute. The traded-instrument features are taken from the cash share (the expired futures
# cannot be read); everything else (RSI, ATR, 20-day, 52-week, relative volume, break count) is cash-based in
# the live scanner too. Also the day's breadth and how many signals had already fired.
import os, pickle, sys, time
from datetime import date, timedelta
import numpy as np
import pandas as pd
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
sys.path.insert(0, sys.argv[1] + "/v2")
from base import SIG, SP, PI, MI, classify
from scanner.series import merge_frames
from scanner.equity.config import EqConfig
from scanner.equity.features import LONG, SHORT, build_context, intraday_base, non_sessions, regular, session_days, side_view, snapshot
from scanner.equity.levels import build_levels
from scanner.equity.score import all_scores

cfg = EqConfig()
early = pickle.load(open(SP + "/v2/data/early.pkl", "rb"))
late = pickle.load(open(SP + "/replay_sep/minutes.pkl", "rb"))
keys, daily, nifty = early["keys"], early["daily"], early["nifty"]
mins = {}
for s, k in keys.items():
    mins[s] = regular(merge_frames(early["minutes"].get(k), late["minutes"].get(k)), cfg)
del early, late
nifty = regular(nifty, cfg)
sessions, skip = session_days(nifty, cfg), non_sessions(nifty, cfg)
print("stocks", len(mins), "| sessions", len(sessions), sessions[0], sessions[-1], "| short sessions", sorted(skip), flush=True)
dayint = {s: (df.index.year * 10000 + df.index.month * 100 + df.index.day).to_numpy() for s, df in mins.items()}
nint = (nifty.index.year * 10000 + nifty.index.month * 100 + nifty.index.day).to_numpy()


def di(d):
    return d.year * 10000 + d.month * 100 + d.day


def window(sym, lo, hi):
    a = dayint[sym]
    return mins[sym].iloc[np.searchsorted(a, di(lo), "left"):np.searchsorted(a, di(hi), "right")]


def nwin(lo, hi):
    return nifty.iloc[np.searchsorted(nint, di(lo), "left"):np.searchsorted(nint, di(hi), "right")]


def breadth_for(day):
    """Per minute: share of stocks above their previous session's close, and the median % change."""
    prev = [d for d in sessions if d < day]
    if not prev:
        return None
    pd_ = prev[-1]
    grid = pd.date_range(pd.Timestamp(day.isoformat() + "T09:15:00+05:30"), periods=375, freq="min")
    cols = []
    for s in mins:
        p = window(s, pd_, pd_)
        t = window(s, day, day)
        if p.empty or t.empty:
            continue
        cols.append((t["close"].reindex(grid).ffill() / float(p["close"].iloc[-1]) - 1) * 100)
    m = pd.concat(cols, axis=1)
    return pd.DataFrame({"up": (m > 0).sum(axis=1) / m.notna().sum(axis=1), "med": m.median(axis=1),
                         "strong_up": (m > 1.0).sum(axis=1) / m.notna().sum(axis=1), "strong_dn": (m < -1.0).sum(axis=1) / m.notna().sum(axis=1)})


out, t0, miss = [], time.time(), 0
for n, x in enumerate(SIG["days"]):
    day = date.fromisoformat(x["day"])
    sigs = [s for s in x["signals"] if s[2] in ("A", "B") and s[4][PI["T1"]] is not None]
    br = breadth_for(day)
    nw = nwin(day - timedelta(days=12), day)
    nday = nw[nw.index.date == day]
    order = sorted(sigs, key=lambda s: (s[0], s[1]))
    for s in sigs:
        tm, sym, setup = s[0], s[1], s[2]
        side = LONG if setup == "A" else SHORT
        cm = window(sym, day - timedelta(days=16), day)
        if cm.empty or sym not in daily:
            miss += 1
            continue
        ctx = build_context(sym, day, daily[sym], cm, None, nw, cfg, sessions, skip)
        base = intraday_base(ctx, None, cm, nw, cfg)
        ts = pd.Timestamp("%sT%s:00+05:30" % (x["day"], tm))
        if base.empty or ts not in base.index or ctx.daily is None or ctx.prev_close is None:
            miss += 1
            continue
        view = side_view(base, ctx, side, cfg)
        i = view.index.get_loc(ts)
        snap = snapshot(view, base, ctx, i)
        lv = build_levels(side, snap["price"], snap.get("atr_pct") or 0.0, snap, 0.05, cfg)
        sc = all_scores(snap, side, lv.chosen, lv.risk, lv.entry_ref, cfg)
        sg = 1 if side == LONG else -1
        b = br.loc[ts] if br is not None and ts in br.index else None
        nopen = float(nday["open"].iloc[0]) if not nday.empty else None
        nnow = nday["close"].reindex([ts], method="ffill").iloc[0] if not nday.empty else None
        earlier = [q for q in order if q[0] < tm]
        f = dict(snap)
        f.update({
            "risk_pct": lv.risk / lv.entry_ref * 100 if lv.entry_ref else None, "structure": 0.0 if (lv.chosen or "").startswith("fallback") else 1.0,
            "stop_at": lv.chosen, "range_atr": (snap["hi"] - snap["lo"]) / snap["price"] * 100 / snap["atr_pct"] if snap.get("atr_pct") else None,
            "nifty_dir": sg * snap["nifty_chg"] if snap.get("nifty_chg") is not None else None,
            "nifty_from_open": sg * (nnow / nopen - 1) * 100 if nopen and nnow == nnow else None,
            "breadth_dir": (b["up"] if sg > 0 else 1 - b["up"]) if b is not None else None,
            "breadth_med_dir": sg * b["med"] if b is not None else None,
            "strong_dir": (b["strong_up"] if sg > 0 else b["strong_dn"]) if b is not None else None,
            "crowd_same": sum(1 for q in earlier if q[2] == setup), "crowd_all": len(earlier), "same_minute": sum(1 for q in order if q[0] == tm) - 1,
            "or_break": (sg * (snap["price"] / (snap["or_high"] if sg > 0 else snap["or_low"]) - 1) * 100) if snap.get("or_high") and snap.get("or_low") else None,
        })
        out.append({"day": x["day"], "time": tm, "symbol": sym, "setup": setup, "side": side, "true": dict(zip(SIG["models"], s[3])),
                    "cash": {m: sc[m]["score"] for m in sc}, "cash_parts": {m: sc[m]["parts"] for m in sc}, "net": s[4], "r": s[5], "out": classify(s[5]), "f": f})
    if n % 10 == 0:
        print("   %s %d/%d rows %d miss %d %.0fs" % (x["day"], n + 1, len(SIG["days"]), len(out), miss, time.time() - t0), flush=True)
pickle.dump(out, open(SP + "/v2/data/feat.pkl", "wb"), protocol=5)
print("DONE rows", len(out), "missing", miss, "in %.0fs" % (time.time() - t0), flush=True)
