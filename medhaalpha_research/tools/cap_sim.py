# Opus and Fable-OP over 1 Sep - 13 Nov 2026: multi-day holds (T1/T2/T3) and what a fixed Rs 3 lakh of
# futures margin per method could actually have carried.
import glob, json, os, sys
import pandas as pd
sp = sys.argv[1]
CAP = float(os.environ.get("CAP", 300000))
cash = json.load(open(os.path.join(sp, "hold_sep.json")))
fut = json.load(open(os.path.join(sp, "t3_hold.json")))
lotmap = {}
for d in ("replay_oct", "replay_nov2", "replay7"):
    for p in glob.glob(os.path.join(sp, d, "replay_*.json")):
        j = json.load(open(p))
        for s in j["signals"]:
            lotmap[(j["day"], s["symbol"], s["time"], s["setup"])] = (s["lot"], s["lots"])
rows = list(cash["rows"])
for r in fut["rows"]:
    r = dict(r)
    r["lot"], r["lots"] = lotmap[(r["day"], r["symbol"], r["time"], r["setup"])]
    assert r["lot"] * r["lots"] == r["qty"]
    r["entry_ts"] = (pd.Timestamp("%sT%s:00+05:30" % (r["day"], r["time"])) + pd.Timedelta(minutes=1)).isoformat()
    rows.append(r)
days = sorted(set(cash["days"]) | set(fut["days"]))
NS = len(days)
print("sessions", NS, days[0], "->", days[-1], "| trades", len(rows))
MS = ("opus", "fable_op")
PERIODS = (("Sep", "2026-09-01", "2026-09-30"), ("Oct", "2026-10-01", "2026-10-31"), ("Nov", "2026-11-01", "2026-11-30"), ("All", "2026-09-01", "2026-11-30"))


def summ(tr, pol):
    x = [r["res"][pol] for r in tr]
    hit = [a for a in x if a["status"] == "target"]
    return {"n": len(x), "hit": len(hit), "stopped": sum(a["status"] == "stopped" for a in x), "open": sum(a["status"] == "open" for a in x),
            "net": round(sum(a["net_rs"] for a in x)), "r": round(sum(a["r"] for a in x), 1),
            "days_hist": [sum(1 for a in hit if a["sessions"] == k) for k in range(5)] + [sum(1 for a in hit if a["sessions"] >= 5)],
            "max_days": max([a["sessions"] for a in hit] or [0])}


out = {"sessions": NS, "days": days, "hold": {}, "cap": {}}
for m in MS:
    for name, lo, hi in PERIODS:
        tr = [r for r in rows if m in r["models"] and lo <= r["day"] <= hi]
        nd = sum(1 for d in days if lo <= d <= hi)
        for pol in ("T1", "T2", "T3"):
            s = summ(tr, pol)
            out["hold"]["%s|%s|%s" % (m, name, pol)] = {**s, "sessions": nd}
            print("%-8s %-3s (%2d sessions) %s: n=%3d hit=%3d stop=%3d open=%d net %+9d per trade %+6d R %+6.1f | days to target %s max %d" % (
                m, name, nd, pol, s["n"], s["hit"], s["stopped"], s["open"], s["net"], s["net"] / max(1, s["n"]), s["r"], s["days_hist"], s["max_days"]))
    print()


def sim(tr, pol, cap, rate):
    """Fixed capital. Trades in entry order; a trade is taken only if its margin (rate x contract value) is free;
    2-lot trades fall back to 1 lot. Margin frees at the exit minute. cap None = take everything."""
    evs = sorted(tr, key=lambda r: r["entry_ts"])
    openp, taken, skipped, peak, peak_n = [], [], 0, 0.0, 0
    for r in evs:
        et = pd.Timestamp(r["entry_ts"])
        openp = [(x, mg) for x, mg in openp if x > et]
        used = sum(mg for _, mg in openp)
        res = r["res"][pol]
        lots = r["lots"]
        while lots >= 1:
            mg = rate * res["entry"] * r["lot"] * lots
            if cap is None or cap - used >= mg:
                break
            lots -= 1
        if lots == 0:
            skipped += 1
            continue
        openp.append((pd.Timestamp(res["exit_ts"]), mg))
        peak, peak_n = max(peak, used + mg), max(peak_n, len(openp))
        taken.append({"day": r["day"], "symbol": r["symbol"], "exit_ts": res["exit_ts"], "status": res["status"],
                      "net": res["net_rs"] * lots / r["lots"], "lots": lots, "margin": mg})
    eq, hi, dd = 0.0, 0.0, 0.0
    for t in sorted(taken, key=lambda t: t["exit_ts"]):
        eq += t["net"]
        hi = max(hi, eq)
        dd = min(dd, eq - hi)
    bym = {}
    for t in taken:
        k = t["day"][:7]
        bym.setdefault(k, [0, 0.0])
        bym[k][0] += 1
        bym[k][1] += t["net"]
    return {"taken": len(taken), "skipped": skipped, "net": round(sum(t["net"] for t in taken)), "hit": sum(t["status"] == "target" for t in taken),
            "stopped": sum(t["status"] == "stopped" for t in taken), "open": sum(t["status"] == "open" for t in taken),
            "peak_margin": round(peak), "peak_open": peak_n, "max_dd": round(dd), "by_month": {k: [v[0], round(v[1])] for k, v in sorted(bym.items())},
            "avg_margin": round(sum(t["margin"] for t in taken) / max(1, len(taken))), "worst_trade": round(min([t["net"] for t in taken] or [0])),
            "per_session": round(sum(t["net"] for t in taken) / NS), "year": round(sum(t["net"] for t in taken) / NS * 250)}


for m in MS:
    tr = [r for r in rows if m in r["models"]]
    for pol in ("T1", "T2", "T3"):
        for rate in (0.15, 0.20, 0.25):
            for cap in (None, CAP):
                if cap is None and rate != 0.20:
                    continue
                s = sim(tr, pol, cap, rate)
                out["cap"]["%s|%s|%s|%s" % (m, pol, rate, "all" if cap is None else int(cap))] = s
                print("%-8s %s margin %2d%% cap %-9s: taken %3d skipped %3d | hit %3d stop %3d open %d | net %+9d | per session %+6d -> 250 sessions %+10d | max drawdown %+8d | worst trade %+7d | peak margin %9d (%d open) avg margin %d | %s" % (
                    m, pol, rate * 100, "none" if cap is None else "%d" % cap, s["taken"], s["skipped"], s["hit"], s["stopped"], s["open"], s["net"], s["per_session"], s["year"],
                    s["max_dd"], s["worst_trade"], s["peak_margin"], s["peak_open"], s["avg_margin"], s["by_month"]))
    print()
json.dump(out, open(os.path.join(sp, "cap_sim.json"), "w"))
