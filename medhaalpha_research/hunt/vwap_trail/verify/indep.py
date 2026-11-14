# Reviewer's independent recomputation of vwap_trail S3 (Fable-OP picks, 1-minute VWAP checks once MFE >= 0.5R),
# written from the pre-registered spec only (does not import run.py). Uses harness.py directly for picks and option pricing.
import sys, json
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

D = H.load_all()
mins, daily, nifty, lot = H.minute_data()


def session(sym, day):
    m = mins[sym]
    dm = m[m.index.strftime('%Y-%m-%d') == day]
    hm = dm.index.strftime('%H:%M')
    return dm[(hm >= '09:15') & (hm <= '15:29')]


def sim(dm, side, sigtime, stop_from_E, mode, target_from_E=None):
    """mode: 'CLOSE' (stop only), 'TGT' (stop + target), 'VW1M' (stop + VWAP once MFE>=0.5R), 'VW1', 'VW30'.
    Returns E, X, exit_ts."""
    hm = list(dm.index.strftime('%H:%M'))
    O = dm['open'].values; Hh = dm['high'].values; L = dm['low'].values; Cl = dm['close'].values; V = dm['volume'].values
    tp = (Hh + L + Cl) / 3.0
    cv = np.cumsum(V); cpv = np.cumsum(tp * V)
    e = next(i for i in range(len(dm)) if hm[i] > sigtime)
    E = float(O[e])
    stop = stop_from_E(E)
    tgt = target_from_E(E) if target_from_E else None
    R = abs(E - stop)
    lg = side == 'LONG'
    best = -np.inf
    for k in range(e, len(dm)):
        o, h, l, c = O[k], Hh[k], L[k], Cl[k]
        if lg:
            if o <= stop: return E, float(o), dm.index[k], 'stop_gap'
            if l <= stop: return E, float(stop), dm.index[k], 'stop'
        else:
            if o >= stop: return E, float(o), dm.index[k], 'stop_gap'
            if h >= stop: return E, float(stop), dm.index[k], 'stop'
        if tgt is not None:
            if lg and (o >= tgt or h >= tgt): return E, float(o if o >= tgt else tgt), dm.index[k], 'target'
            if (not lg) and (o <= tgt or l <= tgt): return E, float(o if o <= tgt else tgt), dm.index[k], 'target'
        best = max(best, (h - E) if lg else (E - l))
        if mode.startswith('VW'):
            active = True
            if mode == 'VW1M':
                active = best >= 0.5 * R
            if mode == 'VW30':
                mm = int(hm[k][:2]) * 60 + int(hm[k][3:])
                active = (mm - (9 * 60 + 44)) % 30 == 0 and 584 <= mm <= 914
            vw = cpv[k] / cv[k] if cv[k] > 0 else np.nan
            if active and np.isfinite(vw) and ((lg and c < vw) or ((not lg) and c > vw)):
                if k + 1 < len(dm):
                    return E, float(O[k + 1]), dm.index[k + 1], 'vwap'
    return E, float(Cl[-1]), dm.index[-1], 'close'


def make_trades(s, mode, score='s_fable_op'):
    df = D[s]
    t = H.pick(df, score, 75, 6).copy()
    real = s == 'real'
    F1, XT, WHY = [], [], []
    for ix, r in t.iterrows():
        dm = session(r.symbol, r.day)
        sgn = 1 if r.side == 'LONG' else -1
        if real:
            stopf = lambda E, r=r, sgn=sgn: E * (1 - sgn * r.o_risk_abs / r.o_F0)
        else:
            stopf = lambda E, r=r: float(r.stop)
        tgtf = None
        if mode == 'T3':
            tgtf = (lambda E, r=r, sgn=sgn: r.price * (1 + sgn * 2.6 * r.risk_pct / 100)) if real else (lambda E, r=r: float(r.t3))
        E, X, xts, why = sim(dm, r.side, r.time, stopf, 'TGT' if mode == 'T3' else mode, tgtf)
        F1.append(r.o_F0 * X / E); XT.append(xts.isoformat()); WHY.append(why)
    t['o_F1_X'] = F1; t['o_exit_ts_X'] = XT; t['why'] = WHY
    t['pnl'] = H.option_net(t, 'X')
    return t


def summary(t, s, lo=None, hi=None):
    days = sorted(D[s].day.unique())
    if lo:
        days = [d for d in days if lo <= d <= hi]
        t = t[(t.day >= lo) & (t.day <= hi)]
    by = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
    eq = by.cumsum()
    return {'n': len(t), 'net': round(float(t.pnl.sum())), 'worst_day': round(float(by.min())),
            'maxdd': round(float((eq - eq.cummax().clip(lower=0)).min()))}, by


out = {}
H2 = ('2026-09-01', '2026-11-11')
for s in ('unseen', 'real', 'known'):
    # sanity: my loop with VWAP disabled vs harness opt_CLOSE / opt_T3 on the same picks
    tc = make_trades(s, 'CLOSE')
    base = H.pick(D[s], 's_fable_op', 75, 6)
    print('%s sanity CLOSE: mine %+d harness %+d | exit ts match %.1f%%' % (s, tc.pnl.sum(), base.opt_CLOSE.sum(), 100 * (tc.o_exit_ts_X == base.o_exit_ts_CLOSE).mean()))
    t3 = make_trades(s, 'T3')
    print('%s sanity T3:    mine %+d harness %+d | exit ts match %.1f%%' % (s, t3.pnl.sum(), base.opt_T3.sum(), 100 * (t3.o_exit_ts_X == base.o_exit_ts_T3).mean()))
    tv = make_trades(s, 'VW1M')
    print('%s exit mix VW1M: %s' % (s, tv.why.value_counts().to_dict()))
    a, by_c = summary(tv, s)
    print('%s VW1M S3 all: %s' % (s, a))
    halves = H.halves(s)
    for i, (lo, hi) in enumerate(halves):
        print('   h%d %s' % (i + 1, summary(tv, s, lo, hi)[0]))
    out[s] = {'cand': tv, 'mineT3': t3, 'base': base}

# ---- bootstrap of per-day difference vs the better baseline (same picks), unseen and real h2
rng = np.random.default_rng(7)


def boot(diff, B=20000):
    x = diff.values
    m = rng.integers(0, len(x), (B, len(x)))
    bs = x[m].sum(1)
    return float(x.sum()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float((bs <= 0).mean())


print('\n-- bootstrap (days resampled) of candidate minus baseline, option net')
for s, lo, hi in (('unseen', None, None), ('real', H2[0], H2[1]), ('known', None, None), ('real', None, None)):
    days = sorted(D[s].day.unique())
    if lo:
        days = [d for d in days if lo <= d <= hi]
    c = out[s]['cand']; c = c[c.day.isin(days)]
    by_c = c.pnl.groupby(c.day).sum().reindex(days).fillna(0)
    for bname, spec in (('Fable-OP T3 (harness)', ('s_fable_op', 75, 'T3', 6)), ('Opus v3 T1 (harness)', ('s_opus_v3', 75, 'T1', 6))):
        tb = H.run(D[s], spec); tb = tb[tb.day.isin(days)]
        by_b = tb.pnl.groupby(tb.day).sum().reindex(days).fillna(0)
        d = by_c - by_b
        tot, l, h, p = boot(d)
        print('  %-6s %-9s vs %-22s diff %+9.0f  95%% CI [%+9.0f, %+9.0f]  P(diff<=0) %.3f  days %d' % (s, 'h2' if lo else 'all', bname, tot, l, h, p, len(days)))
    t3 = out[s]['mineT3']; t3 = t3[t3.day.isin(days)]
    by_e = t3.pnl.groupby(t3.day).sum().reindex(days).fillna(0)
    tot, l, h, p = boot(by_c - by_e)
    print('  %-6s %-9s vs %-22s diff %+9.0f  95%% CI [%+9.0f, %+9.0f]  P(diff<=0) %.3f' % (s, 'h2' if lo else 'all', 'my T3 re-sim (same pk)', tot, l, h, p))

# ---- sensitivity of the unseen gain to the option model (decay / IV), candidate vs Fable-OP T3 same picks
print('\n-- option-model sensitivity, unseen, candidate minus Fable-OP T3 (harness T3 exits)')
for dec in (1.0, 2.31, 3.5):
    for ivm in (0.8, 1.0, 1.2):
        c = out['unseen']['cand']; b = out['unseen']['base']
        cn = H.option_net(c, 'X', decay=dec, iv_mult=ivm).sum(); bn = H.option_net(b, 'T3', decay=dec, iv_mult=ivm).sum()
        print('  decay %.2f iv x%.1f: cand %+9.0f  FableT3 %+9.0f  diff %+9.0f' % (dec, ivm, cn, bn, cn - bn))

# top-day concentration of the unseen edge
c = out['unseen']['cand']; days = sorted(D['unseen'].day.unique())
tb = H.run(D['unseen'], ('s_fable_op', 75, 'T3', 6))
d = (c.pnl.groupby(c.day).sum().reindex(days).fillna(0) - tb.pnl.groupby(tb.day).sum().reindex(days).fillna(0)).sort_values()
print('\nunseen per-day diff vs Fable-OP T3: total %+d, top5 days %+d, bottom5 days %+d, total excl top5 %+d' % (d.sum(), d.tail(5).sum(), d.head(5).sum(), d.sum() - d.tail(5).sum()))
print(d.tail(5).round(0).to_dict())
