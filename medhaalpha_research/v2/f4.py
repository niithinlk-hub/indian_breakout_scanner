# Leave-one-month-out search. In each fold the gates are chosen on the other six months only (thresholds from those months),
# then applied to the month left out. The out-of-fold total is what a data-driven v3 would have delivered on months it had not seen.
import sys, warnings, math, json
warnings.filterwarnings('ignore')
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
from lab import *
df = load()
A = df[df.design | df.unseen].copy()
early = (1 - np.log(A.minutes_since_open.clip(lower=5) / 5) / math.log(180 / 5)).clip(0, 1)
ext = np.where(A.long == 1, 1 + A.from_52w_high / 25, 1 - A.from_52w_low / 25).clip(0, 1)
A['fable_tight'] = A.t_fable - 100 / 3 * early - 100 / 3 * ext
A['stop_atr_true'] = (2 - A.fable_tight / (100 / 3)) / A.atr_pct
lg = (A.long == 1).to_numpy()
FE = ['rel_vol', 'n_break', 'ext52', 'stop_atr_true', 'fable_tight', 'atr_pct', 'ret5_dir', 'ret20_dir', 't_opus', 't_fable', 't_fable_op', 'rsi_room', 'vs20_dir', 'nifty_dir', 'breadth_dir',
      'minutes_since_open', 'crowd_same', 'gap_atr', 'move_atr', 'pos', 'vwap_atr', 'open_atr']
Q = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
months = sorted(A.month.unique())


def score(P, lgate=None, sgate=None, S=False):
    """v2 score with optional gates. A gate is (feature, 'low'|'high', threshold): the signal is dropped when the feature is below / above it."""
    ls = P.t_fable_op.to_numpy().copy()
    ss = (np.maximum(P.t_opus, P.t_fable_op) if S else P.t_opus).to_numpy().copy()
    for gate, arr in ((lgate, ls), (sgate, ss)):
        if gate:
            f, d, thr = gate
            x = P[f].to_numpy()
            arr[(x < thr) if d == 'low' else (x > thr)] = 0.0
    return np.where((P.long == 1).to_numpy(), ls, ss)


def run(P, **kw):
    P = P.assign(_s=score(P, **kw))
    return stat(P, live_df(P, '_s', 75)), P.loc[live_df(P, '_s', 75)]


def choose(T):
    """On training rows T: best long gate and best short option, each judged with the other side left as in v2."""
    base, picks = run(T)
    bl, bs = picks[picks.long == 1], picks[picks.long == 0]

    def side_stats(p, long):
        g = p[p.long == (1 if long else 0)]
        return len(g), g.hit.mean() if len(g) else 0, g['stop'].mean() if len(g) else 1, g.net1.sum()
    best = {}
    for long in (True, False):
        n0, h0, s0, net0 = side_stats(picks, long)
        cands = [(None, False)] + ([(None, True)] if not long else [])
        pool = bl if long else bs
        for f in FE:
            for d, q in (('low', Q), ('high', 1 - Q)):
                thr = float(pool[f].quantile(q))
                cands.append(((f, d, thr), False))
                if not long:
                    cands.append(((f, d, thr), True))
        top = (net0, None, False)
        for gate, S in cands:
            kw = {('lgate' if long else 'sgate'): gate}
            if not long:
                kw['S'] = S
            _, p = run(T, **kw)
            n, h, s, net = side_stats(p, long)
            if n >= 0.9 * n0 and h >= h0 and s <= s0 and net > top[0]:
                top = (net, gate, S)
        best['long' if long else 'short'] = top
    return best


oof, chosen = [], []
for mo in months:
    T, H = A[A.month != mo], A[A.month == mo]
    b = choose(T)
    kw = dict(lgate=b['long'][1], sgate=b['short'][1], S=b['short'][2])
    _, p = run(H, **kw)
    oof.append(p)
    chosen.append((mo, b['long'][1], b['short'][1], b['short'][2]))
    print('%s chosen on the other months -> longs: %s | shorts: %s%s' % (mo, b['long'][1] and '%s %s %.2f' % b['long'][1], b['short'][1] and '%s %s %.2f' % b['short'][1], ' + FOP shorts' if b['short'][2] else ''))
O = pd.concat(oof)
_, V = run(A)
A['opus'] = A.t_opus
print()
print(line('Opus', stat(A, live_df(A, 'opus', 75)))[:150])
print(line('v2', stat(A, V.index))[:150])
print(line('v3 search, out-of-fold', stat(A, O.index))[:150])
print('by month, out-of-fold v3 search vs v2: trades:hit%:stop%/net k')
print('  v3-search', ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0f' % (mo[5:], len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum() / 1000) for mo, g in O.groupby('month')))
print('  v2       ', ' | '.join('%s %2d:%2.0f:%2.0f/%+4.0f' % (mo[5:], len(g), 100 * g.hit.mean(), 100 * g['stop'].mean(), g.net1.sum() / 1000) for mo, g in V.groupby('month')))
b = choose(A)
print('\nchosen on all seven months -> longs:', b['long'][1], '| shorts:', b['short'][1], '+ FOP shorts' if b['short'][2] else '')
s, _ = run(A, lgate=b['long'][1], sgate=b['short'][1], S=b['short'][2])
print(line('that choice, in-sample (flattering)', s)[:150])
