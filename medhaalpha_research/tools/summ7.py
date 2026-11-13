import glob, json, os, sys
d = sys.argv[1]
days = [json.load(open(p)) for p in sorted(glob.glob(os.path.join(d, "replay_*.json")))]
MODELS = ("opus", "fable_op", "fable")
tot = {m: {"n": 0, "hit": 0, "stop": 0, "close": 0, "win": 0, "fut": 0.0, "opt": 0.0, "days_pos": 0, "days_traded": 0,
           "pol": {p: 0.0 for p in ("T1", "T2", "T3", "CLOSE", "T2_TR", "T3_TR")}} for m in MODELS}
print("%-10s %4s | %-34s | %-34s | %-34s" % ("day", "sigs", "opus>=75: n hit/stop/close fut opt", "fable_op>=75: n hit/stop/close fut opt", "fable>=80: n hit/stop/close fut opt"))
for p in days:
    row = []
    for m in MODELS:
        sel = p["models"][m]["selections"]["live"]
        f, o = sel["futures"], sel.get("options") or {}
        t1 = f["T1"]
        on = (o.get("T1") or {}).get("net_rs") or 0
        row.append("%d  %d/%d/%d  %+8.0f %+8.0f" % (sel["n"], t1["target"], t1["stopped"], t1["close"], t1["net_rs"], on))
        T = tot[m]
        T["n"] += sel["n"]; T["hit"] += t1["target"]; T["stop"] += t1["stopped"]; T["close"] += t1["close"]; T["win"] += t1["winners"]
        T["fut"] += t1["net_rs"]; T["opt"] += on
        T["days_traded"] += sel["n"] > 0; T["days_pos"] += t1["net_rs"] > 0
        for pol in T["pol"]:
            T["pol"][pol] += f[pol]["net_rs"]
    print("%-10s %4d | %-34s | %-34s | %-34s" % (p["day"], sum(1 for s in p["signals"] if s["enabled"]), *row))
print()
for m in MODELS:
    T = tot[m]
    print("%-8s trades %2d | T1 hit %d (%.0f%%) stopped %d closed-at-eod %d | net winners %d | futures net %+.0f (per trade %+.0f) | options net %+.0f | days traded %d, positive %d | by exit: %s" % (
        m, T["n"], T["hit"], 100 * T["hit"] / max(T["n"], 1), T["stop"], T["close"], T["win"], T["fut"], T["fut"] / max(T["n"], 1), T["opt"],
        T["days_traded"], T["days_pos"], {k: round(v) for k, v in T["pol"].items()}))
for m in ("fable_op", "opus"):
    print("\n%s live-rule trades" % m)
    for p in days:
        for s in p["signals"]:
            if "live" in s["in"][m]:
                f, o = s["fut"]["T1"], ((s.get("option") or {}).get("legs") or {}).get("T1", {})
                print("  %s %s %-11s %s %-5s qty %-5s score %5.1f entry %-8s stop %-8s t1 %-8s %-7s %s R %+.2f fut %+7.0f opt %s" % (
                    p["day"][5:], s["time"], s["symbol"][:11], s["setup"], s["side"], s["lot"] * (s["lots"] or 0), s["scores"][m], f["entry"], s["stop"], s["t1"],
                    f["status"], f["exit_ts"][11:16], f["r"], f["net_rs"], ("%+.0f" % o["net_rs"]) if o.get("net_rs") is not None else "n/a"))
print("\nfable_op near the threshold (65 to 75), enabled signals:")
for p in days:
    for s in p["signals"]:
        if s["enabled"] and 65 <= s["scores"]["fable_op"] < 75:
            f = s["fut"]["T1"]
            print("  %s %s %-11s score %5.1f lots %s %-8s R %+.2f fut %+7.0f" % (p["day"][5:], s["time"], s["symbol"][:11], s["scores"]["fable_op"], s["lots"], f["status"], f["r"], f["net_rs"]))
