# The scanner's own replay (EquityEngine.replay) for sessions whose futures contracts have expired.
# Same scan/score/fill code and config defaults as replay_multi.py. Differences, all because the September and
# October contracts can no longer be read without a paid data login:
#   * every stock is scanned and priced on its cash share (the engine's own "cash basis" fallback), sized with
#     today's futures lot size and costed as a futures trade;
#   * a stock counts as an F&O stock on a day only if its November futures contract had started trading by then;
#   * no option leg (those option contracts have expired too).
import asyncio, copy, json, os, pickle, sys, time
from datetime import date, datetime, timedelta
out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(out_dir, "multi.db")
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"
os.environ["SCANNER_TOKEN"] = ""
for k in [k for k in os.environ if k.startswith("EQ_")]:
    del os.environ[k]
from scanner.config import IST
from scanner.series import candles_to_df
from scanner.source import UpstoxSource
from scanner.equity.config import eq_settings as cfg
from scanner.equity.data import Throttle, fetch_range
from scanner.equity.engine import EquityEngine
from scanner.equity.features import session_days


class _Raw:
    def __init__(self, owner):
        self.owner = owner

    async def candles(self, key, unit, interval, to, frm):
        self.owner.net += 1
        return await UpstoxSource.candles(self.owner, key, unit, interval, to, frm)


class CashSource(UpstoxSource):
    def __init__(self):
        super().__init__("http://127.0.0.1:9", "", "")
        self.win, self.cache, self.locks, self.net, self.nifty_key = {}, {}, {}, 0, ""
        self.pace = Throttle(per_sec=5.0, per_30min=1900)
        self.raw = _Raw(self)

    async def candles(self, key, unit, interval, to, frm):
        if key.startswith("NSE_FO") and key != self.nifty_key:   # expired-month stand-in: force the cash basis
            return candles_to_df([])
        lo, hi = self.win.get(unit, (None, None))
        if lo is None or frm < lo or to > hi:
            await self.pace.wait()
            return await self.raw.candles(key, unit, interval, to, frm)
        k = (key, unit)
        async with self.locks.setdefault(k, asyncio.Lock()):
            if k not in self.cache:
                self.cache[k] = await fetch_range(self.raw, self.pace, key, unit, lo, hi)
        df = self.cache[k]
        if df.empty:
            return df
        d = df.index.date
        return df[(d >= frm) & (d <= to)]


async def one_day(src, uni, day, first):
    u2 = copy.copy(uni)
    u2.unds = {s: u for s, u in uni.unds.items() if u.kind != "EQUITY" or (first.get(s) is not None and first[s] <= day)}
    u2.pick_option = lambda *a, **k: None
    eng = EquityEngine(src)
    eng.uni = u2
    eng.thr = Throttle(per_sec=1e6, per_30min=10 ** 9)
    t0 = time.time()
    task = asyncio.create_task(eng.replay(day))
    while not task.done():
        await asyncio.sleep(20)
        print("   %s %4ds %s | net reads %d | errors %d" % (day, time.time() - t0, eng.replay_status.get("progress"), src.net, len(src.errors)), flush=True)
    await task
    res = eng.replay_result(day.isoformat())
    st = eng.replay_status
    if res and not st.get("error"):
        json.dump(res, open(os.path.join(out_dir, "replay_%s.json" % day), "w"))
        bases = {}
        for s in res["signals"]:
            bases[s.get("basis")] = bases.get(s.get("basis"), 0) + 1
        print("DONE %s in %ds: universe %d scanned %d signals %d %s basis %s | engine errors %d" % (
            day, time.time() - t0, res["universe"], res["scanned"], len(res["signals"]), res["counts"], bases, len(eng.status["errors"])), flush=True)
    else:
        print("FAILED %s: %s" % (day, st.get("error")), flush=True)


async def main():
    src = CashSource()
    uni = await src.load_universe()
    today = datetime.now(IST).date()
    lo, hi = [date.fromisoformat(x) for x in os.environ["RANGE"].split(":")]
    hold_to = today - timedelta(days=1)
    nf = uni.pick_future("NIFTY", today, cfg.roll_sessions)
    src.nifty_key = nf.key
    nifty = await fetch_range(src.raw, src.pace, nf.key, "minutes", lo - timedelta(days=20), hold_to)
    sessions = [d for d in session_days(nifty, cfg) if d < today]
    days = [d for d in sessions if lo <= d <= hi]
    print("replaying:", [d.isoformat() for d in days], flush=True)
    first, sem = {}, asyncio.Semaphore(4)

    async def f1(s):
        async with sem:
            f = uni.pick_future(s, lo, cfg.roll_sessions)
            await src.pace.wait()
            df = await src.raw.candles(f.key, "days", 1, hold_to, lo - timedelta(days=20))
            first[s] = df.index[0].date() if df is not None and not df.empty else None

    await asyncio.gather(*[f1(s) for s in uni.stocks])
    late = {s: (d.isoformat() if d else None) for s, d in first.items() if d is None or d > lo}
    print("F&O membership by first futures candle: %d stocks from the start, %d later or never: %s" % (len(first) - len(late), len(late), late), flush=True)
    json.dump({s: (d.isoformat() if d else None) for s, d in first.items()}, open(os.path.join(out_dir, "first_fut.json"), "w"))
    src.win = {"minutes": (days[0] - timedelta(days=14), hold_to), "days": (days[0] - timedelta(days=500), hold_to)}
    for day in days:
        await one_day(src, uni, day, first)
    print("source errors so far:", src.errors[-10:], "| net reads", src.net, flush=True)
    mins = {k[0]: df for k, df in src.cache.items() if k[1] == "minutes"}
    pickle.dump({"minutes": mins, "sessions": sessions, "cash_key": {s: uni.get(s).cash_key for s in uni.stocks},
                 "lot": {s: (uni.pick_future(s, lo, cfg.roll_sessions).lot_size, uni.pick_future(s, lo, cfg.roll_sessions).tick) for s in uni.stocks}},
                open(os.path.join(out_dir, "minutes.pkl"), "wb"), protocol=5)
    print("ALL DONE | net reads %d | source errors %d %s | cached minute series %d" % (src.net, len(src.errors), src.errors[-10:], len(mins)), flush=True)
    await src.close()

asyncio.run(main())
