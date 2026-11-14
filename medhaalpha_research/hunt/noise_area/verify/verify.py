"""Independent check of noise_area S2 (Fable-OP>=75 AND noise_x>=1.5, T3) using harness.py directly.
noise_x recomputed with a different route (pandas pivots + rolling over full sessions), option net from both the
opt_T3 column and a fresh H.option_net(...) call, own day-level stats, bootstrap of per-day difference vs baselines."""
import sys, json
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

D = H.load_all()
need = pd.concat([D[s][['symbol', 'day']] for s in H.SETS]).drop_duplicates()
mins, daily, nifty, lot = H.minute_data()
del nifty

feat = {}   # (sym, day) -> (O0, Cprev, close-at-minute Series ffilled, sigma Series)
for sym, g in need.groupby('symbol'):
    m = mins[sym]
    idx = m.index.tz_convert('Asia/Kolkata') if m.index.tz is not None else m.index
    df = pd.DataFrame({'o': m['open'].values, 'c': m['close'].values,
                       'day': idx.strftime('%Y-%m-%d'), 'hm': idx.strftime('%H:%M')})
    df = df[(df.hm >= '09:15') & (df.hm <= '15:29')]
    grid = pd.date_range('2000-01-01 09:15', periods=375, freq='min').strftime('%H:%M')
    C = df.pivot_table(index='day', columns='hm', values='c', aggfunc='last').reindex(columns=grid)
    nbars = C.notna().sum(1)
    Cf = C.ffill(axis=1)
    first_open = df.groupby('day').o.first()
    o915 = df[df.hm == '09:15'].set_index('day').o
    O0 = o915.reindex(C.index).fillna(first_open)
    A = (Cf.div(O0, axis=0) - 1).abs()
    full_days = C.index[nbars >= 300]
    Af = A.loc[full_days]
    # mean of last 14 full sessions (inclusive) per column; min 10 valid values
    roll = Af.rolling(14, min_periods=10).mean()
    dl = daily[sym]
    didx = dl.index.tz_convert('Asia/Kolkata') if dl.index.tz is not None else dl.index
    dser = pd.Series(dl['close'].values, index=didx.strftime('%Y-%m-%d')).sort_index()
    for day in g.day.unique():
        prev_full = [x for x in full_days if x < day]
        sig = roll.loc[prev_full[-1]] if prev_full else pd.Series(np.nan, index=grid)
        before = dser[dser.index < day]
        cprev = before.iloc[-1] if len(before) else np.nan
        feat[(sym, day)] = (O0.get(day, np.nan), cprev, Cf.loc[day] if day in Cf.index else None, sig)
del mins, daily


def noise(df):
    out = np.full(len(df), np.nan)
    for i, r in enumerate(df[['symbol', 'day', 'time', 'side']].itertuples(index=False)):
        o0, cp, cf, sig = feat[(r.symbol, r.day)]
        if cf is None:
            continue
        P, sg = cf[r.time], sig[r.time]
        if r.side == 'LONG':
            out[i] = (P / max(o0, cp) - 1) / sg
        else:
            out[i] = (1 - P / min(o0, cp)) / sg
    return pd.Series(out, index=df.index)


tester = pd.read_pickle(SP + '/hunt/noise_area/noise_x.pkl')
rep = {}
for s in H.SETS:
    d = D[s]
    nx = noise(d)
    d['nx_mine'] = nx
    tx = tester[s]
    assert (tx[['day', 'time', 'symbol']].values == d[['day', 'time', 'symbol']].values).all()
    diff = (nx - tx['noise_x'].values).abs()
    # check daily vs minute consistency for Cprev (split / adjustment issues)
    gap_raw = np.array([feat[(a, b)][0] / feat[(a, b)][1] - 1 for a, b in zip(d.symbol, d.day)])
    print('%-6s noise_x mine vs tester: max abs diff %.2e, NaN mine %d | rows with |O/Cprev-1|>8%%: %d' % (
        s, np.nanmax(diff), int(nx.isna().sum()), int((np.abs(gap_raw) > 0.08).sum())))
    # opt_T3 column == fresh option_net?
    fresh = H.option_net(d, 'T3')
    print('       opt_T3 column vs fresh H.option_net(T3): max abs diff %.4f' % float((fresh - d['opt_T3']).abs().max()))

    days = sorted(d.day.unique())
    sel = {}
    sel['S2'] = H.pick(d, d['s_fable_op'].where(~(nx < 1.5)), 75, 6)
    sel['FOP'] = H.pick(d, 's_fable_op', 75, 6)
    sel['V3'] = H.pick(d, 's_opus_v3', 75, 6)
    pol = {'S2': 'T3', 'FOP': 'T3', 'V3': 'T1'}
    byday = {}
    for k, t in sel.items():
        assert t.groupby('day').size().max() <= 6
        pnl = H.option_net(t, pol[k])
        byday[k] = pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
    halves = H.halves(s)
    for part, (lo, hi) in [('all', (days[0], days[-1]))] + [('h%d' % (i + 1), h) for i, h in enumerate(halves)]:
        line = []
        for k in ('S2', 'FOP', 'V3'):
            b = byday[k][(byday[k].index >= lo) & (byday[k].index <= hi)]
            eq = b.cumsum()
            dd = float((eq - eq.cummax().clip(lower=0)).min())
            line.append('%s net %+9.0f wd %+7.0f dd %+8.0f' % (k, b.sum(), b.min(), dd))
            rep.setdefault(s, {}).setdefault(part, {})[k] = dict(net=round(b.sum()), wd=round(b.min()), dd=round(dd), n=int(((sel[k].day >= lo) & (sel[k].day <= hi)).sum()))
        print('   %-4s %s' % (part, ' | '.join(line)))
    # bootstrap per-day difference vs better baseline (by net) on the test parts
    for part, (lo, hi) in [('all', (days[0], days[-1]))] + [('h%d' % (i + 1), h) for i, h in enumerate(halves)]:
        msk = (byday['S2'].index >= lo) & (byday['S2'].index <= hi)
        for base in ('FOP', 'V3'):
            df_ = (byday['S2'] - byday[base])[msk].to_numpy()
            rng = np.random.default_rng(1)
            bs = np.array([rng.choice(df_, len(df_)).sum() for _ in range(5000)])
            # 5-day block bootstrap
            nb = int(np.ceil(len(df_) / 5))
            starts = rng.integers(0, len(df_) - 4, size=(5000, nb))
            bb = np.array([np.concatenate([df_[a:a + 5] for a in row])[:len(df_)].sum() for row in starts])
            print('   %-6s %-4s S2-%-3s sum %+9.0f  sd(day diff) %7.0f  iid 90%%CI [%+9.0f, %+9.0f] P(>0) %.2f | block5 P(>0) %.2f | days differ %d' % (
                s, part, base, df_.sum(), df_.std(), np.percentile(bs, 5), np.percentile(bs, 95), (bs > 0).mean(), (bb > 0).mean(), int((np.abs(df_) > 1).sum())))
json.dump(rep, open(SP + '/hunt/noise_area/verify/verify_results.json', 'w'), indent=1)
