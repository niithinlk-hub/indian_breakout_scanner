"""Numba-accelerated technical indicators. All functions are causal (value at i uses data <= i)."""
from __future__ import annotations

import numpy as np
from numba import njit


@njit(cache=True)
def ema(x: np.ndarray, n: int) -> np.ndarray:
    out = np.empty_like(x)
    alpha = 2.0 / (n + 1.0)
    acc = np.nan
    for i in range(x.shape[0]):
        v = x[i]
        if np.isnan(acc):
            acc = v
        elif not np.isnan(v):
            acc = alpha * v + (1.0 - alpha) * acc
        out[i] = acc
    # mark the warm-up period as NaN so early values are not used
    out[: min(n, x.shape[0])] = np.nan
    return out


@njit(cache=True)
def wilder(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    acc = 0.0
    cnt = 0
    for i in range(x.shape[0]):
        v = x[i]
        if np.isnan(v):
            out[i] = out[i - 1] if i > 0 else np.nan
            continue
        if cnt < n:
            acc += v
            cnt += 1
            if cnt == n:
                acc = acc / n
                out[i] = acc
        else:
            acc = (acc * (n - 1) + v) / n
            out[i] = acc
    return out


@njit(cache=True)
def true_range(h: np.ndarray, l: np.ndarray, c: np.ndarray) -> np.ndarray:
    tr = np.empty_like(c)
    tr[0] = h[0] - l[0]
    for i in range(1, c.shape[0]):
        pc = c[i - 1]
        tr[i] = max(h[i] - l[i], abs(h[i] - pc), abs(l[i] - pc))
    return tr


@njit(cache=True)
def atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    return wilder(true_range(h, l, c), n)


@njit(cache=True)
def adx(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14):
    size = c.shape[0]
    pdm = np.zeros(size)
    ndm = np.zeros(size)
    for i in range(1, size):
        # round to 1e-6 so equal moves on the tick grid are ties (not decided by float noise)
        up = np.round(h[i] - h[i - 1], 6)
        dn = np.round(l[i - 1] - l[i], 6)
        if up > dn and up > 0:
            pdm[i] = up
        if dn > up and dn > 0:
            ndm[i] = dn
    tr = true_range(h, l, c)
    atr_ = wilder(tr, n)
    spdm = wilder(pdm, n)
    sndm = wilder(ndm, n)
    pdi = np.full(size, np.nan)
    ndi = np.full(size, np.nan)
    dx = np.full(size, np.nan)
    for i in range(size):
        a = atr_[i]
        if not np.isnan(a) and a > 0:
            pdi[i] = 100.0 * spdm[i] / a
            ndi[i] = 100.0 * sndm[i] / a
            s = pdi[i] + ndi[i]
            dx[i] = 100.0 * abs(pdi[i] - ndi[i]) / s if s > 0 else 0.0
    return wilder(dx, n), pdi, ndi


@njit(cache=True)
def session_vwap(h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, day_id: np.ndarray) -> np.ndarray:
    out = np.empty_like(c)
    pv = 0.0
    vv = 0.0
    cur = -1
    for i in range(c.shape[0]):
        if day_id[i] != cur:
            cur = day_id[i]
            pv = 0.0
            vv = 0.0
        tp = (h[i] + l[i] + c[i]) / 3.0
        pv += tp * v[i]
        vv += v[i]
        out[i] = pv / vv if vv > 0 else tp
    return out


@njit(cache=True)
def rolling_max(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    for i in range(n - 1, x.shape[0]):
        m = x[i]
        for j in range(i - n + 1, i):
            if x[j] > m:
                m = x[j]
        out[i] = m
    return out


@njit(cache=True)
def rolling_min(x: np.ndarray, n: int) -> np.ndarray:
    out = np.full_like(x, np.nan)
    for i in range(n - 1, x.shape[0]):
        m = x[i]
        for j in range(i - n + 1, i):
            if x[j] < m:
                m = x[j]
        out[i] = m
    return out


@njit(cache=True)
def slot_rvol(v: np.ndarray, day_id: np.ndarray, slot: np.ndarray, n_slots: int, lookback: int = 20) -> np.ndarray:
    """Volume / mean volume of the same time-of-day slot over the previous `lookback` sessions."""
    size = v.shape[0]
    out = np.full(size, np.nan)
    hist = np.full((n_slots, lookback), np.nan)
    count = np.zeros(n_slots, dtype=np.int64)
    pos = np.zeros(n_slots, dtype=np.int64)
    for i in range(size):
        s = slot[i]
        if s < 0 or s >= n_slots:
            continue
        if count[s] >= min(lookback, 10):
            m = 0.0
            k = 0
            for j in range(lookback):
                if not np.isnan(hist[s, j]):
                    m += hist[s, j]
                    k += 1
            m = m / k if k > 0 else np.nan
            out[i] = v[i] / m if m > 0 else np.nan
        hist[s, pos[s]] = v[i]
        pos[s] = (pos[s] + 1) % lookback
        count[s] += 1
    return out
