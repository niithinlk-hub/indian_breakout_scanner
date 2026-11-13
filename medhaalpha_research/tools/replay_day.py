# Run the scanner's own after-close replay (EquityEngine.replay) for one day, off the VPS.
# Same code as the VPS image, config defaults, public Upstox candles (no token), a throwaway local database.
import asyncio, json, os, sys, time
from datetime import date
out_dir, day = sys.argv[1], sys.argv[2]
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(out_dir, "replay_%s.db" % day)
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"
os.environ["SCANNER_TOKEN"] = ""
for k in [k for k in os.environ if k.startswith("EQ_")]:
    del os.environ[k]
from scanner.source import UpstoxSource
from scanner.equity.engine import EquityEngine


async def main():
    src = UpstoxSource("http://127.0.0.1:9", "", "")
    eng = EquityEngine(src)
    t0 = time.time()
    task = asyncio.create_task(eng.replay(date.fromisoformat(day)))
    while not task.done():
        await asyncio.sleep(20)
        print("%4ds %s | calls %d | source errors %d" % (time.time() - t0, eng.replay_status.get("progress"), src.calls, len(src.errors)), flush=True)
    await task
    print("status", json.dumps(eng.replay_status), flush=True)
    print("source errors (last 15):", src.errors[-15:])
    print("engine errors:", eng.status["errors"])
    res = eng.replay_result(day)
    if res:
        json.dump(res, open(os.path.join(out_dir, "replay_%s.json" % day), "w"))
        print("saved; universe", res["universe"], "scanned", res["scanned"], "signals", len(res["signals"]), "counts", res["counts"])
    await src.close()

asyncio.run(main())
