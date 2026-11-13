# Cash 1-minute and daily candles for every stock in the six-month signal file, 20 Apr - 17 Aug 2026 (the later
# part is already cached from the September run), plus the Nifty 50 index. Public Upstox candle endpoints.
import asyncio, os, pickle, sys
from datetime import date
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
sys.path.insert(0, sys.argv[1] + "/v2")
from base import SIG, SP
from scanner.source import UpstoxSource
from scanner.equity.data import Throttle, fetch_range

OUT = SP + "/v2/data"
os.makedirs(OUT, exist_ok=True)


async def main():
    src = UpstoxSource("http://127.0.0.1:9", "", "")
    uni = await src.load_universe()
    thr = Throttle(per_sec=5.0, per_30min=1900)
    syms = sorted({s[1] for x in SIG["days"] for s in x["signals"]})
    late = pickle.load(open(SP + "/replay_sep/minutes.pkl", "rb"))
    have = set(late["minutes"])
    keys = {s: uni.cash_key(s) for s in syms}
    print("symbols", len(syms), "| no cash key:", [s for s in syms if not keys[s]], "| not in late cache:", [s for s in syms if keys[s] not in have], flush=True)
    mins, daily, sem, done = {}, {}, asyncio.Semaphore(4), [0]

    async def one(s):
        async with sem:
            k = keys[s]
            hi = date(2026, 8, 17) if k in have else date(2026, 11, 12)
            try:
                mins[k] = await fetch_range(src, thr, k, "minutes", date(2026, 4, 20), hi)
                daily[s] = await fetch_range(src, thr, k, "days", date(2024, 11, 1), date(2026, 11, 12))
            except Exception as e:  # noqa: BLE001
                print("FAILED", s, type(e).__name__, flush=True)
            done[0] += 1
            if done[0] % 20 == 0:
                print("   %d/%d | source errors %d" % (done[0], len(syms), len(src.errors)), flush=True)

    await asyncio.gather(*[one(s) for s in syms if keys[s]])
    nifty = await fetch_range(src, thr, "NSE_INDEX|Nifty 50", "minutes", date(2026, 4, 20), date(2026, 11, 12))
    print("nifty index candles", len(nifty), nifty.index[0] if len(nifty) else None, nifty.index[-1] if len(nifty) else None, flush=True)
    pickle.dump({"minutes": mins, "daily": daily, "nifty": nifty, "keys": keys}, open(OUT + "/early.pkl", "wb"), protocol=5)
    print("ALL DONE | series", len(mins), "| rows", sum(len(v) for v in mins.values()), "| source errors", len(src.errors), src.errors[-5:], flush=True)
    await src.close()

asyncio.run(main())
