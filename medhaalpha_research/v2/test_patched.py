# Checks the patched copy of the scanner code (v2/patched), offline, against the stored replay days and the six-month report.
import glob, json, os, sys
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
import scanner
assert "/v2/patched/" in scanner.__file__, scanner.__file__
from scanner.equity.config import EqConfig
from scanner.equity.score import MODELS, LABELS, all_scores, min_score, opus_v2_score
from scanner.equity.backtest import with_all_models, summary_row
SP = sys.argv[1]
cfg = EqConfig()
assert MODELS == ("opus", "fable", "fable_op", "opus_v2") and LABELS["opus_v2"] == "Opus v2" and min_score(cfg, "opus_v2") == 75.0 and min_score(cfg, "opus") == 75.0
six = json.load(open(SP + "/six/pull.json"))
picks_report = {tuple(k) for k in json.load(open(SP + "/v2/split_picks.json"))}
nsig = worst = 0
tot = {m: {"n": 0, "T1": 0.0, "hit": 0} for m in MODELS}
days = 0
for d in ("replay_oct", "replay_nov2", "replay7"):
    for p in sorted(glob.glob(SP + "/" + d + "/replay_*.json")):
        day = json.load(open(p))
        days += 1
        for s in day["signals"]:
            sc = all_scores(s["snapshot"], s["side"], s["stop_at"], s["risk"], s["entry_ref"], cfg)
            for m in ("opus", "fable", "fable_op"):
                worst = max(worst, abs(sc[m]["score"] - s["scores"][m]))
            want = sc["fable_op"] if s["side"] == "LONG" else sc["opus"]
            assert sc["opus_v2"] == want and opus_v2_score(s["snapshot"], s["side"], s["stop_at"], cfg) == (want["score"], want["parts"])
            nsig += 1
        up = with_all_models(day, cfg)
        assert set(up["models"]) == set(MODELS)
        for s0, s1 in zip(day["signals"], up["signals"]):
            assert all(s0["in"][m] == s1["in"][m] for m in ("opus", "fable", "fable_op")), (day["day"], s0["symbol"])      # old models untouched
            assert s1["scores"]["opus_v2"] == (s1["scores"]["fable_op"] if s1["side"] == "LONG" else s1["scores"]["opus"])
        live = {(day["day"], s["symbol"], s["setup"], s["time"]) for s in up["signals"] if "live" in s["in"]["opus_v2"]}
        assert live == {k for k in picks_report if k[0] == day["day"]}, (day["day"], live ^ {k for k in picks_report if k[0] == day["day"]})
        row = summary_row(up)
        for m in MODELS:
            c = row["models"][m]["live"]
            tot[m]["n"] += c["n"]; tot[m]["T1"] += c["T1"]; tot[m]["hit"] += c["t1_hit"]
print("replay days checked:", days, "| signals rescored:", nsig, "| largest difference from the stored opus/fable/fable_op scores: %.3f points" % worst)
print("opus_v2 live picks from the patched code equal the tested picks on every one of those days")
for m in MODELS:
    print("  21 Oct - 13 Nov, %-8s live: %3d trades, %2d reached T1, T1 net %+9.0f" % (m, tot[m]["n"], tot[m]["hit"], tot[m]["T1"]))
