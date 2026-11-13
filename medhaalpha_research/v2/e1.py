# Experiment 1 (design period only): out-of-fold scores from leave-one-month-out fits, per side, then the live rule
# at Opus's trade count. Compares feature sets and what the score is asked to predict.
import sys, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
D = df[df.design].copy()
months = sorted(D.month.unique())
SETS = {
    'snap': ['move_atr', 'open_atr', 'vwap_atr', 'gap_atr', 'pos', 'log_stale', 'log_open_min', 'nifty_dir', 'rel_vol', 'n_break', 'rsi_room', 'ext52', 'risk_pct', 'beyond_pd', 'vs20_dir', 'ret5_dir', 'ret20_dir'],
    'snap_small': ['move_atr', 'open_atr', 'vwap_atr', 'gap_atr', 'pos', 'log_open_min', 'nifty_dir', 'rel_vol'],
    'scores+exact': ['t_opus', 't_fable', 't_fable_op', 'log_open_min', 'nifty_dir', 'rel_vol', 'n_break', 'rsi_room', 'ext52', 'vs20_dir', 'ret5_dir', 'ret20_dir'],
    'scores only': ['t_opus', 't_fable', 't_fable_op'],
    'snap+context': ['move_atr', 'open_atr', 'vwap_atr', 'gap_atr', 'pos', 'log_stale', 'log_open_min', 'nifty_dir', 'rel_vol', 'n_break', 'rsi_room', 'ext52', 'risk_pct', 'beyond_pd', 'crowd_same', 'crowd_all', 'breadth_dir', 'strong_dir'],
}
target = len(live_df(D, 't_opus', 75))
print('design signals', len(D), '| Opus live trades', target)
print(line('Opus >= 75 (now)', stat(D, live_df(D, 't_opus', 75))))
print(line('Fable-OP >= 75 (now)', stat(D, live_df(D, 't_fable_op', 75))))
print(line('Fable-OP >= 72 (same count)', stat(D, live_df(D, 't_fable_op', 72))))
out = {}
for sname, feats in SETS.items():
    for l2 in (10.0, 50.0):
        ph, ps, er = pd.Series(np.nan, index=D.index), pd.Series(np.nan, index=D.index), pd.Series(np.nan, index=D.index)
        for side in ('LONG', 'SHORT'):
            S = D[D.side == side]
            for mo in months:
                tr, te = S[S.month != mo], S[S.month == mo]
                prep = Prep(tr[feats].to_numpy(float))
                Ztr, Zte = prep(tr[feats].to_numpy(float)), prep(te[feats].to_numpy(float))
                ph[te.index] = logit_pred(logit_fit(Ztr, tr.hit.to_numpy(float), l2), Zte)
                ps[te.index] = logit_pred(logit_fit(Ztr, tr['stop'].to_numpy(float), l2), Zte)
                er[te.index] = ridge_pred(ridge_fit(Ztr, tr.r1.clip(-1.2, 1.2).to_numpy(float), l2), Zte)
        D['_ph'], D['_net'], D['_er'] = ph, ph - ps, er
        for obj in ('_ph', '_net', '_er'):
            thr = thr_for(D, obj, target)
            idx = live_df(D, obj, thr)
            s = stat(D, idx)
            bym = ' '.join('%d%%/%+dk' % (100 * D.loc[[i for i in idx if D.month[i] == mo]].hit.mean() if any(D.month[i] == mo for i in idx) else 0,
                                           D.loc[[i for i in idx if D.month[i] == mo]].net1.sum() / 1000) for mo in months)
            name = '%s l2=%g %s' % (sname, l2, {'_ph': 'P(hit)', '_net': 'P(hit)-P(stop)', '_er': 'E[R]'}[obj])
            print(line(name, s)[:132], '|', bym)
