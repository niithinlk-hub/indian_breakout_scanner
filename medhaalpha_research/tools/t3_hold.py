# Opus vs Fable-OP held for T3 across days: the live paper ledger's method (fills.run_policies without the
# end-of-day square-off), applied to the trades the live rule picks in each day's replay.
import glob, gzip, json, os, sys, time, urllib.parse, urllib.request
import pandas as pd
from scanner.series import candles_to_df, merge_frames
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import run_policies
from scanner.equity.universe_upstox import parse

sp, out_json = sys.argv[1], sys.argv[2]
cfg = EqConfig()
days = sorted((json.load(open(p)) for d in ("replay_oct", "replay_nov2", "replay7") for p in glob.glob(os.path.join(sp, d, "replay_*.json"))), key=lambda p: p["day"])
assert len({p["day"] for p in days}) == len(days)
print("sessions:", [p["day"] for p in days])
uni = parse(json.loads(gzip.decompress(open(os.path.join(sp, "test", "NSE.json.gz"), "rb").read())))
MODELS = ("opus", "fable_op")
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


def get(url):
    for a in range(4):
        try:
            time.sleep(0.25)
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/8"})
            return json.load(urllib.request.urlopen(req, timeout=40))["data"]["candles"]
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 400 or a == 3:
                print("READ FAILED", getattr(e, "code", type(e).__name__), url[38:], (e.read()[:200] if hasattr(e, "read") else ""), flush=True)
                raise
            time.sleep(1.5 * (a + 1))


candles, keys = {}, {}
for sym, d0 in sorted(first_day.items()):
    fut = uni.pick_future(sym, pd.Timestamp(d0).date(), cfg.roll_sessions)
    keys[sym] = fut
    k = urllib.parse.quote(fut.key, safe="")
    y = str((pd.Timestamp(today) - pd.Timedelta(days=1)).date())
    hist = candles_to_df(get("https://api.upstox.com/v3/historical-candle/%s/minutes/1/%s/%s" % (k, y, d0)) if d0 <= y else [])
    live = candles_to_df(get("https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/1" % k))
    candles[sym] = regular(merge_frames(hist, live), cfg)
print("symbols", len(candles), "| last candle", max(c.index[-1] for c in candles.values()))
sessions = sorted({d for c in candles.values() for d in set(c.index.date)})
count = {}
for c in candles.values():
    for d, n in c.groupby(c.index.date).size().items():
        count[d] = max(count.get(d, 0), n)
full = [d for d in sessions if count[d] >= cfg.min_session_candles]
print("special (short) sessions:", [str(d) for d in sessions if d not in full])


def days_after(ed, xd):
    """Full trading sessions from the entry day to the exit day; an exit in a short special session counts as the next one."""
    n = sum(1 for d in full if ed < d <= xd)
    return n + (1 if xd not in full and xd > ed else 0)
rows, bad, cash = [], 0, {}
for t in trades:
    s, sym = t["s"], t["s"]["symbol"]
    fut = keys[sym]
    assert fut.trading_symbol == s["fut_symbol"], (fut.trading_symbol, s["fut_symbol"])
    m = candles[sym]
    ets = pd.Timestamp("%sT%s:00+05:30" % (t["day"], s["time"])) + pd.Timedelta(minutes=1)
    outs = run_policies(m, s["side"], s["stop"], [s["t1"], s["t2"], s["t3"]], ets, close_at_eod=False, trail=True)
    qty = s["lot"] * s["lots"]
    intr = s["fut"]["T1"]                                   # the replay's own same-day result, as a data check
    basis = "futures"
    if abs(outs["T1"].entry - intr["entry"]) > 1e-6:        # the replay priced this one on the cash share (thin futures)
        ck = uni.get(sym).cash_key
        if ck not in cash:
            kq = urllib.parse.quote(ck, safe="")
            h = candles_to_df(get("https://api.upstox.com/v3/historical-candle/%s/minutes/1/%s/%s" % (kq, y, first_day[sym])) if first_day[sym] <= y else [])
            cash[ck] = regular(merge_frames(h, candles_to_df(get("https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/1" % kq))), cfg)
        m, basis = cash[ck], "cash"
        outs = run_policies(m, s["side"], s["stop"], [s["t1"], s["t2"], s["t3"]], ets, close_at_eod=False, trail=True)
    o1 = outs["T1"]
    if abs(o1.entry - intr["entry"]) > 1e-6 or (intr["status"] in ("target", "stopped") and (o1.status != intr["status"] or abs(o1.exit - intr["exit"]) > 1e-6)):
        bad += 1
        print("MISMATCH", t["day"], sym, o1.status, o1.entry, o1.exit, "vs replay", intr["status"], intr["entry"], intr["exit"])
    res = {}
    for pol, o in outs.items():
        gross = round(o.points * qty, 2)
        net = round(gross - C.round_trip("FUT", o.entry, o.exit, qty, s["side"], cfg.brokerage_per_order, cfg.brokerage_pct)
                    - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
        xd = pd.Timestamp(o.exit_ts).date()
        res[pol] = {"status": o.status, "entry": o.entry, "exit": o.exit, "exit_ts": o.exit_ts, "reason": o.reason, "r": o.r, "net_rs": net,
                    "sessions": days_after(ets.date(), xd)}
    rows.append({"day": t["day"], "time": s["time"], "symbol": sym, "setup": s["setup"], "side": s["side"], "qty": qty, "models": t["models"],
                 "scores": s["scores"], "basis": basis, "stop": s["stop"], "t1": s["t1"], "t2": s["t2"], "t3": s["t3"], "res": res,
                 "intraday": {p: {"status": s["fut"][p]["status"], "net_rs": s["fut"][p]["net_rs"]} for p in ("T1", "T3")}})
print("trades", len(rows), "| data-check mismatches vs replay:", bad)
json.dump({"sessions": [d.isoformat() for d in sessions], "days": [p["day"] for p in days], "rows": rows}, open(out_json, "w"))
