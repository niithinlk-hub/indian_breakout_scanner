# Opus v3 = Opus v2 with one gate: a long also needs relative volume >= 1 (volume so far at least normal for that time of day).
import sys, warnings, json, glob
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from base import SP
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
lg = A.long == 1
A['opus'], A['fable'], A['fable_op'] = A.t_opus, A.t_fable - 5.0, A.t_fable_op
A['v2'] = np.where(lg, A.t_fable_op, A.t_opus)
A['v3'] = np.where(lg, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), A.t_opus)
A['v3s'] = np.where(lg, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), np.maximum(A.t_opus, A.t_fable_op))
C = (('Opus', 'opus'), ('Fable', 'fable'), ('Fable-OP', 'fable_op'), ('Opus v2', 'v2'), ('Opus v3', 'v3'), ('v3 + Fable-OP shorts', 'v3s'))
out = {}
for per, mask in (('all', A.day > ''), ('h1', A.design), ('h2', A.unseen)):
    P = A[mask]
    print('==', per)
    for name, col in C:
        s = stat(P, live_df(P, col, 75))
        out['%s|%s' % (per, col)] = s
        print(line(name, s)[:176])
picks = {col: A.loc[live_df(A, col, 75)] for _, col in C}
print('\n== by month: trades:hit%:stop%/net k')
bym = {}
for name, col in C:
    t = picks[col]
    bym[col] = {mo: [len(g), round(100 * g.hit.mean(), 1), round(100 * g['stop'].mean(), 1), round(g.net1.sum())] for mo, g in t.groupby('month')}
    if col in ('opus', 'v2', 'v3'):
        print('%-10s' % name, ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0f' % (mo[5:], *v[:3], v[3] / 1000) for mo, v in bym[col].items()))
out['bym'] = bym
print('\n== by side, six months')
side = {}
for name, col in C:
    t = picks[col]
    side[col] = {s: [len(g), round(100 * g.hit.mean(), 1), round(100 * g['stop'].mean(), 1), round(g.net1.sum())] for s, g in t.groupby('side')}
    print('%-22s' % name, ' | '.join('%s n=%3d hit %4.1f%% stop %4.1f%% net %+7.0f' % (s, *v) for s, v in side[col].items()))
out['side'] = side
days = sorted(A.day.unique())
rng = np.random.default_rng(11)
ix = rng.integers(0, len(days), size=(20000, len(days)))


def daily(t):
    return (t.groupby('day').net1.sum().reindex(days).fillna(0).to_numpy(), t.groupby('day').hit.sum().reindex(days).fillna(0).to_numpy(),
            t.groupby('day')['stop'].sum().reindex(days).fillna(0).to_numpy(), t.groupby('day').size().reindex(days).fillna(0).to_numpy())


out['boot'] = {}
for a, b in (('v3', 'v2'), ('v3', 'opus'), ('v3', 'fable_op')):
    na, ha, sa, ca = daily(picks[a]); nb, hb, sb, cb = daily(picks[b])
    dn = (na - nb)[ix].sum(axis=1)
    dh = ha[ix].sum(axis=1) / ca[ix].sum(axis=1) - hb[ix].sum(axis=1) / cb[ix].sum(axis=1)
    ds = sa[ix].sum(axis=1) / ca[ix].sum(axis=1) - sb[ix].sum(axis=1) / cb[ix].sum(axis=1)
    out['boot']['%s-%s' % (a, b)] = {'net': float((na - nb).sum()), 'net_p5': float(np.percentile(dn, 5)), 'net_p95': float(np.percentile(dn, 95)), 'net_pos': float(100 * (dn > 0).mean()),
                                     'hit': float(100 * (ha.sum() / ca.sum() - hb.sum() / cb.sum())), 'hit_pos': float(100 * (dh > 0).mean()),
                                     'stop': float(100 * (sa.sum() / ca.sum() - sb.sum() / cb.sum())), 'stop_neg': float(100 * (ds < 0).mean())}
    o = out['boot']['%s-%s' % (a, b)]
    print('%s minus %s: net %+.0f (5-95%%: %+.0f to %+.0f, higher in %.0f%%) | reach-T1 %+.1f pts (higher in %.0f%%) | stop-outs %+.1f pts (lower in %.0f%%)' % (
        a, b, o['net'], o['net_p5'], o['net_p95'], o['net_pos'], o['hit'], o['hit_pos'], o['stop'], o['stop_neg']))
d = picks['v2'].index.difference(picks['v3'].index)
n = picks['v3'].index.difference(picks['v2'].index)
print('\nv2 trades dropped by v3: %d (hit %.0f%%, stop %.0f%%, net %+.0f) | trades v3 takes instead: %d (hit %.0f%%, stop %.0f%%, net %+.0f)' % (
    len(d), 100 * A.loc[d].hit.mean(), 100 * A.loc[d]['stop'].mean(), A.loc[d].net1.sum(), len(n), 100 * A.loc[n].hit.mean(), 100 * A.loc[n]['stop'].mean(), A.loc[n].net1.sum()))
print('rel-vol cut sensitivity (six months): ' + ' | '.join('%.2f: n=%d hit %.1f stop %.1f net %+.0fk' % (
    rv, *[(lambda s: (s['n'], s['hit%'], s['stop%'], s['T1'] / 1000))(stat(A, live_df(A.assign(_x=np.where(lg, np.where(A.rel_vol < rv, 0.0, A.t_fable_op), A.t_opus)), '_x', 75)))][0]) for rv in (0.6, 0.8, 1.0, 1.2, 1.5, 2.0)))
json.dump(out, open(SP + '/v2/f7.json', 'w'))
json.dump([[A.day[i], A.symbol[i], A.setup[i], A.time[i]] for i in picks['v3'].index], open(SP + '/v2/v3_picks.json', 'w'))
