"""Independent re-computation of opt_eqrisk_lots candidate (a): Fable-OP>=75, T3, cap 2x, B = B_eq (design window).
Written from the pre-registered spec, not from the tester's code. Uses harness.py directly for pick / option_net / costs.
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

D = H.load_all()
DES = ('2026-05-12', '2026-08-31')
H2R = ('2026-09-01', '2026-11-11')


def b76(F, K, T, s, call):
    v = s * np.sqrt(np.maximum(T, 1e-12))
    d1 = (np.log(F / K) + 0.5 * v * v) / v
    d2 = d1 - v
    c = F * norm.cdf(d1) - K * norm.cdf(d2)
    p = K * norm.cdf(-d2) - F * norm.cdf(-d1)
    return np.where(call, c, p)


def years(ts, exp):
    t = pd.to_datetime(ts, utc=True)
    e = pd.to_datetime(exp.astype(str) + ' 15:30').dt.tz_localize('Asia/Kolkata').dt.tz_convert('UTC')
    return ((e.values - t.values) / np.timedelta64(1, 's')) / (365 * 86400)


# known-set lot table for real
K = D['known'][['symbol', 'day', 'lot']].drop_duplicates()


def lots_for(t, setname):
    if setname != 'real':
        return t['lot'].to_numpy(float), np.zeros(len(t), bool)
    out, absent = [], []
    for s, d, q in zip(t.symbol, t.day, t.o_qty):
        g = K[K.symbol == s].sort_values('day')
        if len(g) == 0:
            out.append(q); absent.append(True); continue
        prior = g[g.day <= d]
        l = prior.lot.iloc[-1] if len(prior) else g.lot.iloc[0]
        out.append(q if q % l else l); absent.append(False)
    return np.array(out, float), np.array(absent)


def inputs(t, setname):
    call = (t.o_kind == 'CE').to_numpy()
    sgn = np.where(call, 1.0, -1.0)
    F0 = t.o_F0.to_numpy(float)
    T0 = years(t.o_entry_ts, t.o_expiry)
    iv = t.o_iv.to_numpy(float)
    p0 = b76(F0, F0, T0, iv, call)
    pS = b76(F0 - sgn * t.o_risk_abs.to_numpy(float), F0, T0, iv, call)
    lot, absent = lots_for(t, setname)
    fl = t.o_qty.to_numpy(float) / lot
    Ll = 1.2 * (p0 - pS) * lot + H.opt_costs(p0, pS, lot)
    return dict(p0=p0, pS=pS, lot=lot, fl=fl, Ll=Ll, absent=absent, q0=t.o_qty.to_numpy(float))


def L_of(I, B, cap):
    return np.clip(np.floor(B / I['Ll']), 1, cap * I['fl'])


# ---- B_eq by exhaustive scan on the design window (Rs 0.5 steps), independent of bisection
tr = H.pick(D['real'], 's_fable_op', 75, 6)
td = tr[(tr.day >= DES[0]) & (tr.day <= DES[1])]
Id = inputs(td, 'real')
target = (Id['p0'] * Id['q0']).sum()
Bs = np.arange(1000, 60000.5, 0.5)
outl = np.array([(Id['p0'] * L_of(Id, b, 2) * Id['lot']).sum() for b in Bs])
i_first = np.argmax(outl >= target)
print('design picks', len(td), 'absent-lot rows', Id['absent'].sum(), 'target outlay', round(target))
print('smallest B with outlay >= target: %.1f (outlay %.0f, ratio %.4f); B just below: %.1f (outlay %.0f, ratio %.4f)'
      % (Bs[i_first], outl[i_first], outl[i_first] / target, Bs[i_first - 1], outl[i_first - 1], outl[i_first - 1] / target))
# step interval containing tester's B=7881.7
B_t = 7881.7
o_t = (Id['p0'] * L_of(Id, B_t, 2) * Id['lot']).sum()
same = Bs[np.isclose(outl, o_t)]
print('tester B=%.1f outlay %.0f; this outlay holds for B in [%.1f, %.1f]' % (B_t, o_t, same.min(), same.max()))
B = B_t


def cand(setname, B=B, cap=2):
    t = H.pick(D[setname], 's_fable_op', 75, 6).copy()
    I = inputs(t, setname)
    L = L_of(I, B, cap)
    t['L'], t['fl'], t['Ll'] = L, I['fl'], I['Ll']
    q = L * I['lot']
    t['pnl'] = H.option_net(t, 'T3', qty=q).to_numpy()
    t['outlay'] = I['p0'] * q
    t['base'] = t['opt_T3']
    # own full repricing of the option (independent of option_net) as a cross-check
    call = (t.o_kind == 'CE').to_numpy()
    F0, F1 = t.o_F0.to_numpy(float), t.o_F1_T3.to_numpy(float)
    T0 = years(t.o_entry_ts, t.o_expiry)
    hold = (pd.to_datetime(t.o_exit_ts_T3, utc=True) - pd.to_datetime(t.o_entry_ts, utc=True)).dt.total_seconds().to_numpy() / 60 + 1
    T1 = T0 - 2.31 * hold / 525600
    p0, p1 = b76(F0, F0, T0, t.o_iv.to_numpy(float), call), b76(F1, F0, T1, t.o_iv.to_numpy(float), call)
    t['own'] = q * (p1 - p0) - H.opt_costs(p0, p1, q)
    return t


def daily(t, days):
    return t.groupby('day').pnl.sum().reindex(days).fillna(0.0)


def ddstats(s):
    eq = s.cumsum()
    return round(s.sum()), round(s.min()), round((eq - eq.cummax().clip(lower=0)).min())


def base(setname, sc, pol):
    t = H.pick(D[setname], sc, 75, 6).copy()
    t['pnl'] = t['opt_' + pol]
    return t


rng = np.random.default_rng(7)
for setname, lo, hi in (('unseen', '2025-11-03', '2026-05-11'), ('real', H2R[0], H2R[1]), ('real', DES[0], DES[1]),
                        ('unseen', '2025-11-03', '2026-02-05'), ('unseen', '2026-02-06', '2026-05-11'),
                        ('known', '2026-05-12', '2026-07-31'), ('known', '2026-08-01', '2026-10-19')):
    days = sorted(d for d in D[setname].day.unique() if lo <= d <= hi)
    c = cand(setname)
    c = c[(c.day >= lo) & (c.day <= hi)]
    f = base(setname, 's_fable_op', 'T3'); f = f[(f.day >= lo) & (f.day <= hi)]
    o = base(setname, 's_opus_v3', 'T1'); o = o[(o.day >= lo) & (o.day <= hi)]
    dc, df_, do = daily(c, days), daily(f, days), daily(o, days)
    print('\n== %s %s..%s (%d days)' % (setname, lo, hi, len(days)))
    print('  candidate  n=%d net/worst/maxDD %s   own-repricing net %.0f   |max diff option_net vs own| %.2f' % (len(c), ddstats(dc), c.own.sum(), (c.pnl - c.own).abs().max()))
    print('  Fable-OP   n=%d %s' % (len(f), ddstats(df_)))
    print('  Opus v3    n=%d %s' % (len(o), ddstats(do)))
    print('  lots changed: up %d, down %d, same %d; floor binding (B/Ll<1 and fl>1) %d; fut_lots==1 %d'
          % ((c.L > c.fl).sum(), (c.L < c.fl).sum(), (c.L == c.fl).sum(), ((np.floor(B / c.Ll) < 1) & (c.fl > 1)).sum(), (c.fl == 1).sum()))
    diff = (dc - df_).to_numpy()
    bs = np.array([rng.choice(diff, len(diff)).sum() for _ in range(10000)])
    print('  diff vs Fable-OP: total %+.0f, sd of daily diff %.0f, nonzero days %d, bootstrap 90%% CI [%+.0f, %+.0f], P(>0)=%.3f'
          % (diff.sum(), diff.std(), (np.abs(diff) > 1).sum(), np.percentile(bs, 5), np.percentile(bs, 95), (bs > 0).mean()))
    # worst-day attribution
    wd = dc.idxmin()
    print('  candidate worst day %s: %+.0f (Fable-OP that day %+.0f)' % (wd, dc[wd], df_[wd]))
    x = c[c.day == wd][['symbol', 'time', 'L', 'fl', 'pnl', 'base']]
    print(x.to_string().replace('\n', '\n    '))

# ---- sensitivity of candidate to B around B_eq (not a choice, just how fragile)
print('\nB sensitivity (option net): unseen all / real 2nd half / design')
for b in (6000, 7000, 7500, 7882, 8500, 9000, 10000):
    u = cand('unseen', b).pnl.sum()
    r = cand('real', b); rh2 = r[r.day >= H2R[0]].pnl.sum(); rd = r[r.day <= DES[1]].pnl.sum()
    print('  B=%5d  unseen %+9.0f  real h2 %+9.0f  design %+9.0f' % (b, u, rh2, rd))
