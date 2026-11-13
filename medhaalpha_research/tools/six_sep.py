import json, sys
d = json.load(open(sys.argv[1]))
six, sig = d["six"], d["sig"]
MS = ("opus", "fable_op")
print("== months, live rule, net Rs (intraday, squared off at the close), real contract month")
for m in six["months"]:
    row = [m["month"], "days %2d" % m["days"], "nifty %+6.2f%%" % m["nifty_pct"]]
    for k in MS:
        t = m["totals"][k]["live"]
        row.append("%s n=%3d hit=%3d stop=%3d T1 %+8.0f T2 %+8.0f T3 %+8.0f CLOSE %+8.0f" % (k, t["n"], t["t1_hit"], t["t1_stopped"], t["T1"], t["T2"], t["T3"], t["CLOSE"]))
    print(" | ".join(row))
for name in ("totals", "totals_unseen", "totals_in_sample"):
    for k in MS:
        t = six[name][k]["live"]
        print(name, k, {x: t[x] for x in ("n", "t1_hit", "t1_stopped", "t1_won", "T1", "T2", "T3", "CLOSE", "T2_TR", "T3_TR")}, "days+", t.get("days_positive", {}).get("T1"), "maxDD", t.get("max_drawdown"), "worst", t.get("worst_day"))
print()
print("== September by day, live rule")
tot = {k: {"n": 0, "hit": 0, "stop": 0, "T1": 0, "T2": 0, "T3": 0, "CLOSE": 0} for k in MS}
for r in six["summary"]:
    if not r["day"].startswith("2026-09"):
        continue
    row = [r["day"]]
    for k in MS:
        c = r["models"][k]["live"]
        row.append("%s n=%d hit=%d stop=%d T1 %+7.0f T2 %+7.0f T3 %+7.0f CL %+7.0f" % (k, c["n"], c["t1_hit"], c["t1_stopped"], c["T1"], c["T2"], c["T3"], c["CLOSE"]))
        for a, b in (("n", "n"), ("hit", "t1_hit"), ("stop", "t1_stopped"), ("T1", "T1"), ("T2", "T2"), ("T3", "T3"), ("CLOSE", "CLOSE")):
            tot[k][a] += c[b]
    print(" | ".join(row))
print(tot)
sep = next(m for m in six["months"] if m["month"] == "2026-09")
for k in MS:
    print(k, json.dumps(sep["totals"][k]["live"]))
print(json.dumps(sep["setups"])[:1500])
