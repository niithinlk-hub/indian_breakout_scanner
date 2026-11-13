import json, statistics, sys
doc = json.load(open(sys.argv[1])); out_md = sys.argv[2]
rows, sessions = doc["rows"], doc["sessions"]
NAME = {"opus": "Opus", "fable_op": "Fable-OP"}
fm = lambda x: "{:+,.0f}".format(x)
L = ["# Opus vs Fable-OP held for T3, 21 Oct to 13 Nov 2026", "",
     "Trades are the ones the live rule picks in each day's replay (first 6 signals scoring 75 or more). Each is held with its original stop until T3 (2.6R) or the stop, across days, with no square-off at the close: the method of the scanner's live paper ledger. Trades still open are marked to the 13 Nov close. Futures rupees after charges and assumed slippage.", ""]
summary = {}
for m in ("opus", "fable_op"):
    tr = [r for r in rows if m in r["models"]]
    print("\n=====", NAME[m], "trades", len(tr))
    for pol in ("T1", "T2", "T3", "T2_TR", "T3_TR"):
        x = [r["res"][pol] for r in tr]
        st = lambda k: sum(1 for v in x if v["status"] == k)
        print("  hold %-6s target %2d stopped %2d trail %2d open %2d | net %9s | R %+6.2f | per trade %7s | open marks %s" % (
            pol, st("target"), st("stopped"), st("trail"), st("open"), fm(sum(v["net_rs"] for v in x)), sum(v["r"] for v in x),
            fm(sum(v["net_rs"] for v in x) / len(x)), fm(sum(v["net_rs"] for v in x if v["status"] == "open"))))
    print("  same trades, squared off at each close (replay): T1 %s | T3 %s" % (fm(sum(r["intraday"]["T1"]["net_rs"] for r in tr)), fm(sum(r["intraday"]["T3"]["net_rs"] for r in tr))))
    t3 = [r["res"]["T3"] for r in tr]
    hit = [v["sessions"] for v in t3 if v["status"] == "target"]
    stp = [v["sessions"] for v in t3 if v["status"] == "stopped"]
    dist = lambda xs: {k: sum(1 for v in xs if (v == k if k < 5 else v >= 5)) for k in range(6)}
    print("  T3 hits by trading days after entry day (0 = same session, 5 = 5 or more):", dist(hit), "| mean %.1f median %s max %s" % (statistics.mean(hit), statistics.median(hit), max(hit)) if hit else "")
    print("  stops by trading days after entry day:", dist(stp))
    # peak number of trades open at once (session granularity)
    six = {d: i for i, d in enumerate(sessions)}
    peak = max(sum(1 for r in tr if six[r["day"]] <= i <= six[r["res"]["T3"]["exit_ts"][:10]]) for i in range(len(sessions)))
    print("  peak trades open in one session under the T3 hold:", peak)
    for lo, hi, lab in (("2026-10-21", "2026-10-30", "21-30 Oct"), ("2026-11-02", "2026-11-13", "2-13 Nov")):
        sub = [r for r in tr if lo <= r["day"] <= hi]
        print("   %s: trades %d | T3 hold net %s (T3 hit %d, stopped %d, open %d) | T1 hold net %s" % (
            lab, len(sub), fm(sum(r["res"]["T3"]["net_rs"] for r in sub)), sum(r["res"]["T3"]["status"] == "target" for r in sub),
            sum(r["res"]["T3"]["status"] == "stopped" for r in sub), sum(r["res"]["T3"]["status"] == "open" for r in sub), fm(sum(r["res"]["T1"]["net_rs"] for r in sub))))
    summary[m] = {"n": len(tr), "hit": hit, "stp": stp, "peak": peak}
    L += ["## %s: every trade, held for T3" % NAME[m], "", "| Entry date | Time | Symbol | Side | Qty | Score | Entry | Stop | T3 | Result | Exit date | Exit time | Trading days after entry day | R | Futures net |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in tr:
        v = r["res"]["T3"]
        L.append("| %s | %s | %s | %s | %d | %.1f | %s | %s | %s | %s | %s | %s | %d | %+.2f | %s |" % (
            r["day"][5:], r["time"], r["symbol"], r["side"], r["qty"], r["scores"][m], v["entry"], r["stop"], r["t3"],
            {"target": "T3 hit", "stopped": "stopped", "open": "still open"}[v["status"]], v["exit_ts"][5:10], v["exit_ts"][11:16], v["sessions"], v["r"], fm(v["net_rs"])))
    L.append("")
open(out_md, "w").write("\n".join(L) + "\n")
print("\nwrote", out_md)
for m in ("opus", "fable_op"):
    print("\nT3 hits,", NAME[m])
    for r in rows:
        v = r["res"]["T3"]
        if m in r["models"] and v["status"] == "target":
            print("  %s %s %-11s %-5s entered %s -> T3 %s %s (%d days) R %+.2f net %s" % (r["day"][5:], r["time"], r["symbol"], r["side"], v["entry"], v["exit_ts"][5:10], v["exit_ts"][11:16], v["sessions"], v["r"], fm(v["net_rs"])))
