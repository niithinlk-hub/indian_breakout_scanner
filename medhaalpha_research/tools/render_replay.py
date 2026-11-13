import json, sys
p = json.load(open(sys.argv[1]))
print("day", p["day"], "| mode", p["mode"], "| run_at", p["run_at"], "| universe", p["universe"], "scanned", p["scanned"],
      "| signals", len(p["signals"]), p["counts"], "| over_budget", p["over_budget"], "| config", p["config"])
print("near-misses", p["near_misses_total"])
sig = p["signals"]
en = [s for s in sig if s["enabled"]]
for m in ("opus", "fable", "fable_op"):
    thr = p["models"][m]["min_score"]
    print("  %s: threshold %g, enabled signals at/above it: %d of %d; top scores: %s" % (
        m, thr, sum(s["scores"][m] >= thr for s in en), len(en),
        [(s["symbol"], s["time"], s["scores"][m]) for s in sorted(en, key=lambda s: -s["scores"][m])[:6]]))
for m in ("fable_op", "opus"):
    sel = p["models"][m]["selections"]["live"]
    fs, osum = sel["futures"], sel.get("options") or {}
    print("\n=== %s | %s | n=%d" % (m, sel["label"], sel["n"]))
    print("time  symbol       set side  qty   score  entry     stop      t1        T1      exit      at     R      fut_net  | option                  opt_T1_net")
    for s in [s for s in sig if "live" in s["in"][m]]:
        f, o = s["fut"]["T1"], ((s.get("option") or {}).get("legs") or {}).get("T1", {})
        print("%s %-12s %s   %-5s %-5s %5.1f  %-9s %-9s %-9s %-7s %-9s %s  %+5.2f  %+8.0f | %-22s %s" % (
            s["time"], s["symbol"][:12], s["setup"], s["side"], s["lot"] * (s["lots"] or 0), s["scores"][m], f["entry"], s["stop"], s["t1"],
            f["status"], f["exit"], f["exit_ts"][11:16], f["r"], f["net_rs"], ((s.get("option") or {}).get("symbol") or "-")[:22],
            ("%+.0f" % o["net_rs"]) if o.get("net_rs") is not None else "n/a"))
    for pol in ("T1", "T2", "T3", "CLOSE", "T2_TR", "T3_TR"):
        x = fs[pol]
        print("   exit %-6s futures net %+8.0f (R %+.2f; target %d, stopped %d, trail %d, close %d, winners %d) | options net %s over %s" % (
            pol, x["net_rs"], x["total_r"], x["target"], x["stopped"], x["trail"], x["close"], x["winners"],
            ("%+.0f" % osum[pol]["net_rs"]) if pol in osum else "n/a", osum.get(pol, {}).get("n")))
both = [s["symbol"] for s in sig if "live" in s["in"]["fable_op"] and "live" in s["in"]["opus"]]
print("\ntaken by both:", both)
