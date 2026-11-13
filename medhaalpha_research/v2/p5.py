import sys, json, warnings
warnings.filterwarnings('ignore')
SP = sys.argv[1]
sys.path.insert(0, SP + '/v2')
import numpy as np, pandas as pd
from lab import live_df
from p3 import proxy_rows, add_models
K = add_models(proxy_rows(SP + '/v2/proxy_known')); U = add_models(proxy_rows(SP + '/v2/proxy_unseen'))
out = {}
for lab, X in (('known', K), ('unseen', U)):
    nd = X.day.nunique()
    print(lab, nd, 'sessions | signals/day %.1f (longs %.1f, shorts %.1f)' % (len(X) / nd, (X.side == 'LONG').sum() / nd, (X.side == 'SHORT').sum() / nd),
          '| all-signal hit %.1f%% stop %.1f%% net/trade %+.0f' % (100 * X.hit.mean(), 100 * X['stop'].mean(), X.net1.mean()))
    out[lab] = {'sessions': nd}
    for m in ('m_opus', 'm_fable_op', 'm_v2', 'm_v3'):
        t = X.loc[live_df(X, m, 75)]
        lo, sh = t[t.side == 'LONG'], t[t.side == 'SHORT']
        out[lab][m] = {'n': len(t), 'hit': round(100 * t.hit.mean(), 1), 'stop': round(100 * t['stop'].mean(), 1), 'net': round(t.net1.sum()), 'per_session': round(t.net1.sum() / nd),
                       'long': [len(lo), round(100 * lo.hit.mean(), 1), round(100 * lo['stop'].mean(), 1), round(lo.net1.sum())], 'short': [len(sh), round(100 * sh.hit.mean(), 1), round(100 * sh['stop'].mean(), 1), round(sh.net1.sum())]}
        print('   %-9s trades/session %.2f hit %.1f%% stop %.1f%% net/session %+6.0f | longs n=%3d hit %.1f%% net %+8.0f | shorts n=%3d hit %.1f%% net %+8.0f' % (
            m[2:], len(t) / nd, 100 * t.hit.mean(), 100 * t['stop'].mean(), t.net1.sum() / nd, len(lo), 100 * lo.hit.mean(), lo.net1.sum(), len(sh), 100 * sh.hit.mean(), sh.net1.sum()))
json.dump(out, open(SP + '/v2/p5.json', 'w'))
