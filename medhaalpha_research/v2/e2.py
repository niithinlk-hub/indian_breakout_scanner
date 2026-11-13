# Experiment 2 (design period only): the two-score blend w x Opus + (1 - w) x Fable-OP, exact inputs.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
D = df[df.design].copy()
months = sorted(D.month.unique())
target = len(live_df(D, 't_opus', 75))


def bym(idx):
    t = D.loc[idx]
    return ' '.join('%d:%d%%/%+dk' % (len(g), 100 * g.hit.mean(), g.net1.sum() / 1000) for mo, g in t.groupby('month'))


print(line('Opus >= 75', stat(D, live_df(D, 't_opus', 75)))[:150], '|', bym(live_df(D, 't_opus', 75)))
for w in (0.3, 0.4, 0.5, 0.6, 0.7):
    D['_b'] = w * D.t_opus + (1 - w) * D.t_fable_op
    t0 = thr_for(D, '_b', target)
    for dt in (-2, -1, 0, 1, 2, 4):
        idx = live_df(D, '_b', t0 + dt)
        print(line('w_opus %.1f thr %.1f' % (w, t0 + dt), stat(D, idx))[:150], '|', bym(idx))
    print()
D['_b'] = 0.5 * D.t_opus + 0.5 * D.t_fable_op
t0 = thr_for(D, '_b', target)
idx = live_df(D, '_b', t0)
t = D.loc[idx]
print('equal blend thr %.1f: by side' % t0)
for s, g in t.groupby('side'):
    print('   %-5s n=%3d hit %.1f%% stop %.1f%% T1 %+d' % (s, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()))
o = D.loc[live_df(D, 't_opus', 75)]
for s, g in o.groupby('side'):
    print('   Opus %-5s n=%3d hit %.1f%% stop %.1f%% T1 %+d' % (s, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()))
print('entry time, equal blend:', t.time.lt('09:31').sum(), 'by 09:30,', t.time.between('09:31', '11:00').sum(), '09:31-11:00,', t.time.gt('11:00').sum(), 'after 11:00 | Opus:',
      o.time.lt('09:31').sum(), o.time.between('09:31', '11:00').sum(), o.time.gt('11:00').sum())
print('overlap with Opus trades:', len(set(idx) & set(o.index)), 'of', len(idx))
for n in (4, 5, 6, 8):
    print(line('equal blend thr %.1f cap %d' % (t0, n), stat(D, live_df(D, '_b', t0, n)))[:150])
