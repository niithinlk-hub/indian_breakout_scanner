# Experiment 5 (design period only): the side-aware candidate. Longs: w x Opus + (1 - w) x Fable-OP >= T_L. Shorts: Opus >= 75.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
D = df[df.design].copy()
D['tb'] = pd.cut(D.minutes_since_open, [0, 15, 45, 105, 165, 400], labels=['-09:30', '-10:00', '-11:00', '-12:00', '12:00+'])
target = len(live_df(D, 't_opus', 75))


def v2(d, w, tl, ts=75.0):
    """One score on Opus's scale: 75 is the cut for both sides."""
    return np.where(d.long == 1, w * d.t_opus + (1 - w) * d.t_fable_op + (75.0 - tl), d.t_opus + (75.0 - ts))


def bym(idx):
    return ' '.join('%d:%d%%/%+dk' % (len(g), 100 * g.hit.mean(), g.net1.sum() / 1000) for mo, g in D.loc[idx].groupby('month'))


print(line('Opus >= 75', stat(D, live_df(D, 't_opus', 75)))[:150], '|', bym(live_df(D, 't_opus', 75)))
for w in (0.5, 0.25, 0.0):
    for tl in np.arange(66, 76.01, 1.0):
        D['_v'] = v2(D, w, tl)
        idx = live_df(D, '_v', 75)
        s = stat(D, idx)
        print(line('longs w_opus %.2f T_L %.0f' % (w, tl), s)[:150], '|', bym(idx))
    print()
D['_v'] = v2(D, 0.5, 70.0)
idx = live_df(D, '_v', 75)
t = D.loc[idx]
for side, g in t.groupby('side'):
    print('  %-5s n=%3d hit %.1f%% stop %.1f%% T1 %+d' % (side, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()), '| by time:',
          ' | '.join('%s n%d hit %.0f net %+dk' % (i, len(x), 100 * x.hit.mean(), x.net1.sum() / 1000) for i, x in g.groupby('tb', observed=True)))
