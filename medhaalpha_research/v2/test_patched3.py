# Offline check of the patched copy with opus_v2 and opus_v3, on the 17 stored replay days (real November futures).
import glob, json, os, pickle, sys
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
import scanner
assert "/v2/patched/" in scanner.__file__, scanner.__file__
from scanner.equity.config import EqConfig
from scanner.equity.score import MODELS, all_scores, min_score, opus_v3_score
from scanner.equity.backtest import with_all_models, summary_row
SP = sys.argv[1]
cfg = EqConfig()
assert MODELS == ("opus", "fable", "fable_op", "opus_v2", "opus_v3") and min_score(cfg, "opus_v3") == 75.0 and cfg.opus_v3_min_rel_vol == 1.0
v2p = {tuple(k) for k in json.load(open(SP + "/v2/split_picks.json"))}
v3p = {tuple(k) for k in json.load(open(SP + "/v2/v3_picks.json"))}
feat = {(r["day"], r["symbol"], r["setup"], r["time"]): r["f"]["rel_vol"] for r in pickle.load(open(SP + "/v2/data/feat.pkl", "rb"))}
tot = {m: {"n": 0, "T1": 0.0, "hit": 0, "stop": 0} for m in MODELS}
nsig = gated = rvn = 0
rvmax = 0.0
flip = 0
picks3 = []
for d in ("replay_oct", "replay_nov2", "replay7"):
    for p in sorted(glob.glob(SP + "/" + d + "/replay_*.json")):
        day = json.load(open(p))
        for s in day["signals"]:
            sc = all_scores(s["snapshot"], s["side"], s["stop_at"], s["risk"], s["entry_ref"], cfg)
            for m in ("opus", "fable", "fable_op"):
                assert abs(sc[m]["score"] - s["scores"][m]) < 1e-9
            v2 = sc["fable_op"] if s["side"] == "LONG" else sc["opus"]
            g = s["side"] == "LONG" and s["snapshot"]["rel_vol"] is not None and s["snapshot"]["rel_vol"] < 1.0
            assert sc["opus_v2"] == v2 and sc["opus_v3"]["score"] == (0.0 if g else v2["score"]) and opus_v3_score(s["snapshot"], s["side"], s["stop_at"], cfg)[0] == sc["opus_v3"]["score"]
            assert abs(sum(sc["opus_v3"]["parts"].values()) - sc["opus_v3"]["score"]) < 0.26       # parts are rounded to 0.1
            nsig += 1; gated += g
            k = (day["day"], s["symbol"], s["setup"], s["time"])
            if s["setup"] in ("A", "B") and k in feat and s["snapshot"]["rel_vol"] is not None:      # my rebuilt rel_vol against the scanner's own
                rvn += 1; rvmax = max(rvmax, abs(feat[k] - s["snapshot"]["rel_vol"]))
                flip += (feat[k] < 1.0) != (s["snapshot"]["rel_vol"] < 1.0)
        up = with_all_models(day, cfg)
        for s0, s1 in zip(day["signals"], up["signals"]):
            assert all(s0["in"][m] == s1["in"][m] for m in ("opus", "fable", "fable_op"))
        for m, ref in (("opus_v2", v2p), ("opus_v3", v3p)):
            live = {(day["day"], s["symbol"], s["setup"], s["time"]) for s in up["signals"] if "live" in s["in"][m]}
            if day["day"] <= "2026-11-11":
                assert live == {k for k in ref if k[0] == day["day"]}, (m, day["day"], live ^ {k for k in ref if k[0] == day["day"]})
        picks3 += [[day["day"], s["symbol"], s["setup"], s["time"]] for s in up["signals"] if "live" in s["in"]["opus_v3"]]
        row = summary_row(up)
        for m in MODELS:
            c = row["models"][m]["live"]
            tot[m]["n"] += c["n"]; tot[m]["T1"] += c["T1"]; tot[m]["hit"] += c["t1_hit"]; tot[m]["stop"] += c["t1_stopped"]
print("signals rescored:", nsig, "| longs gated by volume:", gated, "| existing models reproduced exactly and their picks untouched")
print("my rebuilt rel_vol vs the scanner's own, %d signals: largest difference %.4f, on the other side of 1.0 in %d" % (rvn, rvmax, flip))
print("opus_v2 and opus_v3 picks from the patched code equal the six-month-file picks on all 15 days up to 11 Nov")
for m in MODELS:
    t = tot[m]
    print("  21 Oct - 13 Nov %-8s %2d trades, %2d reached T1 (%2.0f%%), %2d stopped (%2.0f%%), T1 net %+8.0f" % (m, t["n"], t["hit"], 100 * t["hit"] / t["n"], t["stop"], 100 * t["stop"] / t["n"], t["T1"]))
json.dump(picks3, open(SP + "/v2/v3_picks_replays.json", "w"))
