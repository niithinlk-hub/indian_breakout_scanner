"""Trade plan (section 4): one implementation for live plans, paper trades and backtests.

Conventions (all thresholds from config, per segment where applicable):

* Signal on bar t (close of T). Entry at the open of bar t+1, the symbol's next bar.
  Fill = open x (1 + slippage). Costs: half of `costs.round_trip` on each side.
* Skips: stop >= signal close, or stop more than `plan.max_stop_pct` below the signal
  close (checked again against the fill); open at or below the stop.
* Sessions are counted from the entry bar (session 1). Within a bar, events are
  resolved in the order they can happen, and where the order is unknowable the worse
  outcome is assumed:
    1. exit decided at the previous close -> sell everything at this open;
    2. open <= stop -> sell everything at the open (gap through the stop);
       open >= partial target -> partial fill at the open;
    3. low <= stop -> sell everything at the stop (assumed to happen BEFORE a target
       touch on the same bar);
       high >= partial target -> partial fill at the target (resting limit order);
    4. high >= +`plan.breakeven_at` -> stop moves to the entry fill from the NEXT bar;
    5. at the close: session `plan.time_exit_sessions` -> sell the rest at the close;
       otherwise decide an exit for the next open, first match wins:
         close < pivot within `plan.failed_breakout_sessions` (only when a pivot exists)
         -> FAILED_BREAKOUT; after the partial, close < EMA(`plan.trail_ema`) -> TRAIL_EMA;
         before the partial, at session `plan.stall_sessions`, close < fill x (1 +
         `plan.stall_min_gain`) -> STALL (if `plan.stall_enabled`).
* Triple-barrier label, independent of the exits: upper = fill x (1 + `labels.upper`),
  lower = initial stop, vertical = `labels.vertical_sessions`; same-bar ties count as
  the lower barrier. +1 upper first, -1 lower first, 0 neither.
* A trade that has not finished when the data ends is OPEN (right-censored) and is
  excluded from metrics.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple, Sequence

import numpy as np

from .config import Config

NAN = float("nan")


@dataclass(frozen=True)
class PlanParams:
    max_stop_pct: float
    failed_breakout_sessions: int
    breakeven_at: float
    partial_at: float
    partial_frac: float
    stall_enabled: bool
    stall_sessions: int
    stall_min_gain: float
    time_exit_sessions: int
    cost_side: float
    slip_side: float
    label_upper: float
    label_vertical: int

    @classmethod
    def from_config(cls, cfg: Config, segment: str) -> "PlanParams":
        return cls(
            max_stop_pct=float(cfg["plan.max_stop_pct"]),
            failed_breakout_sessions=int(cfg["plan.failed_breakout_sessions"]),
            breakeven_at=float(cfg["plan.breakeven_at"]),
            partial_at=float(cfg["plan.partial_at"]),
            partial_frac=float(cfg["plan.partial_frac"]),
            stall_enabled=bool(cfg["plan.stall_enabled"]),
            stall_sessions=int(cfg["plan.stall_sessions"]),
            stall_min_gain=float(cfg["plan.stall_min_gain"]),
            time_exit_sessions=int(cfg["plan.time_exit_sessions"]),
            cost_side=float(cfg["costs.round_trip"]) / 2.0,
            slip_side=float(cfg.seg("costs.slippage_per_side", segment)),
            label_upper=float(cfg["labels.upper"]),
            label_vertical=int(cfg["labels.vertical_sessions"]),
        )


class Trade(NamedTuple):
    status: str  # CLOSED | SKIPPED | OPEN
    skip_reason: str
    signal_idx: int
    stop: float
    stop_pct_signal: float
    entry_idx: int
    entry_raw: float
    entry_fill: float
    stop_pct_entry: float
    exit_idx: int
    exit_reason: str
    partial_idx: int
    sessions: int
    ret_gross: float
    ret_net: float
    r_net: float
    mfe_pct: float
    mae_pct: float
    label: float  # +1 / -1 / 0; NaN if censored
    label_sessions: int
    label_ret: float  # return at the vertical barrier when label == 0
    touched_upper: float  # 1.0 if high reached the upper barrier within the vertical window
    spans_big_move: bool


def _skipped(t: int, stop: float, stop_pct: float, reason: str, entry_idx: int = -1, entry_raw: float = NAN) -> Trade:
    return Trade("SKIPPED", reason, t, stop, stop_pct, entry_idx, entry_raw, NAN, NAN, -1, "", -1, 0,
                 NAN, NAN, NAN, NAN, NAN, NAN, 0, NAN, NAN, False)


def triple_barrier(o: Sequence[float], h: Sequence[float], l: Sequence[float], c: Sequence[float], t: int,
                   entry_fill: float, stop: float, upper_pct: float, vertical: int) -> tuple[float, int, float, float]:
    """(label, sessions to touch, vertical return, touched_upper) from entry bar t+1."""

    n = len(c)
    upper = entry_fill * (1.0 + upper_pct)
    label, label_sessions, label_ret = NAN, 0, NAN
    for s in range(1, vertical + 1):
        i = t + s
        if i >= n:
            break
        if o[i] >= upper:
            label, label_sessions = 1.0, s
            break
        if o[i] <= stop or l[i] <= stop:
            label, label_sessions = -1.0, s
            break
        if h[i] >= upper:
            label, label_sessions = 1.0, s
            break
        if s == vertical:
            label, label_sessions, label_ret = 0.0, s, c[i] / entry_fill - 1.0
    last = min(t + vertical, n - 1)
    touched = NAN
    if t + 1 <= last:
        window_high = max(h[t + 1 : last + 1])
        if window_high >= upper:
            touched = 1.0
        elif t + vertical < n:
            touched = 0.0
    return label, label_sessions, label_ret, touched


def simulate_trade(
    o: Sequence[float],
    h: Sequence[float],
    l: Sequence[float],
    c: Sequence[float],
    trail: Sequence[float],
    big_move: Sequence[bool],
    t: int,
    stop: float,
    pivot: float | None,
    p: PlanParams,
) -> Trade:
    """Simulate one long trade signalled on bar t (arrays are one symbol's own bars)."""

    n = len(c)
    close_t = c[t]
    stop_pct_signal = (close_t - stop) / close_t if close_t > 0 else NAN
    if not stop < close_t:
        return _skipped(t, stop, stop_pct_signal, "stop_not_below_close")
    if stop_pct_signal > p.max_stop_pct:
        return _skipped(t, stop, stop_pct_signal, "stop_too_wide")
    e = t + 1
    if e >= n:
        return _skipped(t, stop, stop_pct_signal, "no_entry_bar_yet")
    entry_raw = o[e]
    if entry_raw <= stop:
        return _skipped(t, stop, stop_pct_signal, "open_at_or_below_stop", e, entry_raw)
    entry_fill = entry_raw * (1.0 + p.slip_side)
    stop_pct_entry = (entry_fill - stop) / entry_fill
    if stop_pct_entry > p.max_stop_pct:
        return _skipped(t, stop, stop_pct_signal, "stop_too_wide_at_entry", e, entry_raw)

    risk = entry_fill - stop
    target = entry_fill * (1.0 + p.partial_at)
    breakeven_trigger = entry_fill * (1.0 + p.breakeven_at)
    stall_level = entry_fill * (1.0 + p.stall_min_gain)
    stop_level = next_stop = stop
    remaining = 1.0
    partial_idx = -1
    pending = ""
    legs: list[tuple[float, float]] = []  # (raw price, fraction)
    max_px, min_px = entry_raw, entry_raw
    exit_idx, exit_reason, sessions = -1, "", 0

    for s in range(1, p.time_exit_sessions + 1):
        i = t + s
        if i >= n:
            break
        sessions = s
        stop_level = next_stop
        stop_reason = "BREAKEVEN_STOP" if stop_level > stop else "STOP"
        if pending:
            legs.append((o[i], remaining))
            max_px, min_px = max(max_px, o[i]), min(min_px, o[i])
            exit_idx, exit_reason, remaining = i, pending, 0.0
            break
        if o[i] <= stop_level:
            legs.append((o[i], remaining))
            max_px, min_px = max(max_px, o[i]), min(min_px, o[i])
            exit_idx, exit_reason, remaining = i, stop_reason + "_GAP", 0.0
            break
        if partial_idx < 0 and o[i] >= target:
            legs.append((o[i], p.partial_frac))
            remaining -= p.partial_frac
            partial_idx = i
            if remaining <= 1e-12:  # plan.partial_frac = 1 sells everything at the target
                max_px = max(max_px, o[i])
                exit_idx, exit_reason = i, "TARGET"
                break
        if l[i] <= stop_level:
            legs.append((stop_level, remaining))
            max_px, min_px = max(max_px, o[i]), min(min_px, stop_level)
            exit_idx, exit_reason, remaining = i, stop_reason, 0.0
            break
        if partial_idx < 0 and h[i] >= target:
            legs.append((target, p.partial_frac))
            remaining -= p.partial_frac
            partial_idx = i
        max_px, min_px = max(max_px, h[i]), min(min_px, l[i])
        if remaining <= 1e-12:  # plan.partial_frac = 1 sells everything at the target
            exit_idx, exit_reason = i, "TARGET"
            break
        if h[i] >= breakeven_trigger:
            next_stop = max(next_stop, entry_fill)
        if s == p.time_exit_sessions:
            legs.append((c[i], remaining))
            exit_idx, exit_reason, remaining = i, "TIME", 0.0
            break
        if pivot is not None and s <= p.failed_breakout_sessions and c[i] < pivot:
            pending = "FAILED_BREAKOUT"
        elif partial_idx >= 0 and c[i] < trail[i]:
            pending = "TRAIL_EMA"
        elif p.stall_enabled and partial_idx < 0 and s == p.stall_sessions and c[i] < stall_level:
            pending = "STALL"

    label, label_sessions, label_ret, touched = triple_barrier(
        o, h, l, c, t, entry_fill, stop, p.label_upper, p.label_vertical
    )
    last_bar = exit_idx if exit_idx >= 0 else min(t + p.time_exit_sessions, n - 1)
    spans_big = any(big_move[e : last_bar + 1])
    if remaining > 1e-12:
        return Trade("OPEN", "", t, stop, stop_pct_signal, e, entry_raw, entry_fill, stop_pct_entry, -1, "",
                     partial_idx, sessions, NAN, NAN, NAN, max_px / entry_fill - 1.0, min_px / entry_fill - 1.0,
                     label, label_sessions, label_ret, touched, spans_big)

    cost = p.cost_side
    paid = entry_fill * (1.0 + cost)
    proceeds = sum(frac * px * (1.0 - p.slip_side) * (1.0 - cost) for px, frac in legs)
    pnl = proceeds - paid
    ret_gross = sum(frac * px for px, frac in legs) / entry_raw - 1.0
    return Trade(
        "CLOSED", "", t, stop, stop_pct_signal, e, entry_raw, entry_fill, stop_pct_entry, exit_idx, exit_reason,
        partial_idx, sessions, ret_gross, pnl / paid, pnl / risk, max_px / entry_fill - 1.0,
        min_px / entry_fill - 1.0, label, label_sessions, label_ret, touched, spans_big,
    )


def ema_series(close: np.ndarray, span: int) -> np.ndarray:
    """EMA with alpha = 2/(span+1), seeded with the first close; NaN for the first span-1 bars."""

    out = np.full(len(close), np.nan)
    if len(close) == 0:
        return out
    alpha = 2.0 / (span + 1.0)
    value = close[0]
    for i, px in enumerate(close):
        value = px if i == 0 else alpha * px + (1.0 - alpha) * value
        if i >= span - 1:
            out[i] = value
    return out
