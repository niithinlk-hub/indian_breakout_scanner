# MedhaSuryan cutoff grid: first 6 signals a day whose MedhaSuryan score (Fable-OP, or Opus v3 on Nifty downtrend days)
# is at least the cutoff; exit T3, T1 on downtrend days. Three result measures: same-day modelled option net, same-day
# futures net, held-to-target futures-equivalent net. Design window = real 12 May - 31 Aug; tests = real 1 Sep - 11 Nov
# and unseen 3 Nov 2025 - 11 May 2026.
import json, sys, pickle
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); import harness as H
D = H.load_all()
HELD = pickle.load(open(SP + '/hunt/cutoff/held_all.pkl', 'rb'))
CUTS = [55, 60, 65, 70, 72.5, 75, 77.5, 80, 82.5, 85, 87.5, 90]
SLICES = {'design 12 May-31 Aug 2026': ('real', '2026-05-12', '2026-08-31'),
          'test 1 Sep-11 Nov 2026': ('real', '2026-09-01', '2026-11-11'),
          'test 3 Nov 2025-11 May 2026': ('unseen', '2025-11-03', '2026-05-11')}


def stats(df, cut, held):
    ms = pd.Series(np.where(df.regime == 'Downtrend', df.s_opus_v3, df.s_fable_op), index=df.index)
    t = H.pick(df, ms, cut, 6)
    pol = np.where(t.regime == 'Downtrend', 'T1', 'T3')
    opt = np.array([t.at[i, 'opt_' + p] for i, p in zip(t.index, pol)])
    fut = np.array([t.at[i, 'net_' + p] for i, p in zip(t.index, pol)])
    hld = np.array([held[i][p]['net'] if i in held else 0.0 for i, p in zip(t.index, pol)])
    days = sorted(df.day.unique())
    byday = pd.Series(opt, index=t.day.values).groupby(level=0).sum().reindex(days).fillna(0.0)
    eq = byday.cumsum()
    hit3 = np.mean([t.at[i, 'r_T3'] >= t.at[i, 'r_T1'] + 1.6 - 0.03 and t.at[i, 'status_T1'] == 'target' for i in t.index]) if len(t) else 0
    return {'n': len(t), 'per_day': round(len(t) / len(days), 2), 'opt': round(opt.sum()), 'fut': round(fut.sum()), 'held': round(hld.sum()),
            'opt_per_trade': round(opt.mean()) if len(t) else 0, 'won_opt': round(100 * (opt > 0).mean(), 1) if len(t) else 0,
            'worst_day_opt': round(byday.min()), 'max_dd_opt': round(float((eq - eq.cummax().clip(lower=0)).min())),
            't1_hit': round(100 * (t.status_T1 == 'target').mean(), 1) if len(t) else 0}


out = {}
for name, (s, lo, hi) in SLICES.items():
    df = D[s][(D[s].day >= lo) & (D[s].day <= hi)]
    out[name] = {str(c): stats(df, c, HELD[s]) for c in CUTS}
    print('\n==', name)
    print('  %6s %5s %6s %11s %11s %11s %8s %6s %10s %10s' % ('cutoff', 'n', '/day', 'options', 'futures', 'held', '/trade', 'won%', 'worst day', 'max DD'))
    for c in CUTS:
        r = out[name][str(c)]
        print('  %6s %5d %6.2f %+11d %+11d %+11d %+8d %6.1f %+10d %+10d' % (c, r['n'], r['per_day'], r['opt'], r['fut'], r['held'], r['opt_per_trade'], r['won_opt'], r['worst_day_opt'], r['max_dd_opt']))
json.dump(out, open(SP + '/hunt/cutoff/grid.json', 'w'), indent=1)
