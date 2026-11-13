import json, os, sys, random, glob
import pandas as pd
sys.argv = [sys.argv[0], sys.argv[1]]
sp = sys.argv[1]
src = open(os.path.join(sp, "tools", "cap_sim.py")).read()
# reuse the loader and sim() from cap_sim.py without its printing loops
head = src.split("out = {\"sessions\"")[0]
simsrc = "def sim" + src.split("def sim")[1].split("for m in MS:")[0]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    exec(head)
simsrc = simsrc.replace('return {"taken": len(taken)', 'return {"trades": taken, "taken": len(taken)')
exec(simsrc)
random.seed(7)
res = {}
for m, pol in (("opus", "T1"), ("fable_op", "T3"), ("opus", "T3"), ("fable_op", "T1")):
    tr = [r for r in rows if m in r["models"]]
    for cap in (300000.0, None):
        s = sim(tr, pol, cap, 0.20)
        byday = {d: 0.0 for d in days}
        for t in s["trades"]:
            byday[t["day"]] += t["net"]
        v = [byday[d] for d in days]
        sims = sorted(sum(random.choice(v) for _ in range(250)) for _ in range(4000))
        # the sample split in two halves and three calendar months, each scaled to 250 sessions
        h1, h2 = v[:25], v[25:]
        key = "%s %s %s" % (m, pol, "3L" if cap else "all")
        res[key] = {"net": round(sum(v)), "taken": s["taken"], "skipped": s["skipped"], "pos_days": sum(x > 0 for x in v), "neg_days": sum(x < 0 for x in v), "flat_days": sum(x == 0 for x in v),
                    "worst_day": round(min(v)), "best_day": round(max(v)), "year": round(sum(v) / len(v) * 250),
                    "boot_p5": round(sims[200]), "boot_p50": round(sims[2000]), "boot_p95": round(sims[3800]),
                    "first25_year": round(sum(h1) / 25 * 250), "last25_year": round(sum(h2) / 25 * 250), "max_dd": s["max_dd"], "peak_margin": s["peak_margin"], "peak_open": s["peak_open"],
                    "wins": sum(t["net"] > 0 for t in s["trades"]), "avg_win": round(sum(t["net"] for t in s["trades"] if t["net"] > 0) / max(1, sum(t["net"] > 0 for t in s["trades"]))),
                    "avg_loss": round(sum(t["net"] for t in s["trades"] if t["net"] <= 0) / max(1, sum(t["net"] <= 0 for t in s["trades"]))),
                    "max_losing_streak": 0}
        streak = best = 0
        for t in sorted(s["trades"], key=lambda t: t["exit_ts"]):
            streak = streak + 1 if t["net"] <= 0 else 0
            best = max(best, streak)
        res[key]["max_losing_streak"] = best
        print(key, json.dumps(res[key]))
json.dump(res, open(os.path.join(sp, "cap_boot.json"), "w"))
