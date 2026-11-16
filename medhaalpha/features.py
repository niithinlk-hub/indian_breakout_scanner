"""Feature construction: per-timeframe indicators, leak-free higher-timeframe joins,
sector-relative strength, the 100-point trend score and the regime classifier.

Every feature on a bar is known at that bar's *end* time. Higher-timeframe values are
joined with ``merge_asof(..., on=end)`` so only completed HTF bars are visible.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from medhaalpha import indicators as ind
from medhaalpha.config import RegimeConfig, ScoreWeights
from medhaalpha.data import loader

F32 = np.float32


def _clip01(x):
    return np.clip(np.nan_to_num(x, nan=0.0), 0.0, 1.0)


def core_features(bars: pd.DataFrame, intraday: bool) -> pd.DataFrame:
    df = bars.copy()
    o, h, l, c, v = (df[k].to_numpy(np.float64) for k in ("open", "high", "low", "close", "volume"))
    day_id = df["date"].factorize()[0].astype(np.int64)
    df["ema20"] = ind.ema(c, 20)
    df["ema50"] = ind.ema(c, 50)
    df["atr"] = ind.atr(h, l, c, 14)
    a, pdi, ndi = ind.adx(h, l, c, 14)
    df["adx"], df["pdi"], df["ndi"] = a, pdi, ndi
    if intraday:
        df["vwap"] = ind.session_vwap(h, l, c, v, day_id)
        slot = df.groupby(day_id).cumcount().to_numpy(np.int64)
        df["rvol"] = ind.slot_rvol(v, day_id, slot, int(slot.max()) + 1, 20)
        first_open = df.groupby(day_id)["open"].transform("first").to_numpy()
        df["ret_ref"] = c / first_open - 1.0
    else:
        tp = (h + l + c) / 3.0
        pv = pd.Series(tp * v).rolling(20, min_periods=10).sum()
        vv = pd.Series(v).rolling(20, min_periods=10).sum()
        df["vwap"] = (pv / vv).to_numpy()
        df["rvol"] = v / pd.Series(v).shift(1).rolling(20, min_periods=10).mean().to_numpy()
        df["ret_ref"] = c / pd.Series(c).shift(20).to_numpy() - 1.0
        df["ema100"] = ind.ema(c, 100)
        df["ema250"] = ind.ema(c, 250)
    atr_ = df["atr"].to_numpy()
    e20, e50 = df["ema20"].to_numpy(), df["ema50"].to_numpy()
    df["sep"] = (e20 - e50) / atr_
    df["slope50"] = (e50 - np.roll(e50, 5)) / atr_
    df.loc[df.index[:5], "slope50"] = np.nan
    df["slope20"] = (e20 - np.roll(e20, 3)) / atr_
    lmin = ind.rolling_min(l, 6)
    hmax = ind.rolling_max(h, 6)
    df["hl_up"] = lmin > np.roll(lmin, 6)
    df["lh_dn"] = hmax < np.roll(hmax, 6)
    df["low5"] = ind.rolling_min(l, 5)
    df["high5"] = ind.rolling_max(h, 5)
    df["day_id"] = day_id
    return df


def daily_features(symbol: str, nifty: pd.DataFrame | None = None) -> pd.DataFrame:
    d = core_features(loader.load_daily(symbol), intraday=False)
    d["datr_pct"] = d["atr"] / d["close"]
    if nifty is not None:
        d = d.merge(nifty[["date", "n_trend"]], on="date", how="left")
    else:
        d["n_trend"] = 0
    return d


def nifty_daily() -> pd.DataFrame:
    n = core_features(loader.load_daily("NIFTY50"), intraday=False)
    n["n_trend"] = np.where(n["ema20"] > n["ema50"], 1, -1)
    n["n_ret20"] = n["ret_ref"]
    return n


def market_regime_table() -> pd.DataFrame:
    """NIFTY 50 daily regime (bull / bear / sideways) used for reporting breakdowns."""
    n = nifty_daily()
    bull = (n["ema20"] > n["ema50"]) & (n["close"] > n["ema50"]) & (n["adx"] >= 18)
    bear = (n["ema20"] < n["ema50"]) & (n["close"] < n["ema50"]) & (n["adx"] >= 18)
    n["market_regime"] = np.select([bull, bear], ["bullish", "bearish"], "sideways")
    # regime known at the close of D applies to trading on D+1
    n["market_regime"] = n["market_regime"].shift(1)
    return n[["date", "market_regime"]]


def score(df: pd.DataFrame, side: int, w: ScoreWeights, intraday: bool) -> np.ndarray:
    """100-point directional trend score (side=+1 long, -1 short)."""
    s = float(side)
    aligned = (s * (df["ema20"] - df["ema50"]) > 0).to_numpy(float)
    sep = s * df["sep"].to_numpy()
    slope = s * df["slope50"].to_numpy()
    ema_pts = w.ema * (0.40 * aligned + 0.32 * aligned * _clip01(sep / 1.0) + 0.28 * aligned * _clip01(slope / 0.3))

    htf_al = (s * (df["htf_ema20"] - df["htf_ema50"]) > 0).to_numpy(float)
    htf_cl = (s * (df["htf_close"] - df["htf_ema20"]) > 0).to_numpy(float)
    ctx_al = (s * (df["ctx_ema20"] - df["ctx_ema50"]) > 0).to_numpy(float)
    ctx_cl = (s * (df["ctx_close"] - df["ctx_ema20"]) > 0).to_numpy(float)
    htf_pts = w.htf * (0.40 * htf_al + 0.20 * htf_cl + 0.20 * ctx_al + 0.20 * ctx_cl)

    di_ok = (s * (df["pdi"] - df["ndi"]) > 0).to_numpy(float)
    adx_pts = w.adx * di_ok * _clip01((df["adx"].to_numpy() - 15.0) / 20.0)

    above_vwap = (s * (df["close"] - df["vwap"]) > 0).to_numpy(float)
    struct = (df["hl_up"] if side > 0 else df["lh_dn"]).to_numpy(float)
    vw_pts = w.vwap_structure * (0.55 * above_vwap + 0.45 * struct)

    rv_pts = w.rvol * _clip01((df["rvol"].to_numpy() - 0.8) / 1.0)

    scale = df["datr_ref"].to_numpy() * (0.25 if intraday else 1.0)
    rs_pts = w.sector_rs * _clip01(s * df["rs"].to_numpy() / scale)
    total = ema_pts + htf_pts + adx_pts + vw_pts + rv_pts + rs_pts
    total[np.isnan(df["ema50"].to_numpy()) | np.isnan(df["adx"].to_numpy())] = np.nan
    return total


def regime(df: pd.DataFrame, cfg: RegimeConfig) -> np.ndarray:
    a = df["adx"].to_numpy()
    sep = np.abs(df["sep"].to_numpy())
    trend = (a > cfg.adx_trend) & (sep > cfg.sep_trend)
    side = (a < cfg.adx_sideways) & (sep < cfg.sep_sideways)
    return np.where(trend, 2, np.where(side, 0, 1)).astype(np.int8)


# ------------------------------------------------------------------ sector relative strength
def attach_rs(df: pd.DataFrame, symbol: str, ind_means: pd.DataFrame, key: str = "datetime") -> pd.DataFrame:
    """Sector-relative strength: own return minus the equal-weight return of the *other* universe members
    of the same industry at the same timestamp (point-in-time basket, self excluded). Stocks without an
    industry peer that day fall back to the whole universe basket."""
    g = loader.industry_map().get(symbol, "Other")
    own = df["ret_ref"].to_numpy()
    member = loader.universe_membership()
    mem = (member[symbol].reindex(pd.DatetimeIndex(df[key]).normalize()).fillna(False).to_numpy(bool)
           if symbol in member.columns else np.zeros(len(df), bool))
    self_in = mem & ~np.isnan(own)

    def peers(prefix):
        if f"{prefix}|sum" not in ind_means.columns:
            return np.full(len(df), np.nan)
        tot = ind_means[f"{prefix}|sum"].reindex(df[key]).to_numpy()
        cnt = ind_means[f"{prefix}|n"].reindex(df[key]).to_numpy()
        ps = np.where(self_in, tot - np.nan_to_num(own), tot)
        pn = np.where(self_in, cnt - 1, cnt)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(pn >= 1, ps / pn, np.nan)

    peer = peers(g) if g != "Other" else np.full(len(df), np.nan)
    peer = np.where(np.isnan(peer), peers("ALL"), peer)
    df["rs"] = own - peer
    return df


# ------------------------------------------------------------------ assembling a signal frame
def join_htf(sig: pd.DataFrame, htf: pd.DataFrame, prefix: str = "htf") -> pd.DataFrame:
    right = htf[["end", "ema20", "ema50", "close"]].rename(
        columns={"ema20": f"{prefix}_ema20", "ema50": f"{prefix}_ema50", "close": f"{prefix}_close", "end": "_hend"}
    )
    out = pd.merge_asof(
        sig.sort_values("end"), right.sort_values("_hend"), left_on="end", right_on="_hend", direction="backward"
    )
    return out.drop(columns=["_hend"])


def join_daily_context(sig: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    """Attach the *previous completed* daily candle's values to each intraday bar."""
    d = daily[["date", "ema20", "ema50", "close", "datr_pct", "score_long_d", "score_short_d", "regime_d"]].copy()
    d = d.rename(columns={"ema20": "ctx_ema20", "ema50": "ctx_ema50", "close": "ctx_close", "datr_pct": "datr_ref"})
    d["date"] = d["date"].shift(-1)  # row for D-1 becomes available on D
    d = d.dropna(subset=["date"])
    return sig.merge(d, on="date", how="left")
