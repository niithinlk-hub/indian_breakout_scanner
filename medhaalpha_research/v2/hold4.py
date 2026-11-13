# 21 Oct - 13 Nov 2026, all four score models: the live rule's picks from the stored replay days (patched scanner code adds
# opus_v2), then each pick held across days on its November futures candles (fills.run_policies without the square-off).
import glob, gzip, json, os, sys, time, urllib.parse, urllib.request
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
import pandas as pd
import scanner
assert "/v2/patched/" in scanner.__file__
from scanner.series import candles_to_df, merge_frames
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import run_policies
from scanner.equity.score import MODELS
from scanner.equity.backtest import with_all_models
from scanner.equity.universe_upstox import parse

sp = sys.argv[1]
cfg = EqConfig()
days = sorted((with_all_models(json.load(open(p)), cfg) for d in ("replay_oct", "replay_nov2", "replay7") for p in glob.glob(os.path.join(sp, d, "replay_*.json"))), key=lambda p: p["day"])
print("sessions:", len(days), days[0]["day"], "->", days[-1]["day"], "| models", MODELS)
uni = parse(json.loads(gzip.decompress(open(os.path.join(sp, "test", "NSE.json.gz"), "rb").read())))
trades = []
for p in days:
    for s in p["signals"]:
        ms = [m for m in MODELS if "live" in s["in"][m]]
        if ms:
            trades.append({"day": p["day"], "s": s, "models": ms})
first_day = {}
for t in trades:
    first_day[t["s"]["symbol"]] = min(first_day.get(t["s"]["symbol"], t["day"]), t["day"])
today = pd.Timestamp.now(tz="Asia/Kolkata").date()
y = str((pd.Timestamp(today) - pd.Timedelta(days=1)).date())


def get(url):
    for a in range(4):
        try:
            time.sleep(0.22)
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/8"})
            return json.load(urllib.request.urlopen(req, timeout=40))["data"]["candles"]
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 400 or a == 3:
                raise
            time.sleep(1.5 * (a + 1))


def series(key, d0):
    k = urllib.parse.quote(key, safe="")
    hist = candles_to_df(get("https://api.upstox.com/v3/historical-candle/%s/minutes/1/%s/%s" % (k, y, d0)) if d0 <= y else [])
    live = candles_to_df(get("https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/1" % k))
    return regular(merge_frames(hist, live), cfg)


candles, keys, cash = {}, {}, {}
for sym, d0 in sorted(first_day.items()):
    keys[sym] = uni.pick_future(sym, pd.Timestamp(d0).date(), cfg.roll_sessions)
    candles[sym] = series(keys[sym].key, d0)
print("symbols", len(candles), "| last candle", max(c.index[-1] for c in candles.values()))
count = {}
for c in candles.values():
    for d, n in c.groupby(c.index.date).size().items():
        count[d] = max(count.get(d, 0), n)
sessions = sorted(count)
full = [d for d in sessions if count[d] >= cfg.min_session_candles]


def days_after(ed, xd):
    n = sum(1 for d in full if ed < d <= xd)
    return n + (1 if xd not in full and xd > ed else 0)


rows, bad = [], 0
for t in trades:
    s, sym = t["s"], t["s"]["symbol"]
    assert keys[sym].trading_symbol == s["fut_symbol"]
    m, basis = candles[sym], "futures"
    ets = pd.Timestamp("%sT%s:00+05:30" % (t["day"], s["time"])) + pd.Timedelta(minutes=1)
    outs = run_policies(m, s["side"], s["stop"], [s["t1"], s["t2"], s["t3"]], ets, close_at_eod=False, trail=True)
    intr = s["fut"]["T1"]
    if abs(outs["T1"].entry - intr["entry"]) > 1e-6:        # the replay priced this one on the cash share (thin futures)
        ck = uni.get(sym).cash_key
        if ck not in cash:
            cash[ck] = series(ck, first_day[sym])
        m, basis = cash[ck], "cash"
        outs = run_policies(m, s["side"], s["stop"], [s["t1"], s["t2"], s["t3"]], ets, close_at_eod=False, trail=True)
    o1 = outs["T1"]
    if abs(o1.entry - intr["entry"]) > 1e-6 or (intr["status"] in ("target", "stopped") and (o1.status != intr["status"] or abs(o1.exit - intr["exit"]) > 1e-6)):
        bad += 1
        print("MISMATCH", t["day"], sym, o1.status, o1.entry, o1.exit, "vs replay", intr["status"], intr["entry"], intr["exit"])
    qty = s["lot"] * s["lots"]
    res = {}
    for pol, o in outs.items():
        net = round(o.points * qty - C.round_trip("FUT", o.entry, o.exit, qty, s["side"], cfg.brokerage_per_order, cfg.brokerage_pct)
                    - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
        res[pol] = {"status": o.status, "entry": o.entry, "exit": o.exit, "exit_ts": o.exit_ts, "reason": o.reason, "r": o.r, "net_rs": net,
                    "sessions": days_after(ets.date(), pd.Timestamp(o.exit_ts).date())}
    opt = (s.get("option") or {}).get("legs") or {}
    rows.append({"day": t["day"], "time": s["time"], "symbol": sym, "setup": s["setup"], "side": s["side"], "qty": qty, "lot": s["lot"], "lots": s["lots"],
                 "models": t["models"], "scores": s["scores"], "basis": basis, "stop": s["stop"], "t1": s["t1"], "t2": s["t2"], "t3": s["t3"],
                 "entry_ts": ets.isoformat(), "res": res,
                 "same_day": {p: {"status": s["fut"][p]["status"], "net_rs": s["fut"][p]["net_rs"], "r": s["fut"][p]["r"]} for p in ("T1", "T2", "T3", "CLOSE")},
                 "option": {p: {"status": opt[p].get("status"), "net_rs": opt[p].get("net_rs"), "entry": opt[p].get("entry")} for p in ("T1", "T2", "T3") if p in opt and opt[p].get("status") != "no_data"},
                 "opt_lot": (s.get("option") or {}).get("lot")})
print("trades", len(rows), "| data-check mismatches vs replay:", bad, "| priced on cash:", sum(r["basis"] == "cash" for r in rows))
old = {(r["day"], r["symbol"], r["setup"], r["time"]): r for r in json.load(open(os.path.join(sp, "t3_hold.json")))["rows"]}
diff = sum(1 for r in rows if (r["day"], r["symbol"], r["setup"], r["time"]) in old and any(
    abs(old[(r["day"], r["symbol"], r["setup"], r["time"])]["res"][p]["net_rs"] - r["res"][p]["net_rs"]) > 0.01 for p in ("T1", "T2", "T3")))
print("rows also in the earlier hold file:", sum((r["day"], r["symbol"], r["setup"], r["time"]) in old for r in rows), "| of those, different now:", diff)
json.dump({"days": [p["day"] for p in days], "full": [d.isoformat() for d in full], "rows": rows}, open(os.path.join(sp, "v2", "hold4.json"), "w"))
