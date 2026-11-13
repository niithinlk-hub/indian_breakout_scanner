import json, os, sys
sp = sys.argv[1]
d = json.load(open(os.path.join(sp, "six", "pull.json")))
six = d["six"]
hold = json.load(open(os.path.join(sp, "hold_sep.json")))
cap = json.load(open(os.path.join(sp, "cap_sim.json")))
boot = json.load(open(os.path.join(sp, "cap_boot.json")))
MS = (("opus", "Opus"), ("fable_op", "Fable-OP"))


def inr(x, sign=True):
    x = int(round(x))
    s = str(abs(x))
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if x < 0 else "+" if sign else "") + s


# ------------------------------------------------------------------ September
L = ["# Opus vs Fable-OP: September 2026 (21 sessions, Nifty -6.05 %)", ""]
L += ["Which trades each model took, and the same-day results, come from the scanner's own six-month backtest report stored on the VPS "
      "(generated 13 Nov 2026). That report was priced on the real September futures contracts, live rule (first 6 signals a day scoring 75 or more, "
      "setups A and B), lots sized to risk Rs 15,000 a trade, charges and 0.02 % slippage a side included, anything open squared off at the close. "
      "No option results: the September option contracts have expired.", ""]
sep = next(m for m in six["months"] if m["month"] == "2026-09")
L += ["## Same-day results (squared off at the close)", "", "| | Opus | Fable-OP |", "|---|---|---|"]
t = {k: sep["totals"][k]["live"] for k, _ in MS}
L.append("| Trades | %d | %d |" % (t["opus"]["n"], t["fable_op"]["n"]))
L.append("| Reached T1 | %d | %d |" % (t["opus"]["t1_hit"], t["fable_op"]["t1_hit"]))
L.append("| Stopped out | %d | %d |" % (t["opus"]["t1_stopped"], t["fable_op"]["t1_stopped"]))
L.append("| Squared off at the close | %d | %d |" % (t["opus"]["n"] - t["opus"]["t1_hit"] - t["opus"]["t1_stopped"], t["fable_op"]["n"] - t["fable_op"]["t1_hit"] - t["fable_op"]["t1_stopped"]))
for pol, lab in (("T1", "Net, exit at T1"), ("T2", "Net, hold for T2"), ("T3", "Net, hold for T3"), ("CLOSE", "Net, stop only, exit at the close")):
    L.append("| %s (Rs) | %s | %s |" % (lab, inr(t["opus"][pol]), inr(t["fable_op"][pol])))
L.append("| Net per trade at T1 (Rs) | %s | %s |" % (inr(t["opus"]["T1"] / t["opus"]["n"]), inr(t["fable_op"]["T1"] / t["fable_op"]["n"])))
L.append("| Days in profit at T1 | %d of 21 | %d of 21 |" % (t["opus"]["days_positive"]["T1"], t["fable_op"]["days_positive"]["T1"]))
L.append("| Worst day at T1 (Rs) | %s | %s |" % (inr(t["opus"]["worst_day"]["T1"]), inr(t["fable_op"]["worst_day"]["T1"])))
L += ["", "## Day by day, exit at T1, same day", "", "| Date | Opus trades | Opus T1 hit / stopped | Opus net (Rs) | Fable-OP trades | Fable-OP T1 hit / stopped | Fable-OP net (Rs) |", "|---|---|---|---|---|---|---|"]
for r in six["summary"]:
    if r["day"].startswith("2026-09"):
        o, f = r["models"]["opus"]["live"], r["models"]["fable_op"]["live"]
        L.append("| %s | %d | %d / %d | %s | %d | %d / %d | %s |" % (r["day"][5:], o["n"], o["t1_hit"], o["t1_stopped"], inr(o["T1"]) if o["n"] else "no trade",
                                                                    f["n"], f["t1_hit"], f["t1_stopped"], inr(f["T1"]) if f["n"] else "no trade"))
L.append("| **Total** | **%d** | **%d / %d** | **%s** | **%d** | **%d / %d** | **%s** |" % (t["opus"]["n"], t["opus"]["t1_hit"], t["opus"]["t1_stopped"], inr(t["opus"]["T1"]),
                                                                                 t["fable_op"]["n"], t["fable_op"]["t1_hit"], t["fable_op"]["t1_stopped"], inr(t["fable_op"]["T1"])))
L += ["", "## Held across days (no square-off at the close)", "",
      "Same trades. The September futures candles can no longer be read, so each trade is followed on its cash share: stop and targets rebuilt by the scanner's "
      "level code at the report's signal minute, then held until the target or the stop. Treat these as approximate. Check: followed the same way but squared off "
      "at the close, the cash route gives Opus %s / %s / %s and Fable-OP %s / %s / %s at T1 / T2 / T3, against the report's figures above." % tuple(
          inr(sum(c["net_cash"][p] for c in hold["cmp"] if m in c["models"] and c["day"] < "2026-10-01")) for m in ("opus", "fable_op") for p in ("T1", "T2", "T3")), "",
      "| Exit | Opus: hit / stopped | Opus net (Rs) | Fable-OP: hit / stopped | Fable-OP net (Rs) |", "|---|---|---|---|---|"]
for pol in ("T1", "T2", "T3"):
    o, f = cap["hold"]["opus|Sep|" + pol], cap["hold"]["fable_op|Sep|" + pol]
    L.append("| %s | %d / %d | %s | %d / %d | %s |" % (pol, o["hit"], o["stopped"], inr(o["net"]), f["hit"], f["stopped"], inr(f["net"])))
L += ["", "Trading days taken to reach T3 (after the entry day):", "", "| Trading days after entry day | Opus | Fable-OP |", "|---|---|---|"]
o, f = cap["hold"]["opus|Sep|T3"], cap["hold"]["fable_op|Sep|T3"]
for i, lab in enumerate(("Same session", "1", "2", "3", "4", "5 or more")):
    L.append("| %s | %d | %d |" % (lab, o["days_hist"][i], f["days_hist"][i]))
L.append("| **Reached T3** | **%d** | **%d** |" % (o["hit"], f["hit"]))
L.append("| Longest | %d | %d |" % (o["max_days"], f["max_days"]))
for m, name in MS:
    L += ["", "## %s: every September trade" % name, "",
          "| Date | Time | Symbol | Side | Score | Same day, exit T1 (Rs) | Same day, hold T3 (Rs) | Held: T1 result | Held: T3 result | Days to T3 exit | Held T3 net (Rs) |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in hold["rows"]:
        if m in r["models"] and r["day"] < "2026-10-01":
            lab = {"target": "hit", "stopped": "stopped", "open": "open"}
            L.append("| %s | %s | %s | %s | %.1f | %s | %s | %s | %s | %d | %s |" % (r["day"][5:], r["time"], r["symbol"], r["side"], r["scores"][m], inr(r["report"]["T1"]["net_rs"]),
                     inr(r["report"]["T3"]["net_rs"]), lab[r["res"]["T1"]["status"]], lab[r["res"]["T3"]["status"]], r["res"]["T3"]["sessions"], inr(r["res"]["T3"]["net_rs"])))
L += ["", "## The six months in the same report, month by month (same-day results, live rule)", "",
      "| Month | Sessions | Nifty | Opus trades | Opus T1 (Rs) | Opus T3 (Rs) | Fable-OP trades | Fable-OP T1 (Rs) | Fable-OP T3 (Rs) |", "|---|---|---|---|---|---|---|---|---|"]
for mth in six["months"]:
    o, f = mth["totals"]["opus"]["live"], mth["totals"]["fable_op"]["live"]
    L.append("| %s | %d | %+.2f %% | %d | %s | %s | %d | %s | %s |" % (mth["month"], mth["days"], mth["nifty_pct"], o["n"], inr(o["T1"]), inr(o["T3"]), f["n"], inr(f["T1"]), inr(f["T3"])))
o, f = six["totals"]["opus"]["live"], six["totals"]["fable_op"]["live"]
L.append("| **12 May - 11 Nov** | **%d** | | **%d** | **%s** | **%s** | **%d** | **%s** | **%s** |" % (six["sessions"], o["n"], inr(o["T1"]), inr(o["T3"]), f["n"], inr(f["T1"]), inr(f["T3"])))
L += ["", "Fable-OP's score was shaped on 12 May - 31 Aug, so those months flatter it; 1 Sep onward is its unseen period. Opus's weights were tuned on 21 Oct - 9 Nov.", ""]
open(os.path.join(sp, "opus_vs_fable_op_September_2026.md"), "w").write("\n".join(L))

# ------------------------------------------------------------------ capital
P = ["# Rs 3 lakh per method: Opus exit at T1, Fable-OP exit at T3", "",
     "Sample: 50 sessions, 1 Sep to 13 Nov 2026. Trades are the live rule's picks (scanner's own six-month report for 1 Sep - 19 Oct, followed on the cash share; "
     "my replays on November futures for 21 Oct - 13 Nov). Each trade is held across days until its target or its stop, sized by the scanner (Rs 15,000 risk, mostly one lot), "
     "charges and 0.02 % slippage a side included.", "",
     "Capital rule: Rs 3,00,000 fixed per method, futures margin taken as 20 % of contract value (about Rs 1.3 - 1.5 lakh a trade). Signals are taken in the order they fire; "
     "a signal is skipped when the free margin does not cover it; margin frees at the exit minute. Profits are not reinvested and losses are not topped up.", "",
     "| | Opus, exit T1 | Fable-OP, exit T3 |", "|---|---|---|"]
a, b = cap["cap"]["opus|T1|0.2|300000"], cap["cap"]["fable_op|T3|0.2|300000"]
ua, ub = cap["cap"]["opus|T1|0.2|all"], cap["cap"]["fable_op|T3|0.2|all"]
ba, bb = boot["opus T1 3L"], boot["fable_op T3 3L"]
P.append("| Signals in 50 sessions | %d | %d |" % (ua["taken"], ub["taken"]))
P.append("| Trades Rs 3 lakh could carry | %d | %d |" % (a["taken"], b["taken"]))
P.append("| Signals skipped for lack of margin | %d | %d |" % (a["skipped"], b["skipped"]))
P.append("| Target hit / stopped | %d / %d | %d / %d |" % (a["hit"], a["stopped"], b["hit"], b["stopped"]))
P.append("| Net profit in 50 sessions (Rs) | %s | %s |" % (inr(a["net"]), inr(b["net"])))
P.append("| Same pace for 250 sessions (Rs) | %s | %s |" % (inr(a["year"]), inr(b["year"])))
P.append("| Range when the 50 days are resampled into a year, 5th to 95th percentile (Rs) | %s to %s | %s to %s |" % (inr(ba["boot_p5"]), inr(ba["boot_p95"]), inr(bb["boot_p5"]), inr(bb["boot_p95"])))
P.append("| First 25 sessions' pace for a year (Rs) | %s | %s |" % (inr(ba["first25_year"]), inr(bb["first25_year"])))
P.append("| Last 25 sessions' pace for a year (Rs) | %s | %s |" % (inr(ba["last25_year"]), inr(bb["last25_year"])))
P.append("| Largest fall from a peak (Rs) | %s | %s |" % (inr(a["max_dd"]), inr(b["max_dd"])))
P.append("| Longest run of losing trades | %d | %d |" % (ba["max_losing_streak"], bb["max_losing_streak"]))
P.append("| Average winning / losing trade (Rs) | %s / %s | %s / %s |" % (inr(ba["avg_win"]), inr(ba["avg_loss"]), inr(bb["avg_win"]), inr(bb["avg_loss"])))
P.append("| Days up / down / no trade | %d / %d / %d | %d / %d / %d |" % (ba["pos_days"], ba["neg_days"], ba["flat_days"], bb["pos_days"], bb["neg_days"], bb["flat_days"]))
P += ["", "## By month (Rs 3 lakh, 20 % margin)", "", "| Month | Sessions | Opus T1: trades | Opus T1: net (Rs) | Fable-OP T3: trades | Fable-OP T3: net (Rs) |", "|---|---|---|---|---|---|"]
for mth, ns in (("2026-09", 21), ("2026-10", 20), ("2026-11", 9)):
    x, y = a["by_month"].get(mth, [0, 0]), b["by_month"].get(mth, [0, 0])
    P.append("| %s | %d | %d | %s | %d | %s |" % (mth, ns, x[0], inr(x[1]), y[0], inr(y[1])))
P += ["", "## If every signal could be taken (no capital limit)", "", "| | Opus, exit T1 | Fable-OP, exit T3 |", "|---|---|---|"]
P.append("| Trades | %d | %d |" % (ua["taken"], ub["taken"]))
P.append("| Net profit in 50 sessions (Rs) | %s | %s |" % (inr(ua["net"]), inr(ub["net"])))
P.append("| Most positions open at once | %d | %d |" % (ua["peak_open"], ub["peak_open"]))
P.append("| Margin needed at that moment, at 20 %% (Rs) | %s | %s |" % (inr(ua["peak_margin"], False), inr(ub["peak_margin"], False)))
P.append("| Largest fall from a peak (Rs) | %s | %s |" % (inr(ua["max_dd"]), inr(ub["max_dd"])))
P += ["", "## How much the margin assumption matters (Rs 3 lakh, net in 50 sessions)", "", "| Margin as % of contract value | Opus T1: trades | Opus T1: net (Rs) | Fable-OP T3: trades | Fable-OP T3: net (Rs) |", "|---|---|---|---|---|"]
for rate in ("0.15", "0.2", "0.25"):
    x, y = cap["cap"]["opus|T1|%s|300000" % rate], cap["cap"]["fable_op|T3|%s|300000" % rate]
    P.append("| %d %% | %d | %s | %d | %s |" % (round(float(rate) * 100), x["taken"], inr(x["net"]), y["taken"], inr(y["net"])))
P += ["", "## The other two combinations, for reference (Rs 3 lakh, 20 % margin, 50 sessions)", "", "| | Trades taken | Net (Rs) | Largest fall (Rs) |", "|---|---|---|---|"]
for k, lab in (("opus|T2|0.2|300000", "Opus, exit T2"), ("opus|T3|0.2|300000", "Opus, exit T3"), ("fable_op|T1|0.2|300000", "Fable-OP, exit T1"), ("fable_op|T2|0.2|300000", "Fable-OP, exit T2")):
    x = cap["cap"][k]
    P.append("| %s | %d | %s | %s |" % (lab, x["taken"], inr(x["net"]), inr(x["max_dd"])))
o = six["totals"]["opus"]["live"]
P += ["", "## A slower yardstick: the scanner's own six-month report", "",
      "12 May to 11 Nov 2026, 126 sessions, every signal taken, squared off at the close (no overnight holds), real contract months: Opus at T1 made %s on %d trades, "
      "about %s a session, or %s over 250 sessions with no capital limit. Rs 3 lakh carries roughly half of Opus's signals, so about half of that." % (
          inr(o["T1"]), o["n"], inr(o["T1"] / six["sessions"]), inr(o["T1"] / six["sessions"] * 250)), ""]
open(os.path.join(sp, "capital_3_lakh_one_year_projection.md"), "w").write("\n".join(P))
print("\n".join(L[:22]))
print("...")
print("\n".join(L[40:62]))
print("=====")
print("\n".join(P))
