# The scanner's own replay (EquityEngine.replay) over several sessions, off the VPS.
# Same scan/score/fill code as the VPS image and config defaults. The only addition is a read cache: each
# instrument's candles are fetched once for the whole window and sliced per request, so 8 days cost about
# the same number of Upstox reads as one. Public candle endpoints, no token, a throwaway local database.
import asyncio, json, os, sys, time
from datetime import date, datetime, timedelta
out_dir, n_past, today_after = sys.argv[1], int(sys.argv[2]), sys.argv[3]          # today_after "HH:MM" IST or "-"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(out_dir, "multi.db")
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"
os.environ["SCANNER_TOKEN"] = ""
for k in [k for k in os.environ if k.startswith("EQ_")]:
    del os.environ[k]
from scanner.config import IST
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


class CachedSource(UpstoxSource):
    def __init__(self):
        super().__init__("http://127.0.0.1:9", "", "")
        self.win, self.cache, self.locks, self.intr, self.net = {}, {}, {}, {}, 0
        self.pace = Throttle(per_sec=5.0, per_30min=1900)       # real network reads only
        self.raw = _Raw(self)

    async def candles(self, key, unit, interval, to, frm):
        lo, hi = self.win.get(unit, (None, None))
        if lo is None or frm < lo or to > hi:                    # outside the cached window: a plain read
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

    async def intraday(self, key, unit, interval):
        if key not in self.intr:
            await self.pace.wait()
            self.net += 1
            self.intr[key] = await UpstoxSource.intraday(self, key, unit, interval)
        return self.intr[key]


async def one_day(src, uni, day):
    eng = EquityEngine(src)
    eng.uni = uni
    eng.thr = Throttle(per_sec=1e6, per_30min=10 ** 9)           # reads are paced inside the source instead
    t0 = time.time()
    task = asyncio.create_task(eng.replay(day))
    while not task.done():
        await asyncio.sleep(15)
        print("   %s %4ds %s | net reads %d | errors %d" % (day, time.time() - t0, eng.replay_status.get("progress"), src.net, len(src.errors)), flush=True)
    await task
    res = eng.replay_result(day.isoformat())
    st = eng.replay_status
    if res and not st.get("error"):
        json.dump(res, open(os.path.join(out_dir, "replay_%s.json" % day), "w"))
        print("DONE %s in %ds: universe %d scanned %d signals %d %s | engine errors %d" % (
            day, time.time() - t0, res["universe"], res["scanned"], len(res["signals"]), res["counts"], len(eng.status["errors"])), flush=True)
    else:
        print("FAILED %s: %s" % (day, st.get("error")), flush=True)
    return eng.uni


async def main():
    src = CachedSource()
    uni = await src.load_universe()
    today = datetime.now(IST).date()
    nf = uni.pick_future("NIFTY", today, cfg.roll_sessions)
    nifty = await fetch_range(src.raw, src.pace, nf.key, "minutes", today - timedelta(days=28), today - timedelta(days=1))
    sessions = [d for d in session_days(nifty, cfg) if d < today]
    days = sessions[-n_past:]
    if os.environ.get("RANGE"):
        lo, hi = [date.fromisoformat(x) for x in os.environ["RANGE"].split(":")]
        days = [d for d in sessions if lo <= d <= hi]
    print("sessions found before today:", [d.isoformat() for d in sessions], flush=True)
    print("replaying:", [d.isoformat() for d in days], flush=True)
    last = days[-1] if os.environ.get("RANGE") else today - timedelta(days=1)
    src.win = {"minutes": (days[0] - timedelta(days=14), last), "days": (days[0] - timedelta(days=500), last)}
    for day in days:
        uni = await one_day(src, uni, day)
    print("source errors so far:", src.errors[-10:], "| net reads", src.net, flush=True)
    if today_after != "-":
        h, m = [int(x) for x in today_after.split(":")]
        wait = (datetime.now(IST).replace(hour=h, minute=m, second=0, microsecond=0) - datetime.now(IST)).total_seconds()
        if wait > 0:
            print("waiting %d s for today's close" % wait, flush=True)
            await asyncio.sleep(wait)
        uni = await one_day(src, uni, today)
    print("ALL DONE | net reads %d | source errors %d %s" % (src.net, len(src.errors), src.errors[-10:]), flush=True)
    await src.close()

asyncio.run(main())
