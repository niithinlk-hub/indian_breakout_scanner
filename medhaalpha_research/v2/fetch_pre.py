# Cash 1-minute candles for 15 Oct 2025 - 19 Apr 2026 (the later months are already cached), daily candles from Jan 2024,
# and the Nifty 50 index, for every stock in the six-month signal file. Public Upstox candle endpoints, no login.
import asyncio, os, pickle, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
from scanner.source import UpstoxSource
from scanner.equity.data import Throttle, fetch_range
SP = sys.argv[1]
OUT = SP + "/v2/data"


async def main():
    keys = pickle.load(open(OUT + "/early.pkl", "rb"))["keys"]
    src = UpstoxSource("http://127.0.0.1:9", "", "")
    thr = Throttle(per_sec=5.0, per_30min=1900)
    mins, daily, sem, done = {}, {}, asyncio.Semaphore(4), [0]

    async def one(s):
        async with sem:
            k = keys[s]
            try:
                mins[k] = await fetch_range(src, thr, k, "minutes", date(2025, 10, 15), date(2026, 4, 19))
                daily[s] = await fetch_range(src, thr, k, "days", date(2024, 1, 1), date(2026, 11, 12))
            except Exception as e:  # noqa: BLE001
                print("FAILED", s, type(e).__name__, flush=True)
            done[0] += 1
            if done[0] % 20 == 0:
                print("   %d/%d | source errors %d" % (done[0], len(keys), len(src.errors)), flush=True)

    await asyncio.gather(*[one(s) for s in sorted(keys)])
    nifty = await fetch_range(src, thr, "NSE_INDEX|Nifty 50", "minutes", date(2025, 10, 15), date(2026, 4, 19))
    pickle.dump({"minutes": mins, "daily": daily, "nifty": nifty, "keys": keys}, open(OUT + "/pre.pkl", "wb"), protocol=5)
    empty = [s for s in keys if keys[s] not in mins or mins[keys[s]].empty]
    first = sorted((mins[keys[s]].index[0].date().isoformat(), s) for s in keys if keys[s] in mins and not mins[keys[s]].empty)
    print("ALL DONE | series", len(mins), "| rows", sum(len(v) for v in mins.values()), "| nifty", len(nifty), "| no data:", empty, "| latest-starting:", first[-8:], "| source errors", len(src.errors), src.errors[-3:], flush=True)
    await src.close()

asyncio.run(main())
