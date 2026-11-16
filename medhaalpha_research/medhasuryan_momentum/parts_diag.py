# Diagnostic only (not a selection): MedhaSuryan plus 20 % of ONE momentum part at a time (part scaled to 0-100),
# cutoff matched from scores to MedhaSuryan's 160 design-window trades. Shows which ingredient helps or hurts.
import json, os, sys
import numpy as np, pandas as pd
RP, OUT = sys.argv[1], sys.argv[2]
os.environ['MEDHA_SP'] = RP
sys.path.insert(0, RP + '/hunt'); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import harness as H, heldsim as HS, momscore as M
D = H.load_all()
DT = HS.Data(RP)
W = 0.20
des = D['real'][D['real'].day <= '2026-08-31']


def score(df, part):
    base = M.medhasuryan(df)
    if part is None:
        return base
    p = M.momentum_parts(df)
    x = p[part] * 100 if part != 'all' else M.momentum_score(df)
    return (1 - W) * base + W * x


def cut_for(part):
    if part is None:
        return 75.0
    sc = score(des, part)
    cuts = np.arange(60, 85.01, 0.5)
    n = np.array([len(H.pick(des, sc, c, 6)) for c in cuts])
    return float(cuts[int(np.argmin(abs(n - 160)))])


SL = {'test Sep-Nov 2026': ('real', '2026-09-01', '2026-11-11'), 'test Nov 2025-May 2026': ('unseen', '2025-11-03', '2026-05-11')}
out = {}
print('%-26s %6s | %s' % ('variant', 'cut', ' | '.join('%-34s' % k for k in SL)))
for part in (None, 'all', 'rs', 'trend20', 'breadth', 'volume'):
    c = cut_for(part)
    row = {}
    for k, (s, lo, hi) in SL.items():
        d = D[s][(D[s].day >= lo) & (D[s].day <= hi)]
        t = H.pick(d, score(d, part), c, 6)
        pol = np.where(t.regime == 'Downtrend', 'T1', 'T3')
        opt = sum(t.at[i, 'opt_' + p] for i, p in zip(t.index, pol))
        fut = sum(t.at[i, 'net_' + p] for i, p in zip(t.index, pol))
        hl = 0.0
        for i, p in zip(t.index, pol):
            g = HS.held_trade(DT, d.loc[i], s, pols=(p,))
            hl += g[p]['net'] if g else 0.0
        row[k] = {'n': len(t), 'opt': round(opt), 'fut': round(fut), 'held': round(hl)}
    name = 'MedhaSuryan (as is)' if part is None else '+20% momentum (S1 mix)' if part == 'all' else '+20% ' + part + ' only'
    out[name] = {'cut': c, **row}
    print('%-26s %6.1f | %s' % (name, c, ' | '.join('n %3d opt %+8d fut %+8d held %+8d' % (r['n'], r['opt'], r['fut'], r['held']) for r in row.values())))
json.dump(out, open(OUT, 'w'), indent=1)
