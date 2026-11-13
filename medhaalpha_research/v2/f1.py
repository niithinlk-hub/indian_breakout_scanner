# Six-month check of Opus v2, and where its stop-outs sit. All 126 sessions, 12 May - 11 Nov 2026.
import sys, warnings, math
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
A['opus'], A['fable'], A['fable_op'] = A.t_opus, A.t_fable - 5.0, A.t_fable_op          # fable's own cut is 80
A['v2'] = np.where(A.long == 1, A.t_fable_op, A.t_opus)
print('== six months, live rule, same-day exit at T1')
for lab, col in (('Opus', 'opus'), ('Fable', 'fable'), ('Fable-OP', 'fable_op'), ('Opus v2', 'v2')):
    print(line(lab, stat(A, live_df(A, col, 75))))
# exact pieces that can be backed out of the stored scores
early = (1 - np.log(A.minutes_since_open.clip(lower=5) / 5) / math.log(180 / 5)).clip(0, 1)
ext = np.where(A.long == 1, 1 + A.from_52w_high / 25, 1 - A.from_52w_low / 25).clip(0, 1)
A['fable_tight'] = (A.t_fable - 100 / 3 * early - 100 / 3 * ext).round(1)                 # 33.3 = stop <= 1 % away, 0 = stop >= 2 % away
A['risk_true'] = 2 - A.fable_tight / (100 / 3)                                            # stop distance %, known only inside 1-2 %
A['stop_atr_true'] = A.risk_true / A.atr_pct
print('fable tight part backed out: min %.1f max %.1f | share at the 33.3 cap %.0f%% | share at 0 %.0f%%' % (A.fable_tight.min(), A.fable_tight.max(), 100 * (A.fable_tight > 33.2).mean(), 100 * (A.fable_tight < 0.1).mean()))
V = A.loc[live_df(A, 'v2', 75)].copy()
V['half'] = np.where(V.design, 'H1', 'H2')
print('\nv2 picks:', len(V), '| longs', int(V.long.sum()), '| by half:', V.groupby('half').size().to_dict())
feats = ['minutes_since_open', 't_opus', 't_fable', 't_fable_op', 'fable_tight', 'stop_atr_true', 'risk_atr', 'rel_vol', 'n_break', 'rsi_room', 'vs20_dir', 'ret5_dir', 'ret20_dir', 'atr_pct', 'ext52',
         'nifty_dir', 'breadth_dir', 'crowd_same', 'crowd_all', 'same_minute', 'gap_atr', 'move_atr', 'open_atr', 'vwap_atr', 'pos', 'range_atr', 'beyond_pd']
for side in ('LONG', 'SHORT'):
    g = V[V.side == side]
    print('\n== v2 %s picks n=%d: hit %.1f%% stop %.1f%% net %+.0f | thirds low/mid/high: hit%% | stop%% | net Rs k ; then (hit-stop) high minus low in H1, H2' % (side, len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum()))
    for f in feats:
        x = g[f]
        if x.nunique() < 3:
            continue
        q = pd.qcut(x.rank(method='first'), 3, labels=False)
        t = g.groupby(q).agg(hit=('hit', 'mean'), stop=('stop', 'mean'), net=('net1', 'sum'), lo=(f, 'min'))
        d = []
        for h in ('H1', 'H2'):
            gh = g[g.half == h]
            qh = pd.qcut(gh[f].rank(method='first'), 3, labels=False)
            e = gh.groupby(qh).apply(lambda z: z.hit.mean() - z['stop'].mean())
            d.append(100 * (e[2] - e[0]))
        print('%-18s hit %2.0f %2.0f %2.0f | stop %2.0f %2.0f %2.0f | net %+5.0f %+5.0f %+5.0f | cuts %.2f %.2f | edge H1 %+4.0f H2 %+4.0f %s' % (
            f, *(100 * t.hit), *(100 * t['stop']), *(t.net / 1000), t.lo[1], t.lo[2], d[0], d[1], '<< same sign, both > 12' if d[0] * d[1] > 0 and min(abs(d[0]), abs(d[1])) > 12 else ''))
