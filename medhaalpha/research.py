"""Per-symbol research pipeline: features -> signals -> simulated trades.

A *plan* is a list of RunSpec items. Features for each timeframe combination are built once
per symbol and reused for all entry/exit specs in the plan. Runs in parallel over symbols.
"""
from __future__ import annotations

import multiprocessing as mp
from dataclasses import dataclass, field
from datetime import time

import numpy as np
import pandas as pd

from medhaalpha import features as F
from medhaalpha import signals as S
from medhaalpha.config import ENTRY_END, ENTRY_START, StudyConfig
from medhaalpha.data import loader
from medhaalpha.paths import DATA_DIR
from medhaalpha.simulate import REASONS, ExitSpec, simulate

CACHE = DATA_DIR / "cache"
CACHE.mkdir(exist_ok=True)
CFG = StudyConfig()

INTRADAY_COMBOS = [(3, 15), (3, 60), (5, 15), (5, 60), (15, 60)]


@dataclass(frozen=True)
class RunSpec:
    engine: str  # "intraday" | "positional"
    tf: str  # intraday: "5/15" (signal/confirmation); positional: "60/D" or "D/W"
    entry: S.EntrySpec
    side: int
    exit: ExitSpec = field(default_factory=ExitSpec)
    daily_thr: float = 0.0  # positional: minimum daily score of the prior session
    max_sessions: int = 5
    adaptive: bool = False

    @property
    def key(self) -> tuple:
        return (self.engine, self.tf, self.entry.label if not self.adaptive else f"ADAPT_s{int(self.entry.thr)}",
                self.side, self.exit.label, self.daily_thr)


# ------------------------------------------------------------------ industry-mean prepass
def _ret_ref_series(args):
    sym, tf = args
    if tf == "D":
        d = loader.load_daily(sym)
        r = d["close"] / d["close"].shift(20) - 1.0
        return sym, pd.Series(r.to_numpy(), index=d["date"])
    interval = "minutes3" if tf == 3 else "minutes5"
    b = loader.load_intraday(sym, interval)
    if tf in (15, 60):
        b = loader.resample_intraday(b, tf)
    first = b.groupby("date")["open"].transform("first")
    return sym, pd.Series((b["close"] / first - 1.0).to_numpy(), index=b["datetime"])


def industry_means(tf, symbols: list[str], pool=None) -> pd.DataFrame:
    """Point-in-time industry baskets: per timestamp, the SUM and COUNT of `ret_ref` over the stocks of each
    industry that were in the tradable universe on that date (so a stock's RS can exclude itself and no
    future F&O additions leak into the benchmark). Columns: '<industry>|sum' and '<industry>|n'."""
    import hashlib

    imap = loader.industry_map()
    tag = hashlib.sha1(("v3|" + ",".join(sorted(symbols)) + "|" + repr(sorted(imap.items()))).encode()).hexdigest()[:12]
    path = CACHE / f"indmean_{tf}_{tag}.parquet"
    if path.exists():
        return pd.read_parquet(path)
    args = [(s, tf) for s in symbols]
    res = pool.map(_ret_ref_series, args) if pool else list(map(_ret_ref_series, args))
    wide = pd.DataFrame({s: r for s, r in res})
    member = loader.universe_membership()
    days = wide.index.normalize()
    mem = member.reindex(index=days, columns=wide.columns).fillna(False).to_numpy(bool)
    wide = wide.where(mem)
    groups: dict[str, list[str]] = {}
    for s in wide.columns:
        groups.setdefault(imap.get(s, "Other"), []).append(s)
    cols = {}
    for g, c in groups.items():
        cols[f"{g}|sum"] = wide[c].sum(axis=1, min_count=1)
        cols[f"{g}|n"] = wide[c].notna().sum(axis=1).astype(np.float32)
    cols["ALL|sum"] = wide.sum(axis=1, min_count=1)  # universe equal-weight fallback for peerless stocks
    cols["ALL|n"] = wide.notna().sum(axis=1).astype(np.float32)
    out = pd.DataFrame(cols)
    out.to_parquet(path)
    return out


_IND: dict = {}


def _init_worker(ind: dict):
    _IND.update(ind)


# ------------------------------------------------------------------ frames
def build_daily(sym: str, nifty: pd.DataFrame) -> pd.DataFrame:
    d = F.daily_features(sym, nifty)
    d = F.attach_rs(d, sym, _IND["D"], key="date")
    d["htf_ema20"], d["htf_ema50"], d["htf_close"] = d["ema100"], d["ema250"], d["close"]
    nf = nifty[["date", "ema20", "ema50", "close"]].rename(
        columns={"ema20": "ctx_ema20", "ema50": "ctx_ema50", "close": "ctx_close"})
    d = d.merge(nf, on="date", how="left")
    d["datr_ref"] = d["datr_pct"]
    d["score_long_d"] = F.score(d, +1, CFG.weights, intraday=False)
    d["score_short_d"] = F.score(d, -1, CFG.weights, intraday=False)
    d["regime_d"] = F.regime(d, CFG.regime)
    d["end"] = d["date"] + pd.Timedelta(hours=15, minutes=30)
    return d


def tf_bars(base5: pd.DataFrame, base3: pd.DataFrame | None, tf: int) -> pd.DataFrame:
    if tf == 3:
        return loader.add_end(base3, 3)
    if tf == 5:
        return loader.add_end(base5, 5)
    return loader.resample_intraday(base5, tf)


def build_intraday_frame(sym, base5, base3, tf, conf, daily) -> pd.DataFrame:
    sig = F.core_features(tf_bars(base5, base3, tf), intraday=True)
    htf = F.core_features(tf_bars(base5, base3, conf), intraday=True)
    sig = F.join_htf(sig, htf)
    sig = F.join_daily_context(sig, daily.rename(columns={}))
    sig = F.attach_rs(sig, sym, _IND[tf])
    sig["score_long"] = F.score(sig, +1, CFG.weights, intraday=True)
    sig["score_short"] = F.score(sig, -1, CFG.weights, intraday=True)
    sig["regime"] = F.regime(sig, CFG.regime)
    return sig.sort_values("datetime").reset_index(drop=True)


def build_positional_frame(sym, base5, daily) -> pd.DataFrame:
    sig = F.core_features(loader.resample_intraday(base5, 60), intraday=True)
    sig = F.join_htf(sig, daily)  # completed daily candles only
    sig = F.join_daily_context(sig, daily)
    sig = F.attach_rs(sig, sym, _IND[60])
    sig["score_long"] = F.score(sig, +1, CFG.weights, intraday=True)
    sig["score_short"] = F.score(sig, -1, CFG.weights, intraday=True)
    sig["regime"] = F.regime(sig, CFG.regime)
    return sig.sort_values("datetime").reset_index(drop=True)


# ------------------------------------------------------------------ simulation helpers
def base_arrays(base: pd.DataFrame, step: int, positional: bool) -> dict:
    from medhaalpha.config import CAS_START

    st = base["datetime"].dt.hour * 60 + base["datetime"].dt.minute
    end = st + step
    cas_day = (base["date"] >= pd.Timestamp(CAS_START)).to_numpy()
    if positional:
        # no continuous trading after 15:15 once NSE's closing-auction session is live (from 3 Aug 2026)
        last_entry = np.where(cas_day, 15 * 60 + 15 - step, 15 * 60 + 15)
        ok = (st >= 9 * 60 + 15) & (st.to_numpy() <= last_entry)
    else:
        ok = (st >= ENTRY_START.hour * 60 + ENTRY_START.minute) & (st <= ENTRY_END.hour * 60 + ENTRY_END.minute)
    day = base["date"].factorize()[0].astype(np.int64)
    last = np.r_[day[1:] != day[:-1], True]
    from medhaalpha.config import CAS_START, FLAT_MIN_CAS, FLAT_MIN_PRE_CAS

    flat_min = np.where(base["date"].to_numpy() >= np.datetime64(CAS_START), FLAT_MIN_CAS, FLAT_MIN_PRE_CAS)
    flat = (end.to_numpy() >= flat_min) | last  # first bar ending at/after the flat time (or day's last bar)
    o = base["open"].to_numpy(np.float64).copy()
    h = base["high"].to_numpy(np.float64).copy()
    l = base["low"].to_numpy(np.float64).copy()
    c = base["close"].to_numpy(np.float64)
    # Closing-auction days: bars from 15:15 are not continuous trading (flat, zero-volume bars and a final
    # bar whose close is the auction print). Treat each as a single print at its close so stops, trails and
    # targets crossing there fill at the auction price, never at a price that did not trade.
    auction = cas_day & (st.to_numpy() >= 15 * 60 + 15)
    o[auction] = c[auction]
    h[auction] = c[auction]
    l[auction] = c[auction]
    return {
        "bo": o, "bh": h, "bl": l, "bc": c,
        "bday": day, "entry_ok": np.asarray(ok), "flat_bar": flat, "last_bar": last,
        "start": base["datetime"].to_numpy(), "end": (base["datetime"] + pd.to_timedelta(step, "m")).to_numpy(),
    }


def tf_completion(ba: dict, frame: pd.DataFrame) -> tuple:
    nb = len(ba["bo"])
    pos = np.searchsorted(ba["end"], frame["end"].to_numpy())
    good = (pos < nb)
    good[good] = ba["end"][pos[good]] == frame["end"].to_numpy()[good]
    arrs = []
    for col in ("close", "ema20", "ema50", "atr"):
        a = np.full(nb, np.nan)
        a[pos[good]] = frame[col].to_numpy()[good]
        arrs.append(a)
    return tuple(arrs)


def run_sim(ba: dict, tfc: tuple, cands: pd.DataFrame, ex: ExitSpec, intraday: bool, valid_n: int,
            max_sessions: int) -> pd.DataFrame:
    if cands.empty:
        return pd.DataFrame()
    act = np.searchsorted(ba["start"], cands["end"].to_numpy(), side="left").astype(np.int64)
    n = len(cands)
    res = simulate(
        ba["bo"], ba["bh"], ba["bl"], ba["bc"], ba["bday"], ba["entry_ok"], ba["flat_bar"], ba["last_bar"],
        tfc[0], tfc[1], tfc[2], tfc[3],
        act, cands["side"].to_numpy(np.int64), cands["entry_type"].to_numpy(np.int64),
        np.nan_to_num(cands["level"].to_numpy(np.float64), nan=0.0), np.full(n, valid_n, np.int64),
        cands["stop_struct"].to_numpy(np.float64), cands["atr"].to_numpy(np.float64),
        np.full(n, intraday, np.bool_), max_sessions,
        ex.stop_mode, ex.stop_k, ex.target_r, ex.trail_k, ex.ema_mode, ex.partial_r, ex.partial_frac,
        ex.min_stop_atr, ex.max_stop_atr,
    )
    fill_i, fill, stop, exit_i, exit_px, reason, nexit, mfe, mae = res
    t = cands.copy()
    t["fill_i"], t["fill"], t["stop"], t["exit_i"], t["exit"] = fill_i, fill, stop, exit_i, exit_px
    t["reason"], t["n_exit"], t["mfe"], t["mae"] = reason, nexit, mfe, mae
    # drop unfilled orders and trades still open when the data ends (not completed trades)
    t = t[(t["fill_i"] >= 0) & (t["reason"] != 6)].copy()
    if t.empty:
        return t
    t["fill_time"] = ba["start"][t["fill_i"].to_numpy()]
    t["exit_time"] = ba["end"][t["exit_i"].to_numpy()]
    t["sessions"] = ba["bday"][t["exit_i"].to_numpy()] - ba["bday"][t["fill_i"].to_numpy()] + 1
    t["risk_ps"] = (t["fill"] - t["stop"]).abs()
    t["R"] = t["side"] * (t["exit"] - t["fill"]) / t["risk_ps"]
    t["reason"] = t["reason"].map(REASONS)
    return t.drop(columns=["fill_i", "exit_i", "sig_i", "level", "stop_struct"])


# ------------------------------------------------------------------ per-symbol job
def symbol_job(args) -> pd.DataFrame:
    sym, plan, nifty, member = args
    imap = loader.industry_map()
    out = []
    try:
        base5 = loader.load_intraday(sym, "minutes5")
    except FileNotFoundError:
        return pd.DataFrame()
    need3 = any(r.engine == "intraday" and r.tf.startswith("3/") for r in plan)
    base3 = None
    if need3:
        try:
            base3 = loader.load_intraday(sym, "minutes3")
        except FileNotFoundError:
            plan = [r for r in plan if not r.tf.startswith("3/")]
    daily = build_daily(sym, nifty)
    tradable = member.get(sym)
    if tradable is None:
        return pd.DataFrame()
    by_tf: dict[str, list[RunSpec]] = {}
    for r in plan:
        by_tf.setdefault((r.engine, r.tf), []).append(r)
    ba5_i = base_arrays(base5, 5, positional=False)
    ba5_p = base_arrays(base5, 5, positional=True)
    for (engine, tf), runs in by_tf.items():
        if engine == "intraday":
            stf, ctf = (int(x) for x in tf.split("/"))
            frame = build_intraday_frame(sym, base5, base3, stf, ctf, daily)
            ba = base_arrays(base3, 3, False) if stf == 3 else ba5_i
            step = 3 if stf == 3 else 5
            tod = frame["end"].dt.hour * 60 + frame["end"].dt.minute
            allowed = (
                frame["date"].map(tradable).fillna(False).to_numpy(bool)
                & (tod >= ENTRY_START.hour * 60 + ENTRY_START.minute).to_numpy()
                & (tod <= ENTRY_END.hour * 60 + ENTRY_END.minute).to_numpy()
            )
            valid_mult = max(1, stf // step)
        elif tf == "60/D":
            frame = build_positional_frame(sym, base5, daily)
            ba = ba5_p
            tod = frame["end"].dt.hour * 60 + frame["end"].dt.minute
            allowed = frame["date"].map(tradable).fillna(False).to_numpy(bool) & (tod >= 615).to_numpy() & (
                tod <= 915).to_numpy()
            valid_mult = 12
        else:  # "D/W": daily signals, entry next session
            frame = daily.copy()
            ba = ba5_p
            nxt = frame["date"].shift(-1)
            allowed = nxt.map(tradable).fillna(False).to_numpy(bool)
            frame["score_long"], frame["score_short"] = frame["score_long_d"], frame["score_short_d"]
            frame["regime"] = frame["regime_d"]
            frame["day_id"] = np.arange(len(frame))
            valid_mult = 75
        tfc = tf_completion(ba, frame)
        cache: dict = {}
        for r in runs:
            mask = allowed
            if engine == "positional" and tf == "60/D":
                sc = frame["score_long_d" if r.side > 0 else "score_short_d"].to_numpy()
                trend = (r.side * (frame["ctx_ema20"] - frame["ctx_ema50"]) > 0).to_numpy()
                mask = allowed & trend & (np.nan_to_num(sc, nan=-1) >= r.daily_thr)
            ckey = (r.entry, r.side, r.adaptive, r.daily_thr)
            if ckey not in cache:
                if r.adaptive:
                    cache[ckey] = S.adaptive(frame, r.side, mask, thr=r.entry.thr, n=r.entry.n)
                else:
                    cache[ckey] = S.generate(frame, r.entry, r.side, mask)
            cands = cache[ckey]
            t = run_sim(ba, tfc, cands, r.exit, engine == "intraday", r.entry.valid_bars * valid_mult,
                        r.max_sessions)
            if t.empty:
                continue
            t["symbol"] = sym
            t["industry"] = imap.get(sym, "Other")
            t["engine"], t["tf"], t["entry"], t["exit_spec"], t["daily_thr"] = engine, tf, r.key[2], r.exit.label, r.daily_thr
            out.append(t)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


COMPACT_COLS = [
    "symbol", "industry", "engine", "tf", "entry", "side", "exit_spec", "daily_thr", "model", "date", "end", "fill_time",
    "exit_time", "fill", "stop", "exit", "risk_ps", "R", "reason", "n_exit", "sessions", "score", "rvol", "adx", "regime",
    "ext", "datr_pct", "mfe", "mae", "qty", "notional", "planned_risk", "pnl_net", "R_net", "cost_R",
    "qty_m", "pnl_net_m", "R_net_m", "cost_R_m",
]


def compact_job(args) -> pd.DataFrame:
    """symbol_job + study-window filter + per-symbol non-overlap + standalone sizing (both cap readings)."""
    from medhaalpha.config import STUDY_START
    from medhaalpha.metrics import non_overlapping, standalone_net

    t = symbol_job(args)
    if t.empty:
        return t
    t = t[t["fill_time"] >= STUDY_START]
    t = non_overlapping(t)
    if t.empty:
        return t
    a = standalone_net(t, cap_is_margin=False, keep_zero=True)
    b = standalone_net(t, cap_is_margin=True, keep_zero=True)
    a = a.join(b[["qty", "pnl_net", "R_net", "cost_R"]].rename(columns=lambda c: c + "_m"), how="left")
    a = a[(a["qty"] > 0) | (a["qty_m"] > 0)]
    a = a[[c for c in COMPACT_COLS if c in a.columns]]
    for c in a.columns:
        if a[c].dtype == np.float64 and c not in ("fill", "stop", "exit", "risk_ps"):
            a[c] = a[c].astype(np.float32)
    for c in ("symbol", "industry", "engine", "tf", "entry", "exit_spec", "model", "reason"):
        if c in a.columns:
            a[c] = a[c].astype("category")
    return a


def run_plan(plan: list[RunSpec], symbols: list[str] | None = None, workers: int = 4, compact: bool = False) -> pd.DataFrame:
    symbols = symbols or loader.canonical_symbols()
    member = loader.universe_membership()
    member_d = {s: member[s] for s in member.columns}
    nifty = F.nifty_daily()
    tfs = {3, 5, 15, 60, "D"}
    if not any(r.tf.startswith("3/") for r in plan):
        tfs.discard(3)
    ctx = mp.get_context("fork")
    with ctx.Pool(workers) as pool:
        ind = {tf: industry_means(tf, symbols, pool) for tf in tfs}
    with ctx.Pool(workers, initializer=_init_worker, initargs=(ind,)) as pool:
        fn = compact_job if compact else symbol_job
        parts = pool.map(fn, [(s, plan, nifty, member_d) for s in symbols], chunksize=1)
    parts = [p for p in parts if p is not None and not p.empty]
    if not parts:
        return pd.DataFrame()
    out = pd.concat(parts, ignore_index=True)
    if compact:
        for c in ("symbol", "industry", "engine", "tf", "entry", "exit_spec", "model", "reason"):
            if c in out.columns:
                out[c] = out[c].astype("category")
    return out
