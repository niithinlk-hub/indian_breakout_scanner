# Cash-share stand-in replay from locally cached candles (no network). The scanner's own replay (patched copy, five models),
# every stock scanned and priced on its cash share, Nifty taken from the index, one fixed stock list for every day.
# usage: proxy_replay.py <scratchpad> <out_dir> <from YYYY-MM-DD> <to YYYY-MM-DD>
import asyncio, copy, gzip, json, os, pickle, sys, time
from datetime import date, timedelta
sp, out_dir, LO, HI = sys.argv[1], sys.argv[2], date.fromisoformat(sys.argv[3]), date.fromisoformat(sys.argv[4])
os.makedirs(out_dir, exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(out_dir, "kv_%s.db" % LO.isoformat())
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
for k in [k for k in os.environ if k.startswith("EQ_")]:
    del os.environ[k]
import numpy as np
import pandas as pd
import scanner
assert "/v2/patched/" in scanner.__file__
from scanner.series import candles_to_df, merge_frames
from scanner.source import UpstoxSource
from scanner.equity.config import eq_settings as cfg
from scanner.equity.data import Throttle
from scanner.equity.engine import EquityEngine
from scanner.equity.features import session_days
from scanner.equity.score import MODELS
from scanner.equity.universe_upstox import parse

D = sp + "/v2/data"
parts = [pickle.load(open(D + "/" + f, "rb")) for f in ("pre.pkl", "early.pkl") if os.path.exists(D + "/" + f)]
late = pickle.load(open(sp + "/replay_sep/minutes.pkl", "rb"))
keys = parts[-1]["keys"]
lo_i, hi_i = (LO - timedelta(days=20)), HI


def di(d):
    return d.year * 10000 + d.month * 100 + d.day


def cut(df):
    if df is None or df.empty:
        return df
    a = (df.index.year * 10000 + df.index.month * 100 + df.index.day).to_numpy()
    return df.iloc[np.searchsorted(a, di(lo_i), "left"):np.searchsorted(a, di(hi_i), "right")]


mins, daily = {}, {}
for s, k in keys.items():
    m = None
    for p in parts:
        m = merge_frames(m, cut(p["minutes"].get(k)))
    m = merge_frames(m, cut(late["minutes"].get(k)))
    mins[k] = m if m is not None else candles_to_df([])
    daily[k] = next((p["daily"][s] for p in parts if s in p["daily"]), candles_to_df([]))
nifty = None
for p in parts:
    nifty = merge_frames(nifty, cut(p["nifty"]))
del parts, late
ints = {k: (v.index.year * 10000 + v.index.month * 100 + v.index.day).to_numpy() for k, v in mins.items()}
dints = {k: (v.index.year * 10000 + v.index.month * 100 + v.index.day).to_numpy() for k, v in daily.items()}
nint = (nifty.index.year * 10000 + nifty.index.month * 100 + nifty.index.day).to_numpy()
uni = parse(json.loads(gzip.decompress(open(sp + "/test/NSE.json.gz", "rb").read())))
NKEY = uni.pick_future("NIFTY", date(2026, 11, 13), cfg.roll_sessions).key
six = json.load(open(sp + "/six/pull.json"))["sig"]
members = {s[1] for x in six["days"] if x["day"] <= "2026-06-30" for s in x["signals"]}
EMPTY = candles_to_df([])


class LocalSource(UpstoxSource):
    def __init__(self):
        super().__init__("http://127.0.0.1:9", "", "")

    async def candles(self, key, unit, interval, to, frm):
        if key == NKEY:
            return nifty.iloc[np.searchsorted(nint, di(frm), "left"):np.searchsorted(nint, di(to), "right")]
        if key.startswith("NSE_FO") or key not in mins:
            return EMPTY
        if unit == "minutes":
            return mins[key].iloc[np.searchsorted(ints[key], di(frm), "left"):np.searchsorted(ints[key], di(to), "right")]
        return daily[key].iloc[np.searchsorted(dints[key], di(frm), "left"):np.searchsorted(dints[key], di(to), "right")]


async def main():
    src = LocalSource()
    u2 = copy.copy(uni)
    u2.unds = {s: u for s, u in uni.unds.items() if u.kind != "EQUITY" or s in members}
    u2.pick_option = lambda *a, **k: None
    days = [d for d in session_days(nifty, cfg) if LO <= d <= HI]
    print("stocks", len(u2.stocks), "| sessions", len(days), days[0] if days else None, "->", days[-1] if days else None, "| models", MODELS, flush=True)
    for day in days:
        eng = EquityEngine(src)
        eng.uni = u2
        eng.thr = Throttle(per_sec=1e6, per_30min=10 ** 9)
        t0 = time.time()
        await eng.replay(day)
        res, st = eng.replay_result(day.isoformat()), eng.replay_status
        if res and not st.get("error"):
            json.dump(res, open(os.path.join(out_dir, "proxy_%s.json" % day), "w"))
            live = {m: sum(1 for s in res["signals"] if "live" in s["in"][m]) for m in MODELS}
            print("DONE %s %3ds scanned %d signals %3d %s live %s errors %d" % (day, time.time() - t0, res["scanned"], len(res["signals"]), res["counts"], live, len(eng.status["errors"])), flush=True)
        else:
            print("FAILED %s: %s" % (day, st.get("error")), flush=True)
    print("ALL DONE", LO, HI, flush=True)
    await src.close()

asyncio.run(main())
