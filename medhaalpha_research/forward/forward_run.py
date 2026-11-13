#!/usr/bin/env python3
"""Forward test, one session a run: the scanner's own replay (frozen patched copy in pkg/, five score models) on
that day's real futures candles, option legs included, from Upstox's public candle endpoints (no login).

usage:  forward_run.py <base_dir> [YYYY-MM-DD] [--dry]
  base_dir   the folder holding pkg/ and state/
  date       the session to replay; default is today in India
  --dry      replay and print, but write nothing under state/ (for testing)

Writes state/days/<date>.json (every setup A/B signal of the day, compact) and rebuilds state/log.json,
state/summary.md and the three CSV files the results page reads. Running it again for a day already stored only
rebuilds the totals. Exit code 0 also when the market was shut that day (recorded in state/no_session.json).
"""
import asyncio, csv, json, os, sys, time
from datetime import date, datetime, timedelta

BASE = os.path.abspath(sys.argv[1])
ARGS = [a for a in sys.argv[2:] if not a.startswith("--")]
DRY = "--dry" in sys.argv
sys.path.insert(0, os.path.join(BASE, "pkg"))
os.makedirs(os.path.join(BASE, "tmp"), exist_ok=True)
os.makedirs(os.path.join(BASE, "state", "days"), exist_ok=True)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(BASE, "tmp", "kv_%d.db" % os.getpid())
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"
os.environ["SCANNER_TOKEN"] = ""
for k in [k for k in os.environ if k.startswith("EQ_")]:
    del os.environ[k]

import numpy as np
from scanner.config import IST
from scanner.source import UpstoxSource
from scanner.equity.config import eq_settings as cfg
from scanner.equity.data import Throttle, fetch_range
from scanner.equity.engine import EquityEngine
from scanner.equity.score import MODELS, LABELS, min_score

START = os.environ.get("FWD_TEST_START", "2026-11-16")   # first forward session: nothing before it counts (the override is for testing only)
SCEN = {"opus": "T1", "opus_v2": "T1", "opus_v3": "T1", "fable": "T3", "fable_op": "T3"}     # the exit each model is judged on
POLS = ("T1", "T2", "T3", "CLOSE")
STATE = os.path.join(BASE, "state")


class _Raw:
    def __init__(self, owner):
        self.owner = owner

    async def candles(self, key, unit, interval, to, frm):
        self.owner.net += 1
        return await UpstoxSource.candles(self.owner, key, unit, interval, to, frm)


class CachedSource(UpstoxSource):
    """Each instrument's history is read once for the whole look-back window and sliced per request."""
    def __init__(self):
        super().__init__("http://127.0.0.1:9", "", "")
        self.win, self.cache, self.locks, self.intr, self.net = {}, {}, {}, {}, 0
        self.pace = Throttle(per_sec=5.0, per_30min=1900)
        self.raw = _Raw(self)

    async def candles(self, key, unit, interval, to, frm):
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

    async def intraday(self, key, unit, interval):
        if key not in self.intr:
            await self.pace.wait()
            self.net += 1
            self.intr[key] = await UpstoxSource.intraday(self, key, unit, interval)
        return self.intr[key]


async def replay(day: date):
    src = CachedSource()
    uni = await src.load_universe()
    y = day - timedelta(days=1)
    src.win = {"minutes": (day - timedelta(days=14), y), "days": (day - timedelta(days=500), y)}
    eng = EquityEngine(src)
    eng.uni = uni
    eng.thr = Throttle(per_sec=1e6, per_30min=10 ** 9)
    t0 = time.time()
    task = asyncio.create_task(eng.replay(day))
    while not task.done():
        await asyncio.sleep(30)
        print("   %4ds %s | reads %d | source errors %d" % (time.time() - t0, eng.replay_status.get("progress"), src.net, len(src.errors)), flush=True)
    await task
    res, st = eng.replay_result(day.isoformat()), dict(eng.replay_status)
    errs, serr = list(eng.status["errors"]), list(src.errors)
    await src.close()
    return res, st, errs, serr, src.net


def compact(res: dict) -> dict:
    """One row per setup A/B signal: enough to re-pick any model's trades and total any exit, futures and options."""
    rows = []
    for s in res["signals"]:
        if s["setup"] not in ("A", "B"):
            continue
        opt = s.get("option") or {}
        legs = opt.get("legs") or {}
        rows.append({
            "time": s["time"], "symbol": s["symbol"], "setup": s["setup"], "side": s["side"], "scores": {m: s["scores"][m] for m in MODELS},
            "live": [m for m in MODELS if "live" in s["in"][m]], "rel_vol": s.get("rel_vol"), "lot": s.get("lot"), "lots": s.get("lots"),
            "fut_symbol": s.get("fut_symbol"), "entry_ref": s.get("entry_ref"), "stop": s.get("stop"), "t1": s.get("t1"), "t2": s.get("t2"), "t3": s.get("t3"),
            "fut": {p: [s["fut"][p]["status"], s["fut"][p]["net_rs"], s["fut"][p]["r"], s["fut"][p].get("exit_ts", "")] for p in POLS if p in s["fut"]},
            "opt_symbol": opt.get("symbol"), "opt_qty": (opt.get("lot") or 0) * (s.get("lots") or 0) if opt else None,
            "opt": {p: [legs[p].get("status"), legs[p].get("net_rs"), legs[p].get("entry"), legs[p].get("exit")] for p in POLS
                    if p in legs and legs[p].get("status") not in (None, "no_data")}})
    return {"day": res["day"], "run_at": res.get("run_at"), "universe": res["universe"], "scanned": res["scanned"], "signals": len(res["signals"]),
            "counts": res["counts"], "min_scores": {m: min_score(cfg, m) for m in MODELS}, "rows": rows}


def rebuild():
    days = []
    for f in sorted(os.listdir(os.path.join(STATE, "days"))):
        if f.endswith(".json") and f[:10] >= START:
            days.append(json.load(open(os.path.join(STATE, "days", f))))
    out = {"start": START, "updated": datetime.now(IST).isoformat(timespec="seconds"), "sessions": [d["day"] for d in days], "exit_judged_on": SCEN, "models": {}}
    trades, dayrows = [], []
    for m in MODELS:
        pol = SCEN[m]
        tot = {"label": LABELS[m], "exit": pol, "trades": 0, "reached_t1": 0, "stopped": 0, "won": 0, "futures": {p: 0.0 for p in POLS},
               "options": {p: 0.0 for p in POLS}, "options_priced": 0, "days_up": 0, "days_down": 0, "days_no_trade": 0}
        fser, oser = [], []
        for d in days:
            pick = [r for r in d["rows"] if m in r["live"]]
            f = sum(r["fut"][pol][1] for r in pick)
            o = sum(r["opt"][pol][1] for r in pick if pol in r["opt"])
            fser.append(f); oser.append(o)
            tot["trades"] += len(pick)
            tot["reached_t1"] += sum(r["fut"]["T1"][0] == "target" for r in pick)
            tot["stopped"] += sum(r["fut"]["T1"][0] == "stopped" for r in pick)
            tot["won"] += sum(r["fut"][pol][1] > 0 for r in pick)
            tot["options_priced"] += sum(pol in r["opt"] for r in pick)
            for p in POLS:
                tot["futures"][p] += sum(r["fut"][p][1] for r in pick)
                tot["options"][p] += sum(r["opt"][p][1] for r in pick if p in r["opt"])
            tot["days_up"] += f > 0; tot["days_down"] += f < 0; tot["days_no_trade"] += not pick
            dayrows.append({"day": d["day"], "model": LABELS[m], "exit": pol, "trades": len(pick), "reached_t1": sum(r["fut"]["T1"][0] == "target" for r in pick),
                            "stopped": sum(r["fut"]["T1"][0] == "stopped" for r in pick), "futures_net": round(f), "options_net": round(o),
                            "options_priced": sum(pol in r["opt"] for r in pick)})
            for r in pick:
                trades.append({"day": d["day"], "time": r["time"], "model": LABELS[m], "symbol": r["symbol"], "side": r["side"], "score": r["scores"][m], "exit": pol,
                               "futures_result": r["fut"][pol][0], "futures_net": round(r["fut"][pol][1]), "option": r["opt_symbol"] or "",
                               "options_net": round(r["opt"][pol][1]) if pol in r["opt"] else ""})
        tot["futures"] = {p: round(v) for p, v in tot["futures"].items()}
        tot["options"] = {p: round(v) for p, v in tot["options"].items()}
        tot["futures_net"], tot["options_net"] = tot["futures"][pol], tot["options"][pol]
        tot["futures_by_day"], tot["options_by_day"] = [round(x) for x in fser], [round(x) for x in oser]
        out["models"][m] = tot
    # paired comparisons by day, resampled; meaningful only once there are enough sessions
    out["compare"] = {}
    n = len(days)
    if n >= 10:
        rng = np.random.default_rng(7)
        ix = rng.integers(0, n, size=(20000, n))
        for a, b in (("opus_v3", "opus"), ("opus_v3", "fable_op"), ("fable_op", "opus")):
            for kind in ("futures", "options"):
                x = np.array(out["models"][a][kind + "_by_day"], float); y = np.array(out["models"][b][kind + "_by_day"], float)
                d = (x - y)[ix].sum(axis=1)
                own = x[ix].sum(axis=1)
                out["compare"]["%s_vs_%s_%s" % (a, b, kind)] = {"difference": round(float((x - y).sum())), "ahead_pct": round(float(100 * (d > 0).mean()), 1),
                                                               "first_in_profit_pct": round(float(100 * (own > 0).mean()), 1)}
    if os.path.exists(os.path.join(STATE, "no_session.json")):
        out["no_session"] = json.load(open(os.path.join(STATE, "no_session.json")))
    json.dump(out, open(os.path.join(STATE, "log.json"), "w"), indent=1)
    for name, rows_, cols in (("models.csv", [{"model": v["label"], "exit": v["exit"], "sessions": n, "trades": v["trades"], "reached_t1": v["reached_t1"], "stopped": v["stopped"],
                                                "reached_t1_pct": round(100 * v["reached_t1"] / v["trades"], 1) if v["trades"] else 0,
                                                "stopped_pct": round(100 * v["stopped"] / v["trades"], 1) if v["trades"] else 0,
                                                "futures_net": v["futures_net"], "options_net": v["options_net"], "options_priced": v["options_priced"],
                                                "days_up": v["days_up"], "days_down": v["days_down"], "days_no_trade": v["days_no_trade"]} for v in out["models"].values()],
                               ["model", "exit", "sessions", "trades", "reached_t1", "stopped", "reached_t1_pct", "stopped_pct", "futures_net", "options_net", "options_priced", "days_up", "days_down", "days_no_trade"]),
                              ("days.csv", dayrows, ["day", "model", "exit", "trades", "reached_t1", "stopped", "futures_net", "options_net", "options_priced"]),
                              ("trades.csv", trades, ["day", "time", "model", "symbol", "side", "score", "exit", "futures_result", "futures_net", "option", "options_net"])):
        with open(os.path.join(STATE, name), "w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerows(rows_)
    L = ["# Forward test: %d session%s from %s%s" % (n, "" if n == 1 else "s", START, " to " + days[-1]["day"] if days else ""), "",
         "Real futures and option candles, same-day exit. Opus, Opus v2 and Opus v3 are judged at T1; Fable and Fable-OP at T3.", "",
         "| Model | Exit | Trades | Reached T1 | Stopped | Futures net (Rs) | Options net (Rs) | Options priced |", "|---|---|---|---|---|---|---|---|"]
    for v in out["models"].values():
        L.append("| %s | %s | %d | %d | %d | %+d | %+d | %d |" % (v["label"], v["exit"], v["trades"], v["reached_t1"], v["stopped"], v["futures_net"], v["options_net"], v["options_priced"]))
    if days:
        last = days[-1]["day"]
        L += ["", "Latest session, %s:" % last, ""]
        for m in MODELS:
            x = [t for t in trades if t["day"] == last and t["model"] == LABELS[m]]
            L.append("- %s: %d trade%s, futures %+d, options %+d%s" % (LABELS[m], len(x), "" if len(x) == 1 else "s", sum(t["futures_net"] for t in x),
                     sum(t["options_net"] or 0 for t in x), (" (" + ", ".join("%s %s" % (t["symbol"], t["side"][0]) for t in x) + ")") if x else ""))
    for k, v in out["compare"].items():
        L.append("- %s: difference %+d, ahead in %.0f %% of resamples" % (k.replace("_", " "), v["difference"], v["ahead_pct"]))
    open(os.path.join(STATE, "summary.md"), "w").write("\n".join(L) + "\n")
    return out, "\n".join(L)


def main():
    now = datetime.now(IST)
    day = date.fromisoformat(ARGS[0]) if ARGS else now.date()
    path = os.path.join(STATE, "days", day.isoformat() + ".json")
    if day.weekday() >= 5:
        print("NO SESSION: %s is a weekend" % day)
    elif day == now.date() and (now.hour, now.minute) < (15, 35):
        print("TOO EARLY: the session of %s has not closed (now %s IST)" % (day, now.strftime("%H:%M")))
        return 2
    elif os.path.exists(path) and not DRY:
        print("already stored:", path)
    else:
        res, st, errs, serr, reads = asyncio.run(replay(day))
        if not res or st.get("error"):
            msg = str(st.get("error"))
            if "no regular session" in msg and day == now.date():
                print("NO SESSION on %s (market holiday): %s" % (day, msg))
                if not DRY:
                    p = os.path.join(STATE, "no_session.json")
                    cur = json.load(open(p)) if os.path.exists(p) else []
                    json.dump(sorted(set(cur + [day.isoformat()])), open(p, "w"))
            elif "no regular session" in msg:
                # a past day: either a holiday, or its candles have not reached the history endpoint yet (they
                # leave the same-day endpoint at midnight and arrive in history some hours later). Not recorded.
                print("NO DATA for %s: holiday, or history not loaded yet. Nothing recorded; try again later." % day)
                return 3
            else:
                print("REPLAY FAILED for %s: %s | engine errors %s | source errors %s" % (day, msg, errs[-3:], serr[-3:]))
                return 1
        else:
            c = compact(res)
            bad = len(errs) + len(serr)
            print("replayed %s: stocks scanned %d of %d, signals %d %s, reads %d, engine errors %d, source errors %d" % (day, res["scanned"], res["universe"], len(res["signals"]), res["counts"], reads, len(errs), len(serr)))
            if res["scanned"] < 0.9 * res["universe"] or bad > 20:
                print("INCOMPLETE: too many stocks failed to load; not stored. Run again later.", errs[-3:], serr[-3:])
                return 1
            for m in MODELS:
                pick = [r for r in c["rows"] if m in r["live"]]
                pol = SCEN[m]
                print("  %-9s exit %s: %d trades, futures %+8.0f, options %+8.0f (%d priced) %s" % (LABELS[m], pol, len(pick), sum(r["fut"][pol][1] for r in pick),
                      sum(r["opt"][pol][1] for r in pick if pol in r["opt"]), sum(pol in r["opt"] for r in pick), " ".join("%s(%s)" % (r["symbol"], r["side"][0]) for r in pick)))
            if DRY:
                print("dry run: nothing written")
                return 0
            if day.isoformat() < START:
                print("before the forward start (%s): not stored" % START)
                return 0
            json.dump(c, open(path, "w"))
    if not DRY:
        out, text = rebuild()
        print("\n" + text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
