# Dry run: today's live scanner signals re-decided as if another score model had been the live one.
# Reads the live scanner's SQLite file read-only, prices would-be trades from public Upstox candles.
# Writes nothing to the live database, holds no credential, never talks to the engine.
import base64, glob, gzip, json, os, re, shutil, sqlite3, sys, time, traceback
from datetime import datetime
from urllib.parse import quote

import httpx
import pandas as pd

from scanner.config import IST
from scanner.series import candles_to_df
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import LIVE_POLICIES, option_leg, run_policies
from scanner.equity.rules import enabled
from scanner.equity.scan import lots_for
from scanner.equity.score import MODELS, fable_op_score, min_score

MODEL = os.environ.get("DRY_MODEL", "fable_op")
DATA_DIR = os.environ.get("DRY_DATA_DIR", "/data")
OFFLINE = os.environ.get("DRY_OFFLINE_DIR", "")          # tests only: candle files instead of the network
FINAL_AT = os.environ.get("DRY_FINAL_AT", "15:31")       # IST; a second pass runs once the session has closed
UPSTOX = "https://api.upstox.com"
INSTRUMENTS = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
cfg = EqConfig.from_env()
client = httpx.Client(timeout=30.0, headers={"Accept": "application/json"})
notes = []


def say(*a):
    print(*a, flush=True)


def is_sqlite(p):
    try:
        with open(p, "rb") as fh:
            return fh.read(16) == b"SQLite format 3\x00"
    except OSError:
        return False


def open_db():
    """The live database, opened read-only. Falls back to a private copy if the read-only open is refused."""
    files = [p for p in glob.glob(os.path.join(DATA_DIR, "**", "*"), recursive=True) if os.path.isfile(p) and is_sqlite(p)]
    for p in sorted(files, key=os.path.getmtime, reverse=True):
        try:
            cx = sqlite3.connect("file:" + quote(p) + "?mode=ro", uri=True, timeout=10)
            cx.execute("select count(*) from eq_signals").fetchone()
            return cx, p, "read-only"
        except sqlite3.Error as e:
            notes.append("read-only open of %s: %s" % (os.path.basename(p), e))
            try:
                os.makedirs("/tmp/dbcopy", exist_ok=True)
                for ext in ("", "-wal", "-shm", "-journal"):
                    if os.path.exists(p + ext):
                        shutil.copy2(p + ext, "/tmp/dbcopy/" + os.path.basename(p) + ext)
                cx = sqlite3.connect("/tmp/dbcopy/" + os.path.basename(p), timeout=10)
                cx.execute("select count(*) from eq_signals").fetchone()
                return cx, p, "private copy"
            except (sqlite3.Error, OSError) as e2:
                notes.append("copy of %s: %s" % (os.path.basename(p), e2))
    raise SystemExit("no scanner database with an eq_signals table under " + DATA_DIR + "; " + "; ".join(notes))


def rows(cx, sql, args=()):
    cur = cx.execute(sql, args)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def js(x, default=None):
    if x is None:
        return default
    if isinstance(x, (dict, list)):
        return x
    try:
        return json.loads(x)
    except (TypeError, ValueError):
        return default


_candles = {}


def candles(key):
    """Today's 1-minute candles, regular session only. Public endpoint, no token."""
    if not key:
        return None
    if key in _candles:
        return _candles[key]
    df = None
    if OFFLINE:
        p = os.path.join(OFFLINE, key.replace("|", "_") + ".json")
        if os.path.exists(p):
            df = candles_to_df(json.load(open(p))["data"]["candles"])
    else:
        url = UPSTOX + "/v3/historical-candle/intraday/" + quote(key, safe="") + "/minutes/1"
        for attempt in range(4):
            try:
                time.sleep(0.35)
                r = client.get(url)
                if r.status_code == 429:
                    time.sleep(1.5 + attempt)
                    continue
                body = r.json()
                if r.status_code >= 400 or body.get("status") != "success":
                    notes.append("candles %s: HTTP %s" % (key, r.status_code))
                    break
                df = candles_to_df((body.get("data") or {}).get("candles") or [])
                break
            except (httpx.HTTPError, ValueError) as e:
                if attempt == 3:
                    notes.append("candles %s: %s" % (key, type(e).__name__))
                time.sleep(0.5 * (attempt + 1))
    _candles[key] = regular(df, cfg) if df is not None else None
    return _candles[key]


_lots = {}


def lot_sizes(keys):
    """Contract lot sizes from the public instrument file, for the keys not already known."""
    need = sorted({k for k in keys if k and k not in _lots})
    if not need:
        return
    try:
        if OFFLINE:
            raw = open(os.path.join(OFFLINE, "NSE.json.gz"), "rb").read()
        else:
            r = client.get(INSTRUMENTS, timeout=120.0)
            r.raise_for_status()
            raw = r.content
        data = gzip.decompress(raw)
        pat = re.compile(rb'"instrument_key"\s*:\s*"(' + b"|".join(re.escape(k.encode()) for k in need) + rb')"')
        for m in pat.finditer(data):
            a, b = data.rfind(b"{", 0, m.start()), data.find(b"}", m.end())
            try:
                rec = json.loads(data[a:b + 1])
                _lots[m.group(1).decode()] = int(rec.get("lot_size") or 0)
            except (ValueError, TypeError):
                pass
        del data
    except Exception as e:  # noqa: BLE001 - rupee figures are then left out for those trades
        notes.append("instrument file: %s" % type(e).__name__)


def leg_money(kind, entry, exit_, qty, side, pts=None):
    gross = round(((exit_ - entry) if pts is None else pts) * qty, 2)
    costs = C.round_trip(kind, entry, exit_, qty, side, cfg.brokerage_per_order, cfg.brokerage_pct)
    slip = C.slippage(entry, exit_, qty, cfg.slippage_pct if kind == "FUT" else cfg.opt_slippage_pct)
    return {"gross_rs": gross, "costs": costs, "slip_rs": slip, "net_rs": round(gross - costs - slip, 2)}


def price(sig, cut):
    """Paper legs for one signal, the way the live ledger prices them (engine.update_trades)."""
    lv = sig["levels"]
    entry_ts = pd.Timestamp(sig["ts"]) + pd.Timedelta(minutes=1)
    m = candles(sig["fut_key"])
    out = {"entry_ts": entry_ts.isoformat(), "fut": None, "opt": None}
    if m is None or m.empty:
        out["why"] = "no futures candles"
        return out
    m = m[m.index <= cut]
    if m.empty or m.index[-1] < entry_ts:
        out["why"] = "entry candle not complete yet"
        return out
    outs = run_policies(m, sig["side"], lv["stop"], [lv["t1"], lv["t2"], lv["t3"]], entry_ts, trail=True)
    lots = sig["lots"]
    fq = (sig.get("fut_lot") or 0) * lots
    fut = {}
    for p, o in outs.items():
        d = o.to_dict()
        if o.status != "no_data" and fq:
            d.update(leg_money("FUT", o.entry, o.exit, fq, sig["side"], o.points))
        fut[p] = d
    out["fut"], out["fut_qty"] = fut, fq
    om = candles(sig.get("opt_key"))
    if om is not None and not om.empty:
        oq = (sig.get("opt_lot") or 0) * lots
        opt = {}
        for p, o in outs.items():
            leg = option_leg(om[om.index <= cut], o)
            if leg.get("status") not in (None, "no_data") and oq:
                leg.update(leg_money("OPT", leg["entry"], leg["exit"], oq, "LONG"))
            opt[p] = leg
        out["opt"], out["opt_qty"] = opt, oq
    return out


def cycles(sigs):
    """Signals grouped by the scan that logged them (rows written within seconds of each other)."""
    groups, cur, t0 = [], [], None
    for s in sorted(sigs, key=lambda s: (s["logged_at"] or s["ts"], s["id"])):
        t = pd.Timestamp(s["logged_at"] or s["ts"])
        if t0 is None or (t - t0).total_seconds() > 30:
            cur, t0 = [], t
            groups.append(cur)
        cur.append(s)
    return groups


def run_pass(tag):
    global notes
    notes = []
    _candles.clear()
    now = datetime.now(IST)
    day = os.environ.get("DRY_DAY") or now.date().isoformat()
    cut = pd.Timestamp(now).floor("min") - pd.Timedelta(minutes=1)
    cx, path, how = open_db()
    sigs = rows(cx, "select * from eq_signals where day = ? order by id", (day,))
    ids = [s["id"] for s in sigs]
    trades = rows(cx, "select * from eq_trades where signal_id in (%s) order by id" % ",".join("?" * len(ids)), ids) if ids else []
    kv = {r["k"]: js(r["v"]) for r in rows(cx, "select k, v from kv where k in ('eq_score_model', 'eq_min_scores')")}
    recent = rows(cx, "select day, count(*) n, sum(action = 'fired') fired from eq_signals group by day order by day desc limit 6")
    nm = rows(cx, "select count(*) n, min(ts) first, max(ts) last from eq_near_misses where day = ?", (day,))[0]
    cx.close()

    saved_thr = (kv.get("eq_min_scores") or {}).get(MODEL)
    thr = float(saved_thr) if isinstance(saved_thr, (int, float)) else min_score(cfg, MODEL)
    by_sig = {}
    for t in trades:
        t["outcomes"], t["targets"] = js(t["outcomes"], {}), js(t["targets"], [])
        by_sig.setdefault(t["signal_id"], {})[t["instrument"]] = t
    live_models = set()
    for s in sigs:
        s["levels"], s["features"] = js(s["levels"], {}), js(s["features"], {})
        f = s["features"]
        live_models.add(f.get("score_model"))
        stored = (f.get("scores") or {}).get(MODEL)
        fresh, parts = fable_op_score(f, s["side"], cfg) if MODEL == "fable_op" else (stored, (f.get("score_parts") or {}).get(MODEL))
        s["dry_score"], s["dry_parts"], s["stored_score"] = (fresh if fresh is not None else stored), parts, stored
        s["live_score"] = f.get("score")
        legs = by_sig.get(s["id"], {})
        lots = f.get("lots")
        if legs.get("FUT") and lots:
            s["fut_lot"] = legs["FUT"]["qty"] // lots
        if legs.get("OPT") and lots:
            s["opt_lot"] = legs["OPT"]["qty"] // lots
        s["lots"] = lots

    # the live rule (engine.fire), with MODEL's score in place of the live model's
    fired = 0
    for group in cycles(sigs):
        for s in sorted(group, key=lambda s: (-(s["dry_score"] or 0), -(s["rank_rel_vol"] or 0))):
            if s["dry_score"] is None or s["dry_score"] < thr:
                s["dry_action"] = "below_score"
            elif s["lots"] == 0:
                s["dry_action"] = "over_budget"
            elif fired >= cfg.top_n:
                s["dry_action"] = "capped_out"
            else:
                s["dry_action"] = "fired"
                fired += 1
    picks = [s for s in sigs if s["dry_action"] == "fired"]
    lot_sizes([k for s in picks for k, have in ((s["fut_key"], s.get("fut_lot")), (s["opt_key"], s.get("opt_lot"))) if not have])
    for s in picks:
        s["fut_lot"] = s.get("fut_lot") or _lots.get(s["fut_key"]) or 0
        s["opt_lot"] = s.get("opt_lot") or _lots.get(s["opt_key"] or "") or s["fut_lot"]
        if s["lots"] is None and s["fut_lot"]:
            s["lots"] = lots_for(s["side"], s["levels"]["entry_ref"], s["levels"]["stop"], s["fut_lot"], cfg)
        s["dry"] = price(s, cut)

    def hhmm(ts):
        return pd.Timestamp(ts).strftime("%H:%M") if ts else "--:--"

    def money(x):
        return "n/a" if x is None else "{:+,.0f}".format(x)

    say("=== DRY RUN %s | day %s | as of %s IST (candles to %s) | db %s" % (tag, day, now.strftime("%H:%M:%S"), cut.strftime("%H:%M"), how))
    say("rules: setups %s | scan %s-%s | top_n %d | risk budget Rs %s | dry model %s >= %g (%s) | exit T1 at %gR, stop 1R"
        % ("+".join(st.code for st in enabled(cfg)), cfg.scan_start, cfg.scan_end, cfg.top_n, "{:,.0f}".format(cfg.risk_budget_rs),
           MODEL, thr, "saved in the scanner" if saved_thr is not None else "config default", cfg.t1_r))
    say("live scanner today: model(s) %s | kv model %s | kv thresholds %s | signals %d | near-misses %d (%s to %s)"
        % (sorted(str(x) for x in live_models), kv.get("eq_score_model"), kv.get("eq_min_scores"), len(sigs), nm["n"],
           hhmm(nm["first"]), hhmm(nm["last"])))
    say("recent days (signals/fired): " + ", ".join("%s %s/%s" % (r["day"], r["n"], r["fired"] or 0) for r in recent))
    say("--- every signal the live scanner logged today")
    say("time  symbol        setup side  lots  live_score live_action   %s  as_%s   parts" % (MODEL, MODEL))
    for s in sorted(sigs, key=lambda s: (s["ts"], s["id"]))[:160]:
        say("%s %-13s %-5s %-5s %-4s  %-10s %-13s %-8s %-12s %s" % (
            hhmm(s["ts"]), s["symbol"][:13], s["setup"], s["side"], s["lots"], s["live_score"], s["action"],
            s["dry_score"], s["dry_action"], json.dumps(s["dry_parts"], separators=(",", ":")) if s["dry_parts"] else ""))
    diff = [s for s in sigs if s["stored_score"] is not None and s["dry_score"] is not None and abs(s["stored_score"] - s["dry_score"]) > 0.05]
    say("score check: %d of %d signals carry a stored %s score; %d differ from the recomputed one"
        % (sum(s["stored_score"] is not None for s in sigs), len(sigs), MODEL, len(diff)))

    def table(title, items):
        say("--- " + title)
        say("time  symbol        side  qty   entry      stop       T1         T1_status  exit       R      fut_net   opt_symbol               opt_net")
        tot_f = tot_o = 0.0
        n_f = n_o = 0
        for s, fut, opt, qty in items:
            f1, o1 = (fut or {}).get("T1") or {}, (opt or {}).get("T1") or {}
            if f1.get("net_rs") is not None:
                tot_f += f1["net_rs"]
                n_f += 1
            if o1.get("net_rs") is not None:
                tot_o += o1["net_rs"]
                n_o += 1
            say("%s %-13s %-5s %-5s %-10s %-10s %-10s %-10s %-10s %-6s %-9s %-24s %s" % (
                hhmm(s["ts"]), s["symbol"][:13], s["side"], qty or "?", f1.get("entry", "-"), s["levels"].get("stop"),
                s["levels"].get("t1"), f1.get("status", "-"), f1.get("exit", "-"), f1.get("r", "-"),
                money(f1.get("net_rs")), (s.get("opt_symbol") or "-")[:24], money(o1.get("net_rs"))))
        say("total at T1: futures %s over %d trades | options %s over %d trades" % (money(tot_f), n_f, money(tot_o), n_o))
        return {"n": len(items), "fut_net_t1": round(tot_f, 2), "fut_priced": n_f, "opt_net_t1": round(tot_o, 2), "opt_priced": n_o}

    dry_tot = table("DRY RUN: trades %s would have taken as the live model (paper, charges and slippage included)" % MODEL,
                    [(s, s["dry"].get("fut"), s["dry"].get("opt"), s["dry"].get("fut_qty")) for s in picks])
    for s in picks:
        if s["dry"].get("why"):
            say("   %s: %s" % (s["symbol"], s["dry"]["why"]))
    live = [s for s in sigs if s["action"] == "fired"]
    live_tot = table("LIVE PAPER LEDGER today, as the scanner recorded it (model %s)" % "/".join(sorted(str(x) for x in live_models)),
                     [(s, (by_sig.get(s["id"], {}).get("FUT") or {}).get("outcomes"), (by_sig.get(s["id"], {}).get("OPT") or {}).get("outcomes"),
                       (by_sig.get(s["id"], {}).get("FUT") or {}).get("qty")) for s in live])
    both = sorted(set(s["symbol"] for s in picks) & set(s["symbol"] for s in live))
    say("in both: %s | only %s: %s | only live: %s" % (both or "-", MODEL, sorted(set(s["symbol"] for s in picks) - set(both)) or "-",
                                                       sorted(set(s["symbol"] for s in live) - set(both)) or "-"))
    if notes:
        say("notes: " + " | ".join(notes[:12]))
    doc = {"tag": tag, "day": day, "as_of": now.isoformat(timespec="seconds"), "cut": cut.isoformat(), "model": MODEL, "threshold": thr,
           "threshold_source": "kv" if saved_thr is not None else "config", "kv": kv, "live_models": sorted(str(x) for x in live_models),
           "config": {"top_n": cfg.top_n, "risk_budget_rs": cfg.risk_budget_rs, "scan": [cfg.scan_start, cfg.scan_end],
                      "setups": [st.code for st in enabled(cfg)], "min_scores": {m: min_score(cfg, m) for m in MODELS},
                      "slippage_pct": cfg.slippage_pct, "opt_slippage_pct": cfg.opt_slippage_pct},
           "totals": {"dry": dry_tot, "live": live_tot}, "notes": notes,
           "signals": [{"id": s["id"], "ts": s["ts"], "logged_at": s["logged_at"], "symbol": s["symbol"], "setup": s["setup"], "side": s["side"],
                        "lots": s["lots"], "live_action": s["action"], "live_score": s["live_score"], "live_model": s["features"].get("score_model"),
                        "scores": s["features"].get("scores"), "dry_score": s["dry_score"], "dry_parts": s["dry_parts"],
                        "dry_action": s["dry_action"], "fut_symbol": s["fut_symbol"], "opt_symbol": s["opt_symbol"],
                        "levels": {k: s["levels"].get(k) for k in ("entry_ref", "stop", "t1", "t2", "t3", "risk", "chosen")},
                        "snap": {k: s["features"].get(k) for k in ("day_chg", "atr_pct", "pos", "mins_since_extreme", "minutes_since_open",
                                                                    "nifty_chg", "from_open", "beyond_vwap", "rel_vol", "price")},
                        "dry": s.get("dry"),
                        "live_legs": {k: {"qty": v["qty"], "entry": v["entry"], "status": v["status"], "outcomes": v["outcomes"]}
                                      for k, v in by_sig.get(s["id"], {}).items()}} for s in sigs]}
    blob = base64.b64encode(gzip.compress(json.dumps(doc, default=str, separators=(",", ":")).encode())).decode()
    say("===JSON %s" % tag)
    for i in range(0, len(blob), 4000):
        say(blob[i:i + 4000])
    say("===END %s" % tag)


try:
    run_pass("pass-1")
    now = datetime.now(IST)
    h, m = [int(x) for x in FINAL_AT.split(":")]
    wait = (now.replace(hour=h, minute=m, second=30, microsecond=0) - now).total_seconds()
    if 0 < wait < 4 * 3600 and not OFFLINE and not os.environ.get("DRY_DAY"):
        say("waiting %d min for the session close, then a final pass" % (wait // 60))
        time.sleep(wait)
        run_pass("final")
except SystemExit as e:
    say("STOPPED: %s" % e)
except Exception:  # noqa: BLE001
    say("FAILED")
    say(traceback.format_exc()[-1500:])
