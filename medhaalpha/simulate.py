"""Bar-by-bar trade simulator (numba).

Simulation runs on the *base* bars (3-minute or 5-minute) even when signals come from a
higher timeframe, so the intrabar order of stop/target hits is resolved as finely as the
data allows. Conservative conventions:
  * a bar that touches both stop and target is a stop-out;
  * opening gaps through a stop/target fill at the open;
  * after a stop-order entry, the remainder of that bar can only stop the trade out;
  * EMA-based exits are signalled on the completed signal-timeframe bar and executed
    at the next base bar's open.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numba import njit

REASONS = {1: "stop", 2: "target", 3: "trail", 4: "ema_exit", 5: "time", 6: "end_of_data", 7: "breakeven"}


@dataclass(frozen=True)
class ExitSpec:
    stop_mode: int = 0  # 0 structure (absolute level from signal), 1 ATR multiple from fill
    stop_k: float = 1.5  # ATR multiple when stop_mode == 1
    target_r: float = 2.0  # 0 = no fixed target
    trail_k: float = 0.0  # ATR chandelier trail multiple (0 = off)
    ema_mode: int = 0  # 0 off, 1 close beyond EMA20, 2 EMA20/50 cross against the trade
    partial_r: float = 0.0  # take `partial_frac` off at this R multiple (0 = off)
    partial_frac: float = 0.5
    min_stop_atr: float = 0.5
    max_stop_atr: float = 3.0

    @property
    def label(self) -> str:
        stop = "struct" if self.stop_mode == 0 else f"atr{self.stop_k:g}"
        parts = [stop]
        if self.partial_r > 0:
            parts.append(f"part{self.partial_r:g}R")
        if self.target_r > 0:
            parts.append(f"tgt{self.target_r:g}R")
        if self.trail_k > 0:
            parts.append(f"trail{self.trail_k:g}")
        if self.ema_mode == 1:
            parts.append("ema20x")
        elif self.ema_mode == 2:
            parts.append("emaX")
        if len(parts) == 1:
            parts.append("timeonly")
        return "+".join(parts)


@njit(cache=True)
def simulate(
    bo, bh, bl, bc, bday, entry_ok, flat_bar, last_bar,
    t_close, t_ema20, t_ema50, t_atr,
    act_i, side, etype, level, valid_n, stop_abs, atr_sig, intraday,
    max_sessions, stop_mode, stop_k, target_r, trail_k, ema_mode, partial_r, partial_frac,
    min_stop_atr, max_stop_atr,
):
    n = act_i.shape[0]
    nb = bo.shape[0]
    out_fill_i = np.full(n, -1, np.int64)
    out_fill = np.full(n, np.nan)
    out_stop = np.full(n, np.nan)
    out_exit_i = np.full(n, -1, np.int64)
    out_exit = np.full(n, np.nan)
    out_reason = np.zeros(n, np.int8)
    out_nexit = np.zeros(n, np.int8)
    out_mfe = np.full(n, np.nan)
    out_mae = np.full(n, np.nan)
    for k in range(n):
        a = act_i[k]
        if a < 0 or a >= nb:
            continue
        sd = float(side[k])
        sig_day = bday[a]
        # ---------------- fill
        fi = -1
        fp = np.nan
        if etype[k] == 0:
            if entry_ok[a]:
                fi = a
                fp = bo[a]
        else:
            for j in range(a, min(nb, a + valid_n[k])):
                if not entry_ok[j]:
                    if intraday[k] and bday[j] != sig_day:
                        break
                    continue
                if intraday[k] and bday[j] != sig_day:
                    break
                lv = level[k]
                if sd > 0 and bh[j] >= lv:
                    fi = j
                    fp = max(lv, bo[j])
                    break
                if sd < 0 and bl[j] <= lv:
                    fi = j
                    fp = min(lv, bo[j])
                    break
        if fi < 0:
            continue
        atr0 = atr_sig[k]
        if stop_mode == 0:
            stop = stop_abs[k]
            dist = sd * (fp - stop)
            if dist <= 0:
                continue  # setup invalidated by a gap through the structural stop
        else:
            dist = stop_k * atr0
        if dist < min_stop_atr * atr0:
            dist = min_stop_atr * atr0
        if dist > max_stop_atr * atr0:
            dist = max_stop_atr * atr0
        stop = fp - sd * dist
        init_stop = stop
        tgt = fp + sd * target_r * dist if target_r > 0 else np.nan
        ptgt = fp + sd * partial_r * dist if partial_r > 0 else np.nan
        part_done = False
        part_px = 0.0
        hh = fp
        ll = fp
        sessions = 1
        pend_exit = False
        ex_i = -1
        ex_px = np.nan
        reason = 0
        mfe = 0.0
        mae = 0.0
        moved = False
        for j in range(fi, nb):
            if j > fi and bday[j] != bday[j - 1]:
                sessions += 1
            o, hi, lo, cl = bo[j], bh[j], bl[j], bc[j]
            if j > fi:
                if pend_exit:
                    ex_i, ex_px, reason = j, o, 4
                    break
                # gaps at the open
                if sd * (o - stop) <= 0:
                    ex_i, ex_px = j, o
                    reason = 7 if (part_done and stop == fp) else (3 if (moved and stop != init_stop) else 1)
                    break
                if target_r > 0 and sd * (o - tgt) >= 0:
                    ex_i, ex_px, reason = j, o, 2
                    break
            first_bar_stop_entry = (j == fi) and (etype[k] == 1)
            # intrabar stop
            adverse = lo if sd > 0 else hi
            favour = hi if sd > 0 else lo
            if sd * (adverse - stop) <= 0:
                ex_i, ex_px = j, stop
                reason = 7 if (part_done and stop == fp) else (3 if (moved and stop != init_stop) else 1)
                break
            if not first_bar_stop_entry:
                if partial_r > 0 and not part_done and sd * (favour - ptgt) >= 0:
                    part_done = True
                    part_px = ptgt
                if target_r > 0 and sd * (favour - tgt) >= 0:
                    ex_i, ex_px, reason = j, tgt, 2
                    break
            # excursions
            hh = max(hh, hi)
            ll = min(ll, lo)
            fav = (hh - fp) if sd > 0 else (fp - ll)
            adv = (fp - ll) if sd > 0 else (hh - fp)
            mfe = max(mfe, fav / dist)
            mae = max(mae, adv / dist)
            # end-of-bar management on completed signal-timeframe bars
            if part_done and sd * (fp - stop) > 0:
                stop = fp  # breakeven after partial
                moved = True
            if not np.isnan(t_close[j]):
                if trail_k > 0 and not np.isnan(t_atr[j]):
                    trail = (hh - trail_k * t_atr[j]) if sd > 0 else (ll + trail_k * t_atr[j])
                    if sd * (trail - stop) > 0:
                        stop = trail
                        moved = True
                if ema_mode == 1 and sd * (t_close[j] - t_ema20[j]) < 0:
                    pend_exit = True
                elif ema_mode == 2 and sd * (t_ema20[j] - t_ema50[j]) < 0:
                    pend_exit = True
            # time exits
            if intraday[k] and flat_bar[j]:
                ex_i, ex_px, reason = j, cl, 5
                break
            if (not intraday[k]) and last_bar[j] and sessions >= max_sessions:
                ex_i, ex_px, reason = j, cl, 5
                break
        if ex_i < 0:
            ex_i, ex_px, reason = nb - 1, bc[nb - 1], 6
        mae = max(mae, sd * (fp - ex_px) / dist)
        mfe = max(mfe, sd * (ex_px - fp) / dist)
        if part_done:
            avg = partial_frac * part_px + (1.0 - partial_frac) * ex_px
            nexit = 2
        else:
            avg = ex_px
            nexit = 1
        out_fill_i[k] = fi
        out_fill[k] = fp
        out_stop[k] = init_stop
        out_exit_i[k] = ex_i
        out_exit[k] = avg
        out_reason[k] = reason
        out_nexit[k] = nexit
        out_mfe[k] = mfe
        out_mae[k] = mae
    return out_fill_i, out_fill, out_stop, out_exit_i, out_exit, out_reason, out_nexit, out_mfe, out_mae
