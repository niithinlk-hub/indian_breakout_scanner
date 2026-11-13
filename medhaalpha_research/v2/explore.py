import sys
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from frame import load
df = load()
print('rows', len(df), '| design', int(df.design.sum()), '| unseen', int(df.unseen.sum()), '| longs', int(df.long.sum()))
print('\n-- how well the cash-share rebuild reproduces the scanner\'s own (futures) scores')
for m in ('opus', 'fable', 'fable_op'):
    d = df['c_' + m] - df['t_' + m]
    thr = {'opus': 75, 'fable': 80, 'fable_op': 75}[m]
    agree = ((df['c_' + m] >= thr) == (df['t_' + m] >= thr)).mean()
    print('%-8s corr %.3f | mean diff %+.1f | mean abs diff %.1f | within 5 pts %.0f%% | same side of threshold %.0f%%' % (
        m, np.corrcoef(df['c_' + m], df['t_' + m])[0, 1], d.mean(), d.abs().mean(), 100 * (d.abs() <= 5).mean(), 100 * agree))
D = df[df.design]
print('\n-- design period base rates by side')
for s, g in D.groupby('side'):
    print('%-5s n=%4d hit %.1f%% stop %.1f%% mean R(T1) %+.3f net/trade %+.0f' % (s, len(g), 100 * g.hit.mean(), 100 * g.stop.mean(), g.r1.mean(), g.net1.mean()))
feats = ['open_atr', 'from_open', 'vwap_atr', 'beyond_vwap', 'gap_atr', 'gap', 'rsi_room', 'structure', 'move_atr', 'day_chg', 'pos', 'mins_since_extreme', 'minutes_since_open',
         'nifty_dir', 'nifty_from_open', 'risk_pct', 'risk_atr', 'ext52', 'rel_vol', 'n_break', 'vs20_dir', 'ret5_dir', 'ret20_dir', 'atr_pct', 'beyond_pd', 'range_atr',
         'breadth_dir', 'breadth_med_dir', 'strong_dir', 'crowd_same', 'crowd_all', 'same_minute', 'or_break', 't_opus', 't_fable', 't_fable_op']
print('\n-- design period: each feature cut into 4 equal groups (low -> high): hit%% | stop%% | mean R at T1; sign of (top - bottom) hit%% in each month')
for side in ('LONG', 'SHORT'):
    g = D[D.side == side]
    print('==', side, len(g))
    for f in feats:
        x = g[f]
        if x.isna().all() or x.nunique() < 4:
            if x.nunique() >= 2:
                t = g.groupby(f).agg(n=('hit', 'size'), hit=('hit', 'mean'), stop=('stop', 'mean'), r=('r1', 'mean'))
                print('%-18s %s' % (f, ' | '.join('%s: n%d hit %.0f stop %.0f R %+.2f' % (i, r.n, 100 * r.hit, 100 * r.stop, r.r) for i, r in t.iterrows())))
            continue
        q = pd.qcut(x.rank(method='first'), 4, labels=False)
        t = g.groupby(q).agg(lo=(f, 'min'), hit=('hit', 'mean'), stop=('stop', 'mean'), r=('r1', 'mean'))
        signs = ''
        for mo, gm in g.groupby('month'):
            qm = pd.qcut(gm[f].rank(method='first'), 4, labels=False)
            signs += '+' if gm[qm == 3].hit.mean() > gm[qm == 0].hit.mean() else '-'
        rs = ''
        for mo, gm in g.groupby('month'):
            qm = pd.qcut(gm[f].rank(method='first'), 4, labels=False)
            rs += '+' if gm[qm == 3].r1.mean() > gm[qm == 0].r1.mean() else '-'
        print('%-18s hit %s | stop %s | R %s | cuts %s | hit sign %s R sign %s' % (
            f, ' '.join('%2.0f' % (100 * v) for v in t.hit), ' '.join('%2.0f' % (100 * v) for v in t.stop), ' '.join('%+.2f' % v for v in t.r),
            ' '.join('%.2f' % v for v in t.lo[1:]), signs, rs))
