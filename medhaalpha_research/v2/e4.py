# Experiment 4 (design period only): entry time and short-side context, for all signals and for Opus's own picks.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
D = df[df.design].copy()
D['tb'] = pd.cut(D.minutes_since_open, [0, 15, 45, 105, 165, 225, 400], labels=['-09:30', '-10:00', '-11:00', '-12:00', '-13:00', '13:00+'])
O = D.loc[live_df(D, 't_opus', 75)]


def tab(g, by):
    t = g.groupby(by, observed=True).agg(n=('hit', 'size'), hit=('hit', 'mean'), stop=('stop', 'mean'), r=('r1', 'mean'), net=('net1', 'sum'), rc=('rc', 'mean'))
    return ' | '.join('%s n%d hit %.0f stop %.0f R %+.2f net %+dk' % (i, r.n, 100 * r.hit, 100 * r['stop'], r.r, r.net / 1000) for i, r in t.iterrows())


for side in ('LONG', 'SHORT'):
    print('==', side)
    print('all signals by entry time :', tab(D[D.side == side], 'tb'))
    print('Opus >= 75 picks by time  :', tab(O[O.side == side], 'tb'))
S = O[O.side == 'SHORT'].copy()
print('\nOpus short picks (n=%d) split at the median of:' % len(S))
for f in ('nifty_dir', 'crowd_same', 'breadth_dir', 'gap_atr', 't_fable_op', 'rel_vol', 'open_atr', 'vwap_atr'):
    S['_h'] = (S[f] > S[f].median()).map({False: 'low', True: 'high'})
    signs = ''.join('+' if g[g._h == 'high'].net1.mean() > g[g._h == 'low'].net1.mean() else '-' for mo, g in S.groupby('month'))
    print('  %-12s %s | high better by month: %s' % (f, tab(S, '_h'), signs))
L = O[O.side == 'LONG'].copy()
print('\nOpus long picks (n=%d) split at the median of:' % len(L))
for f in ('nifty_dir', 'crowd_same', 'gap_atr', 't_fable_op', 'rel_vol', 'open_atr', 'vwap_atr', 'move_atr'):
    L['_h'] = (L[f] > L[f].median()).map({False: 'low', True: 'high'})
    signs = ''.join('+' if g[g._h == 'high'].net1.mean() > g[g._h == 'low'].net1.mean() else '-' for mo, g in L.groupby('month'))
    print('  %-12s %s | high better by month: %s' % (f, tab(L, '_h'), signs))
