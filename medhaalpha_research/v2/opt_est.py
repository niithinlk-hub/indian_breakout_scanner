# Six-month option estimate. Real option prices exist only for 21 Oct - 13 Nov, so each six-month futures result is converted
# with the share of the futures result that the option leg kept in that period, by how the futures leg ended. An estimate.
import sys, json, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from base import SP, PI
from frame import load
from lab import *
import pickle
D = json.load(open(SP + '/v2/opt5.json'))
cal = {}
for pol in ('T1', 'T3'):
    cal[pol] = [(r['fut_same'][pol]['status'], r['fut_same'][pol]['net_rs'], r['same'][pol]['net_rs']) for r in D['rows'] if pol in r['same']]


def cls(status, net):
    return status if status in ('target', 'stopped') else ('close_up' if net > 0 else 'close_dn')


def ratios(sample):
    out = {}
    for c in ('target', 'stopped', 'close_up', 'close_dn'):
        g = [(a, b) for s, a, b in sample if cls(s, a) == c]
        out[c] = sum(b for _, b in g) / sum(a for a, _ in g) if g and abs(sum(a for a, _ in g)) > 1 else 0.5
    return out


R = {pol: ratios(cal[pol]) for pol in ('T1', 'T3')}
print('share of the futures result kept by the option:', {p: {k: round(v, 2) for k, v in R[p].items()} for p in R})
df = load()
rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
A = df[df.design | df.unseen].copy()
A['r3'] = [rows[df.index.get_loc(i)]['r'][PI['T3']] for i in A.index]
lg = A.long == 1
A['opus'], A['fable'], A['fable_op'] = A.t_opus, A.t_fable - 5.0, A.t_fable_op
A['v2'] = np.where(lg, A.t_fable_op, A.t_opus)
A['v3'] = np.where(lg, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), A.t_opus)
A['c1'] = np.where(A.out == 'hit', 'target', np.where(A.out == 'stop', 'stopped', np.where(A.net1 > 0, 'close_up', 'close_dn')))
A['c3'] = np.where(A.r3 >= 2.3, 'target', np.where(A.r3 <= -0.97, 'stopped', np.where(A.net3 > 0, 'close_up', 'close_dn')))
SC = (('opus', 'T1', 'Opus, exit T1'), ('v2', 'T1', 'Opus v2, exit T1'), ('v3', 'T1', 'Opus v3, exit T1'), ('fable', 'T3', 'Fable, exit T3'), ('fable_op', 'T3', 'Fable-OP, exit T3'))
rng = np.random.default_rng(5)
boot = {pol: [ratios([cal[pol][i] for i in rng.integers(0, len(cal[pol]), len(cal[pol]))]) for _ in range(4000)] for pol in ('T1', 'T3')}
out = {'ratios': R}
months = sorted(A.month.unique())
for col, pol, name in SC:
    t = A.loc[live_df(A, col, 75)]
    net, c = (t.net1, t.c1) if pol == 'T1' else (t.net3, t.c3)
    bycls = net.groupby(c).sum()
    est = sum(R[pol][k] * bycls.get(k, 0.0) for k in R[pol])
    sims = sorted(sum(b[k] * bycls.get(k, 0.0) for k in b) for b in boot[pol])
    opt_trade = pd.Series([R[pol][k] for k in c], index=t.index) * net
    bym = opt_trade.groupby(t.month).sum()
    byday = opt_trade.groupby(t.day).sum()
    eq = byday.cumsum()
    out[col] = {'n': len(t), 'fut': float(net.sum()), 'est': float(est), 'p5': float(sims[200]), 'p95': float(sims[3800]), 'bycls_n': c.value_counts().to_dict(),
                'bym': {m: float(bym.get(m, 0.0)) for m in months}, 'won': int((net > 0).sum()), 'maxdd': float((eq - eq.cummax().clip(lower=0)).min()),
                'h1': float(opt_trade[t.design].sum()), 'h2': float(opt_trade[t.unseen].sum()), 'months_up': int((bym > 0).sum())}
    o = out[col]
    print('%-18s trades %3d | futures %+9.0f | options est %+9.0f (range %+9.0f to %+9.0f) | %s | by month %s' % (
        name, o['n'], o['fut'], o['est'], o['p5'], o['p95'], o['bycls_n'], ' '.join('%+.0f' % (o['bym'][m] / 1000) for m in months)))
# how well the same conversion reproduces the period where real option prices exist
print('\ncheck on 21 Oct - 13 Nov, same day: converted futures result against the real option result')
S = json.load(open(SP + '/v2/opt_sum.json'))
for m, pol, name in (('opus', 'T1', 'Opus T1'), ('opus_v2', 'T1', 'v2 T1'), ('opus_v3', 'T1', 'v3 T1'), ('fable', 'T3', 'Fable T3'), ('fable_op', 'T3', 'Fable-OP T3')):
    x = [r for r in D['rows'] if m in r['models'] and pol in r['same']]
    est = sum(R[pol][cls(r['fut_same'][pol]['status'], r['fut_same'][pol]['net_rs'])] * r['fut_same'][pol]['net_rs'] for r in x)
    print('  %-12s converted %+8.0f | real %+8.0f' % (name, est, sum(r['same'][pol]['net_rs'] for r in x)))
json.dump(out, open(SP + '/v2/opt_est.json', 'w'))
