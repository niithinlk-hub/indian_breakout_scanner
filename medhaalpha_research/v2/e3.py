# Experiment 3 (design period only): each side on its own. w x Opus + (1 - w) x Fable-OP, live rule within the side.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
D = df[df.design].copy()


def bym(S, idx):
    t = S.loc[idx]
    return ' '.join('%d:%d%%/%+dk' % (len(g), 100 * g.hit.mean(), g.net1.sum() / 1000) for mo, g in t.groupby('month'))


for side in ('LONG', 'SHORT'):
    S = D[D.side == side].copy()
    print('==', side, 'signals', len(S), '| base hit %.1f%% stop %.1f%% net/trade %+.0f' % (100 * S.hit.mean(), 100 * S['stop'].mean(), S.net1.mean()))
    for w in (1.0, 0.75, 0.5, 0.25, 0.0):
        S['_b'] = w * S.t_opus + (1 - w) * S.t_fable_op
        for target in ((60, 100, 140, 180) if side == 'LONG' else (40, 60, 75, 100)):
            thr = thr_for(S, '_b', target)
            idx = live_df(S, '_b', thr)
            s = stat(S, idx)
            print('  w_opus %.2f thr %5.1f n=%3d hit %5.1f%% stop %5.1f%% won %5.1f%% T1 %+8d (%+5d/trade) T2 %+8d T3 %+8d | %s' % (
                w, thr, s['n'], s['hit%'], s['stop%'], s['won%'], s['T1'], s['per'], s['T2'], s['T3'], bym(S, idx)))
        print()
