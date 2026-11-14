# Option levers on the two baselines' own picks: exit policy x strike x expiry (lots as the scanner sizes them).
# Choice made on the design window (real 12 May - 31 Aug) only; then shown on real 2nd half, unseen, known.
import sys, itertools, json
import numpy as np, pandas as pd
import harness as H
D = H.load_all()
H1, H2 = ('2026-05-12', '2026-08-31'), ('2026-09-01', '2026-11-11')
rows = []
for model, col in (('v3', 's_opus_v3'), ('FOP', 's_fable_op')):
    picks = {s: H.pick(D[s], col, 75) for s in D}
    for pol, k, ex in itertools.product(H.POL, (-1.0, 0.0, 1.0, 2.0), ('std', 'next')):
        r = {'model': model, 'pol': pol, 'strike': k, 'expiry': ex}
        for s, t in picks.items():
            det = H.option_net(t, pol, strike_pct=k, expiry=ex, detail=True)
            net = det.net
            if s == 'real':
                r['design'] = net[(t.day >= H1[0]) & (t.day <= H1[1])].sum()
                r['real_h2'] = net[(t.day >= H2[0])].sum()
                r['outlay_med'] = det.outlay.median()
            r[s] = net.sum()
            byday = net.groupby(t.day).sum()
            r[s + '_worst'] = byday.min()
        rows.append(r)
G = pd.DataFrame(rows)
pd.set_option('display.width', 250)
fmt = lambda g: g[['model', 'pol', 'strike', 'expiry', 'design', 'real_h2', 'unseen', 'known', 'real', 'unseen_worst', 'outlay_med']].round(0).to_string(index=False)
for m in ('v3', 'FOP'):
    g = G[G.model == m].sort_values('design', ascending=False)
    print('\n== %s: top 12 settings by DESIGN-window option net (then their results elsewhere)' % m)
    print(fmt(g.head(12)))
    print('-- scanner default (ATM, std expiry): ')
    print(fmt(g[(g.strike == 0) & (g.expiry == 'std')].sort_values('design', ascending=False)))
G.to_pickle('_mine/optgrid.pkl')
