import glob, json, os, sys
src, out, title, note = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
days = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(src, "replay_*.json")))]
L = ["# " + title, "",
     "Scanner's own replay code and default rules (setups A + B, scan 09:17 to 14:15, at most 6 trades a day, risk budget Rs 15,000 a trade).",
     "Live rule: first 6 signals of the day scoring at or above 75. Entry at the next minute's open, anything still open squared off at the close.",
     "Net figures are futures rupees after charges and assumed slippage, exiting at T1 (1R). " + note, "",
     "## By session", "", "| Session | Signals | Opus trades | Opus T1 hit / stopped / closed at EOD | Opus futures net | Fable-OP trades | Fable-OP T1 hit / stopped / closed at EOD | Fable-OP futures net |",
     "|---|---|---|---|---|---|---|---|"]
tot = {m: [0, 0, 0, 0, 0.0] for m in ("opus", "fable_op")}
for p in days:
    row = [p["day"], str(sum(1 for s in p["signals"] if s["enabled"]))]
    for m in ("opus", "fable_op"):
        sel = p["models"][m]["selections"]["live"]
        t1 = sel["futures"]["T1"]
        row += [str(sel["n"]), "%d / %d / %d" % (t1["target"], t1["stopped"], t1["close"]), "{:+,.0f}".format(t1["net_rs"])]
        for i, v in enumerate((sel["n"], t1["target"], t1["stopped"], t1["close"], t1["net_rs"])):
            tot[m][i] += v
    L.append("| " + " | ".join(row) + " |")
o, f = tot["opus"], tot["fable_op"]
L.append("| **Total** | | **%d** | **%d / %d / %d** | **%s** | **%d** | **%d / %d / %d** | **%s** |" % (
    o[0], o[1], o[2], o[3], "{:+,.0f}".format(o[4]), f[0], f[1], f[2], f[3], "{:+,.0f}".format(f[4])))
for m, name in (("fable_op", "Fable-OP"), ("opus", "Opus")):
    L += ["", "## %s trades" % name, "", "| Date | Time | Symbol | Setup | Side | Qty | Score | Entry | Stop | T1 | Result | Exit time | R | Futures net |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in days:
        for s in p["signals"]:
            if "live" in s["in"][m]:
                t = s["fut"]["T1"]
                L.append("| %s | %s | %s | %s | %s | %d | %.1f | %s | %s | %s | %s | %s | %+.2f | %s |" % (
                    p["day"][5:], s["time"], s["symbol"], s["setup"], s["side"], s["lot"] * (s["lots"] or 0), s["scores"][m], t["entry"], s["stop"], s["t1"],
                    {"target": "T1 hit", "stopped": "stopped", "close": "closed at EOD"}.get(t["status"], t["status"]), t["exit_ts"][11:16], t["r"], "{:+,.0f}".format(t["net_rs"])))
open(out, "w").write("\n".join(L) + "\n")
print(out, len(L), "lines | totals", {k: [v[0], v[1], v[2], v[3], round(v[4])] for k, v in tot.items()})
