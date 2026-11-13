# The unseen check. Candidates were fixed on 12 May - 31 Aug before this file was first run.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()


def side_aware(d, w, tl, ts=75.0):
    return np.where(d.long == 1, w * d.t_opus + (1 - w) * d.t_fable_op + (75.0 - tl), d.t_opus + (75.0 - ts))


df['opus'] = df.t_opus
df['fable_op'] = df.t_fable_op
df['v2'] = side_aware(df, 0.5, 70.0)                       # primary
df['v2b'] = 0.5 * df.t_opus + 0.5 * df.t_fable_op + (75 - 68.1)   # equal blend, both sides
df['v2c'] = side_aware(df, 0.25, 71.0)                     # more Fable-OP weight on longs
CANDS = (('Opus >= 75 (now)', 'opus'), ('Fable-OP >= 75 (now)', 'fable_op'), ('V2 primary: side-aware 0.5', 'v2'), ('V2b: equal blend both sides', 'v2b'), ('V2c: side-aware 0.25', 'v2c'))
for name, mask in (('DESIGN 12 May - 31 Aug (78 sessions)', df.design), ('UNSEEN 1 Sep - 11 Nov (48 sessions)', df.unseen)):
    P = df[mask]
    print('==', name, '| signals', len(P))
    for lab, col in CANDS:
        idx = live_df(P, col, 75)
        print(line(lab, stat(P, idx)))
    print()
U = df[df.unseen]
print('== UNSEEN by month: trades : hit% / T1 net')
for lab, col in CANDS:
    t = U.loc[live_df(U, col, 75)]
    print('%-30s' % lab, ' | '.join('%s %3d: %2.0f%% / %+7.0f' % (mo, len(g), 100 * g.hit.mean(), g.net1.sum()) for mo, g in t.groupby('month')))
print('\n== UNSEEN by side')
for lab, col in CANDS:
    t = U.loc[live_df(U, col, 75)]
    print('%-30s' % lab, ' | '.join('%s n=%3d hit %4.1f%% stop %4.1f%% T1 %+7.0f' % (s, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()) for s, g in t.groupby('side')))
o, v = set(live_df(U, 'opus', 75)), set(live_df(U, 'v2', 75))
print('\nUNSEEN: V2 trades also taken by Opus: %d of %d | days with no trade: Opus %d, V2 %d, Fable-OP %d of %d' % (
    len(o & v), len(v), U.day.nunique() - U.loc[list(o)].day.nunique(), U.day.nunique() - U.loc[list(v)].day.nunique(),
    U.day.nunique() - U.loc[live_df(U, 'fable_op', 75)].day.nunique(), 48))
