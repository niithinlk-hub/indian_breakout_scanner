# Parse the dry-run container's log dump (Hostinger API JSON) and render tables; then a local what-if at lower thresholds.
import gzip, json, os, sys, time, urllib.parse, urllib.request
import pandas as pd
from scanner.config import IST
from scanner.series import candles_to_df
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import run_policies
from scanner.equity.universe_upstox import parse

dump, tag, inst = sys.argv[1], sys.argv[2], sys.argv[3]
cfg = EqConfig()
d = json.load(open(dump))
lines = [e["line"] for svc in d if svc["service"].startswith("dryrun") for e in svc["entries"]]
a = max(i for i, l in enumerate(lines) if l.startswith("===HEAD " + tag + " "))
b = next(i for i in range(a, len(lines)) if lines[i].startswith("===END " + tag))
head = json.loads(lines[a].split(" ", 2)[2])
body = lines[a + 1:b]
sig = [json.loads(l[4:]) for l in body if l.startswith("SIG ")]
dry = [json.loads(l[4:]) for l in body if l.startswith("DRY ")]
live = [json.loads(l[5:]) for l in body if l.startswith("LIVE ")]
notes = [json.loads(l[6:]) for l in body if l.startswith("NOTES ")]
print("script hash line:", [l for l in lines if l.startswith("script sha256")][-1])
print("HEAD", json.dumps(head))
print("notes", notes)
hm = lambda ts: pd.Timestamp(ts).strftime("%H:%M")
print("\nall %d signals (time symbol setup lots | opus action | fable_op action | parts)" % len(sig))
for s in sig:
    print("%s %-11s %s %s | %5.1f %-11s | %5.1f %-11s | %s" % (hm(s["ts"]), s["symbol"], s["setup"], s["lots"], s["live_score"], s["live_action"],
                                                             s["dry_score"], s["dry_action"], s["parts"]))
print("stored fable_op scores:", sum(1 for s in sig if (s["scores"] or {}).get("fable_op") is not None), "of", len(sig))
print("\ndry-run picks:", len(dry))
for x in dry:
    f, o = (x["dry"].get("fut") or {}).get("T1", {}), (x["dry"].get("opt") or {}).get("T1", {})
    print(hm(x["ts"]), x["symbol"], x["lots"], f.get("status"), f.get("entry"), f.get("exit"), f.get("r"), f.get("net_rs"), "| opt", o.get("status"), o.get("net_rs"))
print("\nlive paper ledger (model %s)" % head["live_models"])
tot = {}
for x in live:
    row = []
    for p in ("T1", "T2", "T3", "T2_TR", "T3_TR"):
        f, o = x["legs"].get("FUT", {}).get("outcomes", {}).get(p, {}), x["legs"].get("OPT", {}).get("outcomes", {}).get(p, {})
        tot.setdefault(p, [0.0, 0.0])
        tot[p][0] += f.get("net_rs") or 0
        tot[p][1] += o.get("net_rs") or 0
        if p == "T1":
            row = [hm(x["ts"]), x["symbol"], x["legs"].get("FUT", {}).get("qty"), f.get("status"), f.get("entry"), f.get("exit"), hm(f["exit_ts"]) if f.get("exit_ts") else "", f.get("r"),
                   f.get("net_rs"), "| opt", o.get("status"), o.get("entry"), o.get("exit"), o.get("net_rs")]
    print(*row)
print("live totals by exit policy (futures net, options net):", {p: [round(v[0]), round(v[1])] for p, v in tot.items()})

if len(sys.argv) > 4:                                    # what-if at lower thresholds, futures leg, public candles
    uni = parse(json.loads(gzip.decompress(open(inst, "rb").read())))
    day = pd.Timestamp(head["day"]).date()
    cut = pd.Timestamp(head["cut"])

    def candles(key):
        req = urllib.request.Request("https://api.upstox.com/v3/historical-candle/intraday/" + urllib.parse.quote(key, safe="") + "/minutes/1",
                                     headers={"Accept": "application/json", "User-Agent": "curl/8"})
        time.sleep(0.4)
        return regular(candles_to_df(json.load(urllib.request.urlopen(req, timeout=30))["data"]["candles"]), cfg)

    def groups(sigs):
        out, cur, t0 = [], [], None
        for s in sorted(sigs, key=lambda s: s["logged_at"]):
            t = pd.Timestamp(s["logged_at"])
            if t0 is None or (t - t0).total_seconds() > 30:
                cur, t0 = [], t
                out.append(cur)
            cur.append(s)
        return out
    priced = {}
    for thr in [float(x) for x in sys.argv[4].split(",")]:
        fired = []
        for g in groups(sig):
            for s in sorted(g, key=lambda s: (-s["dry_score"], -(s["rel_vol"] or 0))):
                if s["dry_score"] >= thr and s["lots"] and len(fired) < cfg.top_n:
                    fired.append(s)
        tot_net, rows_ = 0.0, []
        for s in fired:
            if s["symbol"] not in priced:
                fut = uni.pick_future(s["symbol"], day, cfg.roll_sessions)
                assert fut.trading_symbol == s["fut_symbol"], (fut.trading_symbol, s["fut_symbol"])
                m = candles(fut.key)
                lv = s["levels"]
                o = run_policies(m[m.index <= cut], s["side"], lv["stop"], [lv["t1"], lv["t2"], lv["t3"]], pd.Timestamp(s["ts"]) + pd.Timedelta(minutes=1), trail=True)["T1"]
                qty = fut.lot_size * s["lots"]
                net = round(o.points * qty - C.round_trip("FUT", o.entry, o.exit, qty, s["side"], cfg.brokerage_per_order, cfg.brokerage_pct)
                            - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
                priced[s["symbol"]] = (o, qty, net)
            o, qty, net = priced[s["symbol"]]
            tot_net += net
            rows_.append("   %s %-11s score %5.1f qty %-5s entry %-8s exit %-8s %-7s %s R %+.2f net %+.0f" % (
                hm(s["ts"]), s["symbol"], s["dry_score"], qty, o.entry, o.exit, o.status, hm(o.exit_ts), o.r, net))
        print("\nwhat-if fable_op >= %g: %d trades, futures net at T1 %+.0f" % (thr, len(fired), tot_net))
        print("\n".join(rows_))
