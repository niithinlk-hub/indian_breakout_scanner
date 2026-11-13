# Can cash-share data stand in for the real futures? First check, on the six known months: keep the scanner's real signals and
# real outcomes, but pick the trades with scores rebuilt from cash candles instead of the scanner's own (futures) scores.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
lg = A.long == 1
gate = A.rel_vol < 1.0
for tag, o, f in (('true', A.t_opus, A.t_fable_op), ('cash', A.c_opus, A.c_fable_op)):
    A['opus_' + tag] = o
    A['fop_' + tag] = f
    A['v2_' + tag] = np.where(lg, f, o)
    A['v3_' + tag] = np.where(lg, np.where(gate, 0.0, f), o)
for per, mask in (('ALL 126 sessions', A.day > ''), ('12 May - 31 Aug', A.design), ('1 Sep - 11 Nov', A.unseen)):
    P = A[mask]
    print('==', per)
    for m, name in (('opus', 'Opus'), ('fop', 'Fable-OP'), ('v2', 'Opus v2'), ('v3', 'Opus v3')):
        a, b = live_df(P, m + '_true', 75), live_df(P, m + '_cash', 75)
        sa, sb = stat(P, a), stat(P, b)
        print('  %-9s real scores: n=%3d hit %4.1f%% stop %4.1f%% T1 %+8d | cash scores: n=%3d hit %4.1f%% stop %4.1f%% T1 %+8d | same trades %3d' % (
            name, sa['n'], sa['hit%'], sa['stop%'], sa['T1'], sb['n'], sb['hit%'], sb['stop%'], sb['T1'], len(set(a) & set(b))))
print('\nby side with cash scores, all six months:')
for m, name in (('opus', 'Opus'), ('fop', 'Fable-OP'), ('v3', 'Opus v3')):
    t = A.loc[live_df(A, m + '_cash', 75)]
    print('  %-9s' % name, ' | '.join('%s n=%3d hit %4.1f%% stop %4.1f%% net %+8.0f' % (s, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()) for s, g in t.groupby('side')))
t = A[(A.long == 1)]
for tag in ('t_fable_op', 'c_fable_op'):
    q = t[t[tag] >= 75]
    print('longs with %s >= 75: n=%d | rel_vol < 1: n=%d hit %.0f%% stop %.0f%% net/trade %+.0f | rel_vol >= 1: n=%d hit %.0f%% stop %.0f%% net/trade %+.0f' % (
        tag, len(q), (q.rel_vol < 1).sum(), 100 * q[q.rel_vol < 1].hit.mean(), 100 * q[q.rel_vol < 1]['stop'].mean(), q[q.rel_vol < 1].net1.mean(),
        (q.rel_vol >= 1).sum(), 100 * q[q.rel_vol >= 1].hit.mean(), 100 * q[q.rel_vol >= 1]['stop'].mean(), q[q.rel_vol >= 1].net1.mean()))
