"""Independent re-implementation of setting c (per-side logistic stacker, Platt per side, quantile gate 5.97 %, exit T3)
plus checks: option columns == harness.option_net, own pick / P&L / risk stats, day-block bootstrap vs better baseline."""
import sys
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

D = H.load_all()
print('time dtype / sample:', D['real']['time'].dtype, D['real']['time'].iloc[:3].tolist())

# 1. option columns are the harness's Black-76 option_net (no outcome shortcut)
for s in H.SETS:
    for p in ('T1', 'T3'):
        fresh = H.option_net(D[s], p)
        print('option check %-6s %s max |opt_col - option_net| = %.6f' % (s, p, float(np.abs(fresh - D[s]['opt_' + p]).max())))


def platt(f, y):
    """Platt (2000) with his target smoothing; returns (a, b) for p = 1/(1+exp(a f + b))."""
    n1 = y.sum(); n0 = len(y) - n1
    t = np.where(y > 0, (n1 + 1) / (n1 + 2), 1 / (n0 + 2))

    def nll(ab):
        z = -(ab[0] * f + ab[1])
        p = np.clip(expit(z), 1e-15, 1 - 1e-15)
        return -np.sum(t * np.log(p) + (1 - t) * np.log(1 - p))
    r = minimize(nll, x0=np.array([0.0, np.log((n0 + 1) / (n1 + 1))]), method='Nelder-Mead', options={'xatol': 1e-10, 'fatol': 1e-12, 'maxiter': 20000})
    return r.x


def Xc(d):
    a, b = d['s_opus'].to_numpy(float), d['s_fable_op'].to_numpy(float)
    return np.column_stack([a, b, a * b])


def fit_lr(X, y):
    sc = StandardScaler().fit(X)
    m = LogisticRegression(C=1.0, max_iter=1000).fit(sc.transform(X), y)
    return lambda Z: m.decision_function(sc.transform(Z))


real = D['real']
des_m = (real.day >= '2026-05-12') & (real.day <= '2026-08-31')
des = real[des_m]
y = (des['opt_T3'] > 0).astype(int).to_numpy()
print('design rows', len(des), 'days', des.day.nunique(), 'label rate', y.mean().round(4))
folds = list(GroupKFold(n_splits=5).split(des, groups=des['day']))
raw = np.full(len(des), np.nan)
side = des['side'].to_numpy()
for tr, te in folds:
    for sd in ('LONG', 'SHORT'):
        a = tr[side[tr] == sd]; b = te[side[te] == sd]
        f = fit_lr(Xc(des.iloc[a]), y[a])
        raw[b] = f(Xc(des.iloc[b]))
p_des = np.full(len(des), np.nan)
AB, FIN = {}, {}
for sd in ('LONG', 'SHORT'):
    m = side == sd
    AB[sd] = platt(raw[m], y[m])
    p_des[m] = expit(-(AB[sd][0] * raw[m] + AB[sd][1]))
    FIN[sd] = fit_lr(Xc(des[m]), y[m])
    print('Platt %s a %+.4f b %+.4f' % (sd, AB[sd][0], AB[sd][1]))
k = int(round(0.0597 * len(des)))
thr = np.sort(p_des)[::-1][k - 1]
print('k', k, 'thr %.5f' % thr)


def score(d):
    out = pd.Series(np.nan, index=d.index)
    for sd in ('LONG', 'SHORT'):
        m = (d.side == sd).to_numpy()
        if m.any():
            out[m] = expit(-(AB[sd][0] * FIN[sd](Xc(d[m])) + AB[sd][1]))
    return out


real = real.copy()
real['pc'] = np.nan
real.loc[des.index, 'pc'] = p_des
real.loc[real.index[~des_m], 'pc'] = score(real[~des_m]).values
U = D['unseen'].copy(); U['pc'] = score(U)
K = D['known'].copy(); K['pc'] = score(K)


def my_pick(d, col, thr, n=6):
    x = d[d[col] >= thr].copy()
    x = x.sort_values(['day', 'time', col, 'symbol'], ascending=[True, True, False, True], kind='mergesort')
    x['rk'] = x.groupby('day').cumcount()
    return x[x.rk < n]


def st(t, pcol, days):
    by = t.groupby('day')[pcol].sum().reindex(days).fillna(0.0)
    eq = by.cumsum()
    dd = (eq - np.maximum(eq.cummax(), 0)).min()
    return dict(n=len(t), net=round(t[pcol].sum()), worst=round(by.min()), maxdd=round(dd)), by


def base_trades(d):
    return {'Opus v3 (T1)': (my_pick(d, 's_opus_v3', 75), 'T1'), 'Fable-OP (T3)': (my_pick(d, 's_fable_op', 75), 'T3')}


rng = np.random.default_rng(0)
results = {}
for nm, d, lo, hi in [('real_h2', real, '2026-09-01', '2026-11-11'), ('unseen', U, '2025-11-03', '2026-05-11'),
                      ('unseen_h1', U, '2025-11-03', '2026-02-05'), ('unseen_h2', U, '2026-02-06', '2026-05-11'),
                      ('design', real, '2026-05-12', '2026-08-31'), ('known', K, '2026-05-12', '2026-10-19')]:
    dd_ = d[(d.day >= lo) & (d.day <= hi)]
    days = sorted(dd_.day.unique())
    tc = my_pick(dd_, 'pc', thr)
    sc, byc = st(tc, 'opt_T3', days)
    scf, _ = st(tc, 'net_T3', days)
    line = '%-10s META c: n %d opt net %+d worst %+d maxDD %+d fut %+d | gate rate %.2f%%' % (nm, sc['n'], sc['net'], sc['worst'], sc['maxdd'], scf['net'], 100 * (dd_.pc >= thr).mean())
    print(line)
    bys = {}
    for bn, (bt, pol) in base_trades(dd_).items():
        sb, byb = st(bt, 'opt_' + pol, days)
        bys[bn] = (sb, byb)
        print('%-10s %-13s n %d opt net %+d worst %+d maxDD %+d' % ('', bn, sb['n'], sb['net'], sb['worst'], sb['maxdd']))
    better = max(bys, key=lambda b: bys[b][0]['net'])
    diff = (byc - bys[better][1]).to_numpy()
    bs = np.array([rng.choice(diff, len(diff), replace=True).sum() for _ in range(5000)])
    # 5-day block bootstrap too
    nb = len(diff) // 5
    blocks = [diff[i:i + 5] for i in range(0, len(diff), 5)]
    bsb = np.array([np.concatenate([blocks[j] for j in rng.integers(0, len(blocks), len(blocks))]).sum() for _ in range(5000)])
    print('%-10s diff vs %s: total %+d, per-day sd %.0f, iid bootstrap P(diff>0) %.3f, 95%% CI [%+.0f, %+.0f]; 5-day block P(diff>0) %.3f'
          % ('', better, diff.sum(), diff.std(ddof=1), (bs > 0).mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), (bsb > 0).mean()))
    results[nm] = sc

# exploratory sensitivity: thr +-10 % of selection count (not pre-registered)
for kk in (int(k * 0.8), int(k * 1.2)):
    t2 = np.sort(p_des)[::-1][kk - 1]
    for nm, d, lo, hi in [('real_h2', real, '2026-09-01', '2026-11-11'), ('unseen', U, '2025-11-03', '2026-05-11')]:
        dd_ = d[(d.day >= lo) & (d.day <= hi)]
        sc, _ = st(my_pick(dd_, 'pc', t2), 'opt_T3', sorted(dd_.day.unique()))
        print('SENS k=%d thr %.5f %-8s n %d opt net %+d worst %+d maxDD %+d' % (kk, t2, nm, sc['n'], sc['net'], sc['worst'], sc['maxdd']))
