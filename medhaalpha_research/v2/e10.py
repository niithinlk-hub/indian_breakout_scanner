import sys, warnings, json
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
A['opus'], A['fable_op'] = A.t_opus, A.t_fable_op
print('== cut sensitivity, all 126 sessions (rows: long cut on Fable-OP; columns: short cut on Opus): trades / hit% / T1 net in Rs thousand')
print('          ' + ''.join('S>=%-14d' % s for s in (72, 75, 78, 80)))
grid = {}
for tl in (70, 72, 75, 78, 80):
    cells = []
    for ts in (72, 75, 78, 80):
        A['_v'] = np.where(A.long == 1, A.t_fable_op + (75 - tl), A.t_opus + (75 - ts))
        s = stat(A, live_df(A, '_v', 75))
        grid['%d|%d' % (tl, ts)] = s
        cells.append('%3d/%4.1f/%+4.0f   ' % (s['n'], s['hit%'], s['T1'] / 1000))
    print('L>=%-5d  ' % tl + ''.join(cells))
A['split'] = np.where(A.long == 1, A.t_fable_op, A.t_opus)
out = {'grid': grid}
print('\n== extra slippage on entries in the first 15 minutes (assumed turnover Rs 13 lakh a trade)')
for lab, col in (('Opus', 'opus'), ('Fable-OP', 'fable_op'), ('Split', 'split')):
    t = A.loc[live_df(A, col, 75)]
    early = int((t.time <= '09:30').sum())
    row = {'n': len(t), 'early': early, 'base': float(t.net1.sum())}
    for extra_pct in (0.03, 0.08):
        row['slip_%g' % (0.02 + extra_pct)] = float(t.net1.sum() - early * 1300000 * extra_pct / 100)
    out['slip|' + col] = row
    print('%-9s trades %3d, entered by 09:30: %3d | T1 net as costed %+8.0f | at 0.05%% a side on early entries %+8.0f | at 0.10%% %+8.0f' % (
        lab, len(t), early, row['base'], row['slip_0.05'], row['slip_0.1']))
print('\n== split: by entry time, all 126 sessions')
t = A.loc[live_df(A, 'split', 75)].copy()
t['tb'] = pd.cut(t.minutes_since_open, [0, 15, 45, 105, 165, 400], labels=['by 09:30', '09:31-10:00', '10:01-11:00', '11:01-12:00', 'after 12:00'])
for side, g in t.groupby('side'):
    print('  %-5s' % side, ' | '.join('%s n%d hit %.0f%% stop %.0f%% net %+dk' % (i, len(x), 100 * x.hit.mean(), 100 * x['stop'].mean(), x.net1.sum() / 1000) for i, x in g.groupby('tb', observed=True)))
print('\n== exploratory only (not part of the candidate): Opus short picks split at the DESIGN-period median of Nifty\'s fall and of earlier same-day short signals')
O = A.loc[live_df(A, 'opus', 75)]
S = O[O.side == 'SHORT']
for f in ('nifty_dir', 'crowd_same'):
    med = S[S.design][f].median()
    for per, m in (('design', S.design), ('unseen', S.unseen)):
        g = S[m]
        lo, hi = g[g[f] <= med], g[g[f] > med]
        print('  %-10s %-6s cut %.2f | at or below: n=%2d hit %2.0f%% stop %2.0f%% net %+7.0f | above: n=%2d hit %2.0f%% stop %2.0f%% net %+7.0f' % (
            f, per, med, len(lo), 100 * lo.hit.mean(), 100 * lo['stop'].mean(), lo.net1.sum(), len(hi), 100 * hi.hit.mean(), 100 * hi['stop'].mean(), hi.net1.sum()))
json.dump(out, open(sys.argv[1] + '/v2/e10.json', 'w'))
