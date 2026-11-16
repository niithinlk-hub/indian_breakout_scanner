"""Entry models A0/A/B/C (+ regime-adaptive selection) evaluated on completed bars.

A signal on bar t (known at ``end[t]``) produces an order that becomes active on the first
bar starting at/after ``end[t]``. Market entries fill at that bar's open; pullback entries
use a stop order at the confirmation candle's high (low for shorts) valid for a few bars.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TICK = 0.05


@dataclass(frozen=True)
class EntrySpec:
    model: str  # A0 | A | B | C | ADAPT
    thr: float = 0.0  # minimum trend score (0 = no score filter)
    n: int = 10  # breakout window (C)
    rvol_min: float = 1.5  # C
    ext_max: float = 3.0  # C: max (close-EMA20)/ATR (daily breakouts sit ~2.5 ATR above EMA20 at the median)
    touch: float = 0.2  # B: pullback must come within touch*ATR of EMA20
    valid_bars: int = 3  # B: stop order validity in signal-TF bars
    p: float = 0.0  # RAND: probability of a random entry on any allowed bar (control benchmark)

    @property
    def label(self) -> str:
        if self.model == "A0":
            return "A0"
        if self.model == "RAND":
            return "RAND"
        if self.model == "C":
            return f"C{self.n}_s{int(self.thr)}"
        return f"{self.model}_s{int(self.thr)}"


def _shift(x: np.ndarray, k: int) -> np.ndarray:
    out = np.roll(x, k)
    if k > 0:
        out[:k] = np.nan
    return out


def generate(df: pd.DataFrame, spec: EntrySpec, side: int, allowed: np.ndarray) -> pd.DataFrame:
    """Return candidate entries for one side. `allowed` = bool mask (tradable day & time window)."""
    s = float(side)
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    e20, e50, atr = df["ema20"].to_numpy(), df["ema50"].to_numpy(), df["atr"].to_numpy()
    sc = df["score_long" if side > 0 else "score_short"].to_numpy()
    sc = np.nan_to_num(sc, nan=-1.0)
    slope50 = np.nan_to_num(df["slope50"].to_numpy(), nan=0.0)
    d = s * (e20 - e50)
    d_prev = _shift(d, 1)
    cross = (d > 0) & (d_prev <= 0)

    entry_type = np.zeros(len(df), dtype=np.int8)  # 0 market next open, 1 stop order
    level = np.full(len(df), np.nan)
    if side > 0:
        stop_struct = df["low5"].to_numpy() - 0.1 * atr
    else:
        stop_struct = df["high5"].to_numpy() + 0.1 * atr

    if spec.model == "A0":
        sig = cross
    elif spec.model == "A":
        improving = s * slope50 > s * np.nan_to_num(_shift(slope50, 3), nan=0.0)
        sig = cross & improving & (sc >= spec.thr)
    elif spec.model == "B":
        trend = (d > 0) & (s * slope50 > 0) & (sc >= spec.thr)
        if side > 0:
            touch = np.zeros(len(df), bool)
            hold = np.ones(len(df), bool)
            for k in (1, 2, 3):
                lk, e20k, e50k, atrk = _shift(l, k), _shift(e20, k), _shift(e50, k), _shift(atr, k)
                touch |= lk <= e20k + spec.touch * atrk
                hold &= lk > e50k - 0.25 * atrk
            confirm = (c > o) & (c > e20) & (c > _shift(c, 1))
            lvl = h + TICK
            stop_struct = np.minimum(df["low5"].to_numpy(), l) - 0.1 * atr
        else:
            touch = np.zeros(len(df), bool)
            hold = np.ones(len(df), bool)
            for k in (1, 2, 3):
                hk, e20k, e50k, atrk = _shift(h, k), _shift(e20, k), _shift(e50, k), _shift(atr, k)
                touch |= hk >= e20k - spec.touch * atrk
                hold &= hk < e50k + 0.25 * atrk
            confirm = (c < o) & (c < e20) & (c < _shift(c, 1))
            lvl = l - TICK
            stop_struct = np.maximum(df["high5"].to_numpy(), h) + 0.1 * atr
        sig = trend & touch & hold & confirm
        entry_type[:] = 1
        level = lvl
    elif spec.model == "C":
        bias = (d > 0) & (s * slope50 >= 0) & (sc >= spec.thr)
        if side > 0:
            prior = pd.Series(h).shift(1).rolling(spec.n).max().to_numpy()
            brk = c > prior
            ext = (c - e20) / atr
        else:
            prior = pd.Series(l).shift(1).rolling(spec.n).min().to_numpy()
            brk = c < prior
            ext = (e20 - c) / atr
        rv = np.nan_to_num(df["rvol"].to_numpy(), nan=0.0)
        sig = bias & brk & (rv >= spec.rvol_min) & (ext <= spec.ext_max)
    elif spec.model == "RAND":
        # control: random entries (same windows, same stops/exits); deterministic per symbol/frame/side
        seed = (int(abs(np.nansum(c[:50])) * 100) + len(df) * 7 + (1 if side > 0 else 2)) % (2**32)
        sig = np.random.default_rng(seed).random(len(df)) < spec.p
    else:
        raise ValueError(spec.model)

    sig = sig & allowed & ~np.isnan(atr) & ~np.isnan(e50) & (atr > 0)
    idx = np.flatnonzero(sig)
    out = pd.DataFrame(
        {
            "sig_i": idx,
            "end": df["end"].to_numpy()[idx],
            "date": df["date"].to_numpy()[idx],
            "side": np.int8(side),
            "entry_type": entry_type[idx],
            "level": level[idx],
            "stop_struct": stop_struct[idx],
            "atr": atr[idx],
            "score": sc[idx],
            "rvol": df["rvol"].to_numpy()[idx],
            "adx": df["adx"].to_numpy()[idx],
            "regime": df["regime"].to_numpy()[idx],
            "close": c[idx],
            "ext": (s * (c - e20) / atr)[idx],
            "datr_pct": (df["datr_ref"].to_numpy()[idx] if "datr_ref" in df else np.full(len(idx), np.nan)),
        }
    )
    out["model"] = spec.model
    out["entry"] = spec.label
    return out


def adaptive(df: pd.DataFrame, side: int, allowed: np.ndarray, thr: float = 60.0, n: int = 15) -> pd.DataFrame:
    """Regime-based model selection (all inputs known at the signal bar):

    * trending regime (strong ADX + wide EMA separation)       -> pullback continuation (B)
    * transition regime after a recent sideways/compressed spell -> breakout (C)
    * transition regime otherwise (newly developing trend)       -> crossover (A)
    * sideways regime                                            -> no trade
    """
    reg = df["regime"].to_numpy()
    sideways_recent = pd.Series(reg == 0).rolling(12, min_periods=6).mean().shift(1).fillna(0).to_numpy() >= 0.5
    parts = []
    b = generate(df, EntrySpec("B", thr=thr), side, allowed & (reg == 2))
    parts.append(b)
    cmask = allowed & (reg == 1) & sideways_recent  # masks are disjoint: B trending, C after sideways, A otherwise
    parts.append(generate(df, EntrySpec("C", thr=thr, n=n), side, cmask))
    amask = allowed & (reg == 1) & ~sideways_recent
    parts.append(generate(df, EntrySpec("A", thr=thr), side, amask))
    out = pd.concat(parts, ignore_index=True).sort_values(["sig_i", "model"]).drop_duplicates("sig_i")
    out["entry"] = f"ADAPT_s{int(thr)}"
    return out.reset_index(drop=True)
