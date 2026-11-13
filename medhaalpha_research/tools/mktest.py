import asyncio, gzip, json, os, sys, urllib.request, urllib.parse
from datetime import datetime, date
T = sys.argv[1]
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(T, "scanner.db")
from scanner.config import IST
from scanner.equity.universe_upstox import parse
from scanner.equity import store
from scanner.equity.config import EqConfig
from scanner.equity.levels import build_levels
from scanner.equity.scan import lots_for
from scanner.equity.score import all_scores
from scanner.series import candles_to_df
from scanner import db
import pandas as pd
cfg = EqConfig()
def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/8"})
    return urllib.request.urlopen(req, timeout=60).read()
raw = get("https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz")
open(os.path.join(T, "NSE.json.gz"), "wb").write(raw)
data = gzip.decompress(raw)
print("instrument file", len(raw), "->", len(data), "bytes; first record:", data[:400])
uni = parse(json.loads(data))
today = datetime.now(IST).date()
def candles(key):
    body = get("https://api.upstox.com/v3/historical-candle/intraday/" + urllib.parse.quote(key, safe="") + "/minutes/1")
    open(os.path.join(T, key.replace("|", "_") + ".json"), "wb").write(body)
    return candles_to_df(json.loads(body)["data"]["candles"])
plan = [("RELIANCE", "A", "LONG", "09:21"), ("SBIN", "A", "LONG", "09:21"), ("TCS", "B", "SHORT", "09:40"),
        ("INFY", "A", "LONG", "10:05"), ("HDFCBANK", "A", "LONG", "11:30")]
day = today.isoformat()
for i, (sym, setup, side, hm) in enumerate(plan):
    fut = uni.pick_future(sym, today, cfg.roll_sessions)
    fm = candles(fut.key)
    ts = pd.Timestamp(f"{day}T{hm}:00+05:30")
    row = fm[fm.index <= ts].iloc[-1]
    px = float(row["close"])
    snap = {"price": px, "atr_pct": 1.6, "day_chg": [1.9, 0.5, 1.7, 1.4, 0.3][i], "pos": [0.88, 0.99, 0.93, 0.85, 1.0][i],
            "mins_since_extreme": [0, 0, 1, 2, 30][i], "minutes_since_open": (ts.hour * 60 + ts.minute) - 555 + 1,
            "nifty_chg": [-0.1, -0.1, -0.4, 0.1, 0.5][i], "from_open": 1.2, "beyond_vwap": 0.6, "gap": 0.3, "rsi14": 58.0,
            "rel_vol": 1.5 + i, "n_break": 5, "from_52w_high": -4.0, "from_52w_low": 30.0}
    lv = build_levels(side, px, snap["atr_pct"], snap, fut.tick, cfg)
    sc = all_scores(snap, side, lv.chosen, lv.risk, lv.entry_ref, cfg)
    opt = uni.pick_option(sym, fut.expiry, "CE" if side == "LONG" else "PE", px)
    candles(opt.key)
    lots = lots_for(side, lv.entry_ref, lv.stop, fut.lot_size, cfg)
    model = "opus"
    feat = dict(snap, score=sc[model]["score"], score_model=model, scores={m: v["score"] for m, v in sc.items()},
                score_parts={m: v["parts"] for m, v in sc.items()}, lots=lots)
    if i == 3:
        feat["scores"].pop("fable_op"); feat["score_parts"].pop("fable_op")     # a row logged before fable_op existed
    action = "fired" if sc[model]["score"] >= 75 and lots else "below_score"
    sid = store.add_signal(day=day, ts=ts.isoformat(), symbol=sym, setup=setup, side=side, action=action, rank_rel_vol=snap["rel_vol"],
                           rank_n_break=5.0, fut_key=fut.key, fut_symbol=fut.trading_symbol, opt_key=opt.key, opt_symbol=opt.trading_symbol,
                           levels=lv.to_dict(), features=feat, note="test")
    print(sym, setup, hm, "px", px, "scores", feat["scores"], "lots", lots, action, "fut lot", fut.lot_size, fut.key, opt.key)
    if action == "fired":
        ets = (ts + pd.Timedelta(minutes=1)).isoformat()
        store.add_trade(signal_id=sid, instrument="FUT", key=fut.key, trading_symbol=fut.trading_symbol, side=side, qty=fut.lot_size * lots,
                        entry_ts=ets, entry=None, stop=lv.stop, targets=lv.targets, status="open",
                        outcomes={"T1": {"status": "open", "entry": px, "exit": px, "r": 0.0, "net_rs": -150.0}})
db.kv_set("eq_min_scores", {"opus": 75})
store.add_near_miss(day=day, ts=f"{day}T09:30:00+05:30", symbol="ITC", setup="A", failed="pos >= 0.7", features={})
