# Independent bar-by-bar re-implementation of the VW rules (plain Python loop, pandas VWAP) to cross-check run.py's
# vectorised engine on the picked rows of every set. Not part of the result; prints mismatches only.
import sys
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
src = open(SP + '/hunt/vwap_trail/run.py').read().split('# ---------------------------------------------------------------------------------------------- engine check')[0]
exec(src)
CHK = {'%02d:%02d' % divmod(m, 60) for m in range(9 * 60 + 44, 15 * 60 + 15, 30)}


def loop(dm, side, sigtime, stop, mode):
    tp = (dm.high + dm.low + dm.close) / 3
    vwap = ((tp * dm.volume).cumsum() / dm.volume.cumsum()).tolist()
    hm = list(dm.index.strftime('%H:%M'))
    O, Hh, L, Cc, IX = dm.open.tolist(), dm.high.tolist(), dm.low.tolist(), dm.close.tolist(), dm.index
    e = next(i for i in range(len(dm)) if hm[i] > sigtime)
    E = O[e]
    R = abs(E - stop)
    lg = side == 'LONG'
    mfe = 0.0
    for k in range(e, len(dm)):
        o, h, l, c = O[k], Hh[k], L[k], Cc[k]
        if lg and (o <= stop or l <= stop):
            return (o if o <= stop else stop), IX[k]
        if (not lg) and (o >= stop or h >= stop):
            return (o if o >= stop else stop), IX[k]
        mfe = max(mfe, (h - E) if lg else (E - l))
        is_chk = (hm[k] in CHK) if mode == 'VW30' else True
        if mode == 'VW1M' and mfe < 0.5 * R:
            is_chk = False
        if is_chk and ((lg and c < vwap[k]) or ((not lg) and c > vwap[k])):
            if k + 1 < len(dm):
                return O[k + 1], IX[k + 1]
            return c, IX[k]
    return Cc[-1], IX[-1]


for s in H.SETS:
    df = D[s]
    idx = sorted(set(H.pick(df, 's_fable_op', 75, 6).index) | set(H.pick(df, 's_opus_v3', 75, 6).index))
    bad = 0
    for ix in idx:
        r = df.loc[ix]
        m = mins[r.symbol]
        dm = m.loc[r.day]
        for mode in ('VW30', 'VW1', 'VW1M'):
            X, xts = loop(dm, r.side, r.time, r.E_stop, mode)
            if xts.isoformat() != r['o_exit_ts_E' + mode] or abs(r.o_F0 * X / r.E_entry - r['o_F1_E' + mode]) > 1e-6:
                bad += 1
                print('MISMATCH', s, r.day, r.time, r.symbol, mode, xts, X, r['o_exit_ts_E' + mode], r['o_F1_E' + mode])
    print('%s: %d picked rows x 3 VW rules, %d mismatches' % (s, len(idx), bad))
