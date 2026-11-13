import asyncio, os, sys
from datetime import date, timedelta
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/probe_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
from scanner.source import UpstoxSource
from scanner.equity.config import eq_settings as cfg
from scanner.equity.data import Throttle, fetch_range
from scanner.equity.features import session_days, regular

async def main():
    src = UpstoxSource("http://127.0.0.1:9", "", "")
    uni = await src.load_universe()
    thr = Throttle(per_sec=4.0, per_30min=1900)
    print("stocks", len(uni.stocks))
    for sym in ["NIFTY", "RELIANCE", "HDFCBANK", "LICI", "CUB", "ICICILIFE", "NAVINFLUOR"]:
        u = uni.get(sym)
        futs = sorted(u.futures, key=lambda f: f.expiry)
        print(sym, [(f.trading_symbol, f.expiry.isoformat(), f.lot_size) for f in futs], "cash", getattr(u, "cash_key", None))
        f = futs[0]
        for lo, hi in [(date(2026, 8, 24), date(2026, 9, 4)), (date(2026, 9, 14), date(2026, 9, 18)), (date(2026, 9, 28), date(2026, 10, 2))]:
            df = await fetch_range(src, thr, f.key, "minutes", lo, hi)
            r = regular(df, cfg) if df is not None and not df.empty else df
            by = {} if r is None or r.empty else r.groupby(r.index.date).agg(n=("close", "size"), vol=("volume", "sum")).to_dict("index")
            print("   fut", lo, hi, {d.isoformat()[5:]: (v["n"], int(v["vol"])) for d, v in by.items()})
        if sym != "NIFTY":
            df = await fetch_range(src, thr, u.cash_key, "minutes", date(2026, 9, 14), date(2026, 9, 18))
            r = regular(df, cfg)
            print("   cash", {d.isoformat()[5:]: n for d, n in r.groupby(r.index.date).size().items()})
    print("errors", src.errors[-5:])
    await src.close()
asyncio.run(main())
