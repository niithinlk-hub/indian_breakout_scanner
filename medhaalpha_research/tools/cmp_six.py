# Cash-basis replay (mine) against the scanner's own six-month report (real contract month), day by day.
import glob, json, os, sys
six_path, rdir = sys.argv[1], sys.argv[2]
d = json.load(open(six_path))
six, sig = d["six"], d["sig"]
MI = {m: i for i, m in enumerate(sig["models"])}
PI = {p: i for i, p in enumerate(sig["policies"])}
THR = {m: six["models"][m]["min_score"] for m in six["models"]}
N = six["top_n"]
MS = ("opus", "fable_op")
POLS = ("T1", "T2", "T3", "CLOSE")
bund = {x["day"]: x["signals"] for x in sig["days"]}
summ = {r["day"]: r for r in six["summary"]}


def live_b(day, m):
    pool = [s for s in bund[day] if s[2] in ("A", "B") and s[4][PI["T1"]] is not None]
    out = []
    for s in sorted(pool, key=lambda s: (s[0], -s[3][MI[m]], s[1])):
        if s[3][MI[m]] >= THR[m] and len(out) < N:
            out.append(s)
    return out


tot = {}
rederive_bad = 0
for p in sorted(glob.glob(os.path.join(rdir, "replay_*.json"))):
    j = json.load(open(p))
    day = j["day"]
    if day not in bund:
        continue
    per = "sep" if day < "2026-10-01" else "oct"
    line = [day]
    allm = {(s["symbol"], s["setup"]) for s in j["signals"] if s["setup"] in ("A", "B")}
    allb = {(s[1], s[2]) for s in bund[day] if s[2] in ("A", "B")}
    line.append("AB signals(sym,setup) mine %3d bundled %3d common %3d" % (len(allm), len(allb), len(allm & allb)))
    for m in MS:
        mine = [s for s in j["signals"] if "live" in s["in"][m]]
        b = live_b(day, m)
        bs = summ[day]["models"][m]["live"]
        if len(b) != bs["n"] or abs(sum(s[4][PI["T1"]] for s in b) - bs["T1"]) > 2:
            rederive_bad += 1
        km, kb = {(s["symbol"], s["setup"]) for s in mine}, {(s[1], s[2]) for s in b}
        t = tot.setdefault((per, m), {"n_m": 0, "n_b": 0, "common": 0, **{"m_" + q: 0.0 for q in POLS}, **{"b_" + q: 0.0 for q in POLS}, "hit_m": 0, "hit_b": 0, "stop_m": 0, "stop_b": 0, "same_min": 0})
        t["n_m"] += len(mine); t["n_b"] += len(b); t["common"] += len(km & kb)
        tb = {(s[1], s[2]): s[0] for s in b}
        t["same_min"] += sum(1 for s in mine if tb.get((s["symbol"], s["setup"])) == s["time"])
        for q in POLS:
            t["m_" + q] += sum(s["fut"][q]["net_rs"] for s in mine)
            t["b_" + q] += sum(s[4][PI[q]] for s in b)
        t["hit_m"] += sum(s["fut"]["T1"]["status"] == "target" for s in mine); t["stop_m"] += sum(s["fut"]["T1"]["status"] == "stopped" for s in mine)
        t["hit_b"] += bs["t1_hit"]; t["stop_b"] += bs["t1_stopped"]
        line.append("%s mine n=%d T1 %+7.0f | bundled n=%d T1 %+7.0f | common %d" % (m, len(mine), sum(s["fut"]["T1"]["net_rs"] for s in mine), len(b), bs["T1"], len(km & kb)))
    print(" || ".join(line))
print("re-derived bundled live selection differs from its own summary on", rederive_bad, "model-days")
for k in sorted(tot):
    t = tot[k]
    print(k, "trades mine %d bundled %d common %d (same minute %d) | T1 hit/stop mine %d/%d bundled %d/%d" % (t["n_m"], t["n_b"], t["common"], t["same_min"], t["hit_m"], t["stop_m"], t["hit_b"], t["stop_b"]))
    print("      " + " | ".join("%s mine %+8.0f bundled %+8.0f" % (q, t["m_" + q], t["b_" + q]) for q in POLS))
