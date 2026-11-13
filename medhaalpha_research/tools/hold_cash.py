# Multi-day hold (the live paper ledger's method: fills.run_policies without the end-of-day square-off) for the
# trades the live rule picks in each cash-basis replay day. Output rows have the same shape as t3_hold.json.
import glob, json, os, pickle, sys
import pandas as pd
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import run_policies

rdir, out_json = sys.argv[1], sys.argv[2]
cfg = EqConfig()
pk = pickle.load(open(os.path.join(rdir, "minutes.pkl"), "rb"))
raw, cash_key = pk["minutes"], pk["cash_key"]
days = sorted((json.load(open(p)) for p in glob.glob(os.path.join(rdir, "replay_*.json"))), key=lambda p: p["day"])
print("sessions:", len(days), days[0]["day"], "->", days[-1]["day"])
MODELS = ("opus", "fable_op")
reg = {}


def series(sym):
    k = cash_key[sym]
    if k not in reg:
        reg[k] = regular(raw[k], cfg)
    return reg[k]


count = {}
nk = [k for k in raw if k.startswith("NSE_FO")]
for k in nk:
    c = regular(raw[k], cfg)
    for d, n in c.groupby(c.index.date).size().items():
        count[d] = max(count.get(d, 0), n)
sessions = sorted(count)
full = [d for d in sessions if count[d] >= cfg.min_session_candles]
print("data to", sessions[-1], "| short sessions:", [str(d) for d in sessions if d not in full])


def days_after(ed, xd):
    n = sum(1 for d in full if ed < d <= xd)
    return n + (1 if xd not in full and xd > ed else 0)


rows, bad, gaps = [], 0, []
for p in days:
    for s in p["signals"]:
        ms = [m for m in MODELS if "live" in s["in"][m]]
        if not ms:
            continue
        sym = s["symbol"]
        m = series(sym)
        ets = pd.Timestamp("%sT%s:00+05:30" % (p["day"], s["time"])) + pd.Timedelta(minutes=1)
        outs = run_policies(m, s["side"], s["stop"], [s["t1"], s["t2"], s["t3"]], ets, close_at_eod=False, trail=True)
        intr = s["fut"]["T1"]
        o1 = outs["T1"]
        if abs(o1.entry - intr["entry"]) > 1e-6 or (intr["status"] in ("target", "stopped") and (o1.status != intr["status"] or abs(o1.exit - intr["exit"]) > 1e-6)):
            bad += 1
            print("MISMATCH", p["day"], sym, o1.status, o1.entry, o1.exit, "vs replay", intr["status"], intr["entry"], intr["exit"])
        qty = s["lot"] * s["lots"]
        res = {}
        for pol, o in outs.items():
            gross = round(o.points * qty, 2)
            net = round(gross - C.round_trip("FUT", o.entry, o.exit, qty, s["side"], cfg.brokerage_per_order, cfg.brokerage_pct)
                        - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
            xd = pd.Timestamp(o.exit_ts).date()
            res[pol] = {"status": o.status, "entry": o.entry, "exit": o.exit, "exit_ts": o.exit_ts, "reason": o.reason, "r": o.r, "net_rs": net,
                        "sessions": days_after(ets.date(), xd)}
        # a split or bonus would show as a huge overnight jump in the cash series: flag anything over 12 %
        w = m[(m.index >= ets) & (m.index <= pd.Timestamp(outs["T3"].exit_ts))]
        dc = w["close"].groupby(w.index.date).last()
        do = w["open"].groupby(w.index.date).first()
        jump = max([abs(do.iloc[i] / dc.iloc[i - 1] - 1) * 100 for i in range(1, len(dc))] or [0.0])
        if jump > 12:
            gaps.append((p["day"], sym, round(jump, 1)))
        rows.append({"day": p["day"], "time": s["time"], "symbol": sym, "setup": s["setup"], "side": s["side"], "qty": qty, "lot": s["lot"],
                     "lots": s["lots"], "models": ms, "scores": s["scores"], "basis": "cash", "stop": s["stop"], "t1": s["t1"], "t2": s["t2"],
                     "t3": s["t3"], "entry_ts": ets.isoformat(), "res": res,
                     "intraday": {pp: {"status": s["fut"][pp]["status"], "net_rs": s["fut"][pp]["net_rs"]} for pp in ("T1", "T2", "T3", "CLOSE")}})
print("trades", len(rows), "| data-check mismatches vs replay:", bad, "| overnight jumps over 12%:", gaps)
json.dump({"sessions": [d.isoformat() for d in sessions], "full": [d.isoformat() for d in full], "days": [p["day"] for p in days], "rows": rows}, open(out_json, "w"))
