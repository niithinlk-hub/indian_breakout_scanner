# Fit (1) IV from the stock's own volatility and option type, (2) intraday time-decay speed, on the real legs.
import sys, numpy as np, pandas as pd
sys.path.insert(0, sys.argv[1] + '/v2/patched')
from scipy.optimize import brentq
from b76 import price
from scanner.equity import costs as C
d = pd.read_pickle('legs_iv.pkl')
ok = d.iv0.notna() & (d.stale.fillna(0) <= 5)
x = d[ok & (d.pol == 'T1')].drop_duplicates(['day', 'time', 'symbol'])
rv = x.atr_pct * np.sqrt(252) / 100 / 1.25
A = np.column_stack([np.ones(len(x)), np.log(rv), (x.kind == 'PE').astype(float)])
c = np.linalg.lstsq(A, np.log(x.iv0), rcond=None)[0]
res = np.log(x.iv0) - A @ c
print('log IV = %.3f + %.3f log(rv) + %.3f PE ; R2 %.2f; resid sd %.3f' % (c[0], c[1], c[2], 1 - res.var() / np.log(x.iv0).var(), res.std()))
np.save('ivfit2.npy', c)
d['mins'] = (pd.to_datetime(d.o_exit_ts) - pd.to_datetime(d.o_entry_ts)).dt.total_seconds() / 60


def model_net(dd, m, use_iv='iv0'):
    out = []
    for r in dd.itertuples():
        s = getattr(r, use_iv)
        p0 = price(r.f_entry, r.strike, r.T0, s, r.kind)
        p1 = price(r.f_exit, r.strike, max(r.T0 - m * r.mins / 525600, 1e-6), s, r.kind)
        q = r.lot * r.lots
        out.append(q * (p1 - p0) - C.round_trip('OPT', p0, p1, q, 'LONG') - C.slippage(p0, p1, q, 0.25))
    return np.array(out)


dk = d[ok]
real_net = dk.o_net.sum()
f = lambda m: model_net(dk, m).sum() - real_net
for m in (1, 2, 3, 5):
    print('decay x%.0f calendar: model net %+.0f vs real %+.0f' % (m, model_net(dk, m).sum(), real_net))
m = brentq(f, 0.2, 20)
print('decay multiplier fitted: %.2f (x calendar time)' % m)
np.save('decay.npy', np.array([m]))
rvd = dk.atr_pct * np.sqrt(252) / 100 / 1.25
dk = dk.assign(ivf=np.exp(c[0] + c[1] * np.log(rvd) + c[2] * (dk.kind == 'PE')))
for lab, col in (('actual entry IV', 'iv0'), ('fitted IV (what history gets)', 'ivf')):
    mn = model_net(dk, m, col)
    print('\n%s: corr with real per leg %.3f' % (lab, np.corrcoef(mn, dk.o_net)[0, 1]))
    g = pd.DataFrame({'pol': dk.pol, 'model': mn, 'real': dk.o_net}).groupby('pol').sum().round(0)
    g['fut'] = dk.groupby('pol').f_net.sum().round(0)
    print(g.to_string())
