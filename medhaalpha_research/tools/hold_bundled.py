# Multi-day holds for the trades the scanner's own six-month report took (live rule, real contract month),
# 1 Sep - 19 Oct 2026. The September/October futures candles have expired, so each trade is followed on its
# cash share: levels (stop, T1-T3) are rebuilt by the scanner's own level code at the report's signal minute
# on the cash series, then held with fills.run_policies without the end-of-day square-off (the live ledger's
# method). Check: the same-day R on cash is compared with the report's own R for every trade.
import json, os, pickle, sys, time, urllib.parse, urllib.request
from datetime import date
import pandas as pd
from scanner.series import candles_to_df
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import LONG, SHORT, build_context, intraday_base, non_sessions, regular, side_view, snapshot
from scanner.equity.fills import run_policies
from scanner.equity.levels import build_levels
from scanner.equity.scan import lots_for

six_path, rdir, out_json = sys.argv[1], sys.argv[2], sys.argv[3]
LO, HI = "2026-09-01", "2026-10-19"
cfg = EqConfig()
d = json.load(open(six_path))
six, sig = d["six"], d["sig"]
MI = {m: i for i, m in enumerate(sig["models"])}
PI = {p: i for i, p in enumerate(sig["policies"])}
THR = {m: six["models"][m]["min_score"] for m in six["models"]}
N = six["top_n"]
MS = ("opus", "fable_op")
pk = pickle.load(open(os.path.join(rdir, "minutes.pkl"), "rb"))
raw, cash_key, lotinfo, sessions = pk["minutes"], pk["cash_key"], pk["lot"], pk["sessions"]
nifty = raw[[k for k in raw if k.startswith("NSE_FO")][0]]
skip = non_sessions(nifty, cfg)
nreg = regular(nifty, cfg)
cnt = nreg.groupby(nreg.index.date).size()
alld = sorted(cnt.index)
full = [x for x in alld if cnt[x] >= cfg.min_session_candles]
print("data to", alld[-1], "| short sessions", [str(x) for x in alld if x not in full])


def days_after(ed, xd):
    n = sum(1 for x in full if ed < x <= xd)
    return n + (1 if xd not in full and xd > ed else 0)


def live_b(sigs, m):
    pool = [s for s in sigs if s[2] in ("A", "B") and s[4][PI["T1"]] is not None]
    out = []
    for s in sorted(pool, key=lambda s: (s[0], -s[3][MI[m]], s[1])):
        if s[3][MI[m]] >= THR[m] and len(out) < N:
            out.append(s)
    return out


trades = {}
days = []
for x in sig["days"]:
    if not (LO <= x["day"] <= HI):
        continue
    days.append(x["day"])
    for m in MS:
        for s in live_b(x["signals"], m):
            trades.setdefault((x["day"], s[1], s[2], s[0]), {"s": s, "models": []})["models"].append(m)
if os.environ.get("ONLY"):                      # follow just these signals: [[day, symbol, setup, time], ...]
    want = {tuple(k) for k in json.loads(os.environ["ONLY"])}
    trades = {}
    for x in sig["days"]:
        for s in x["signals"]:
            if (x["day"], s[1], s[2], s[0]) in want:
                trades[(x["day"], s[1], s[2], s[0])] = {"s": s, "models": ["split"]}
print("sessions", len(days), "| trades", len(trades), "| symbols", len({k[1] for k in trades}))


def get(url):
    for a in range(4):
        try:
            time.sleep(0.25)
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/8"})
            return json.load(urllib.request.urlopen(req, timeout=40))["data"]["candles"]
        except Exception as e:  # noqa: BLE001
            if a == 3:
                raise
            time.sleep(1.5 * (a + 1))


daily, reg = {}, {}
rows, notes, cmp_rows = [], [], []
for (day, sym, setup, tm), t in sorted(trades.items()):
    s = t["s"]
    if sym not in cash_key or cash_key[sym] not in raw:
        notes.append("no cash data: %s %s" % (day, sym))
        continue
    ck = cash_key[sym]
    if sym not in daily:
        daily[sym] = candles_to_df(get("https://api.upstox.com/v3/historical-candle/%s/days/1/%s/%s" % (urllib.parse.quote(ck, safe=""), HI, "2025-04-20")))
        reg[sym] = regular(raw[ck], cfg)
    dd = date.fromisoformat(day)
    side = LONG if setup == "A" else SHORT
    ctx = build_context(sym, dd, daily[sym], raw[ck], None, nifty, cfg, sessions, skip)
    assert ctx.price_basis == "cash"
    base = intraday_base(ctx, None, raw[ck], nifty, cfg)
    view = side_view(base, ctx, side, cfg)
    ts = pd.Timestamp("%sT%s:00+05:30" % (day, tm))
    if ts not in view.index:
        notes.append("no cash candle at the signal minute: %s %s %s" % (day, sym, tm))
        continue
    i = view.index.get_loc(ts)
    snap = snapshot(view, base, ctx, i)
    lot, tick = lotinfo[sym]
    lv = build_levels(side, snap["price"], snap.get("atr_pct") or 0.0, snap, tick, cfg)
    lots = lots_for(side, lv.entry_ref, lv.stop, lot, cfg)
    if lots == 0:
        notes.append("one lot over the risk budget on cash levels, taken at 1 lot: %s %s" % (day, sym))
        lots = 1
    qty = lot * lots
    ets = ts + pd.Timedelta(minutes=1)
    m = reg[sym]
    intr = run_policies(m, side, lv.stop, lv.targets, ets, close_at_eod=True)
    outs = run_policies(m, side, lv.stop, lv.targets, ets, close_at_eod=False, trail=True)
    if outs["T1"].status == "no_data":
        notes.append("no candles after entry: %s %s" % (day, sym))
        continue

    def net_of(o):
        gross = o.points * qty
        return round(gross - C.round_trip("FUT", o.entry, o.exit, qty, side, cfg.brokerage_per_order, cfg.brokerage_pct)
                     - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)

    res = {}
    for pol, o in outs.items():
        res[pol] = {"status": o.status, "entry": o.entry, "exit": o.exit, "exit_ts": o.exit_ts, "reason": o.reason, "r": o.r, "net_rs": net_of(o),
                    "sessions": days_after(ets.date(), pd.Timestamp(o.exit_ts).date())}
    w = m[(m.index >= ets) & (m.index <= pd.Timestamp(outs["T3"].exit_ts))]
    dc, do = w["close"].groupby(w.index.date).last(), w["open"].groupby(w.index.date).first()
    jump = max([abs(do.iloc[k] / dc.iloc[k - 1] - 1) * 100 for k in range(1, len(dc))] or [0.0])
    if jump > 12:
        notes.append("overnight jump %.1f%% while held (possible split/bonus): %s %s" % (jump, day, sym))
    cmp_rows.append({"day": day, "symbol": sym, "models": t["models"],
                     "r_cash": {p: intr[p].r for p in ("T1", "T2", "T3", "CLOSE")}, "r_rep": {p: s[5][PI[p]] for p in ("T1", "T2", "T3", "CLOSE")},
                     "net_cash": {p: net_of(intr[p]) for p in ("T1", "T2", "T3", "CLOSE")}, "net_rep": {p: s[4][PI[p]] for p in ("T1", "T2", "T3", "CLOSE")}})
    rows.append({"day": day, "time": tm, "symbol": sym, "setup": setup, "side": side, "qty": qty, "lot": lot, "lots": lots, "models": t["models"],
                 "scores": dict(zip(sig["models"], s[3])), "basis": "cash", "stop": lv.stop, "t1": lv.targets[0], "t2": lv.targets[1], "t3": lv.targets[2],
                 "entry_ts": ets.isoformat(), "res": res,
                 "intraday": {p: {"status": intr[p].status, "net_rs": net_of(intr[p])} for p in ("T1", "T2", "T3", "CLOSE")},
                 "report": {p: {"net_rs": s[4][PI[p]], "r": s[5][PI[p]]} for p in ("T1", "T2", "T3", "CLOSE")}})
print("rows", len(rows), "| notes", len(notes))
for n in notes:
    print("  NOTE", n)
# check: cash-followed same-day result against the report's own (real contract) result
for m in MS:
    cr = [c for c in cmp_rows if m in c["models"]]
    for per, lo, hi in (("Sep", "2026-09-01", "2026-09-30"), ("Oct 1-19", "2026-10-01", "2026-10-19")):
        x = [c for c in cr if lo <= c["day"] <= hi]
        if not x:
            continue
        line = ["%-8s %-8s n=%3d" % (m, per, len(x))]
        for p in ("T1", "T2", "T3", "CLOSE"):
            line.append("%s cash %+8.0f report %+8.0f (R %+5.1f vs %+5.1f)" % (p, sum(c["net_cash"][p] for c in x), sum(c["net_rep"][p] for c in x),
                                                                                 sum(c["r_cash"][p] for c in x), sum(c["r_rep"][p] for c in x)))
        close = sum(1 for c in x if abs(c["r_cash"]["T1"] - c["r_rep"]["T1"]) <= 0.25)
        line.append("T1 R within 0.25 on %d of %d" % (close, len(x)))
        print(" | ".join(line))
json.dump({"days": days, "full": [x.isoformat() for x in full], "rows": rows, "notes": notes, "cmp": cmp_rows}, open(out_json, "w"))
