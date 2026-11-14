"""Independent reviewer check of nifty_rv_regime (S1 chosen). Own RV code, own pick, fresh option_net pricing,
bootstrap of per-day P&L differences. Does not touch the tester's files (reads ratios.pkl only to compare)."""
import sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

rng = np.random.default_rng(12345)

# ---------------------------------------------------------------- Nifty minutes (loaded once)
_, _, nifty, _ = H.minute_data()
n = nifty[['open', 'close']].copy()
n['day'] = n.index.strftime('%Y-%m-%d')
n['hm'] = n.index.strftime('%H:%M')
n = n[(n.hm >= '09:15') & (n.hm <= '15:29')]
cnt = n.groupby('day').size()
full = sorted(cnt[cnt >= 300].index)
print('sessions', len(cnt), 'full', len(full), 'dropped', sorted(cnt[cnt < 300].index))

# per-day cumulative RV as dict day -> Series indexed by hm (own implementation: pandas per-day loop)
cumrv = {}
for d in full:
    x = n[n.day == d].sort_index()
    x = x[~x.index.duplicated()]
    lr = np.log(x.close).diff()
    lr.iloc[0] = np.log(x.close.iloc[0] / x.open.iloc[0])
    cumrv[d] = pd.Series(np.sqrt((lr ** 2).cumsum().to_numpy()), index=x.hm.to_numpy())
fullpos = {d: i for i, d in enumerate(full)}


def rv_ratio(day, hm):
    if day not in fullpos:
        return np.nan
    i = fullpos[day]
    prev = full[max(0, i - 14):i]
    vals = [cumrv[p].get(hm, np.nan) for p in prev]
    vals = [v for v in vals if np.isfinite(v)]
    if len(vals) < 10:
        return np.nan
    return cumrv[day].get(hm, np.nan) / np.mean(vals)


def pd_ratio(day):
    # first full session strictly before day = d-1
    prevs = [p for p in full if p < day]
    if len(prevs) < 11:
        return np.nan
    dm1 = prevs[-1]
    base = prevs[-15:-1]
    fs = lambda p: cumrv[p].iloc[-1]
    return fs(dm1) / np.mean([fs(p) for p in base])


D = H.load_all()
R = pd.read_pickle(SP + '/hunt/nifty_rv_regime/ratios.pkl')
for s in H.SETS:
    d = D[s]
    keys = d[['day', 'time']].drop_duplicates()
    mp = {(a, b): rv_ratio(a, b) for a, b in keys.itertuples(index=False)}
    d['my_rv'] = [mp[(a, b)] for a, b in zip(d.day, d.time)]
    pdm = {a: pd_ratio(a) for a in d.day.unique()}
    d['my_pd'] = d.day.map(pdm)
    # compare to tester's ratio table
    trv = np.array([R['RATIO'].loc[a, b] if a in R['RATIO'].index else np.nan for a, b in zip(d.day, d.time)])
    tpd = d.day.map(R['PD']).to_numpy(float)
    print('%-6s my rv NaN %d, max |diff| vs tester rv %.2e, pd %.2e' % (s, d.my_rv.isna().sum(), np.nanmax(np.abs(d.my_rv - trv)), np.nanmax(np.abs(d.my_pd - tpd))))

# timing check: nifty_chg should equal Nifty close of bar 'time' vs previous full-session close (not bar time+1)
lastc = {d: n[n.day == d].close.iloc[-1] for d in full}
x = D['unseen'].drop_duplicates(['day', 'time']).sample(200, random_state=3)
e0, e1 = [], []
for _, r in x.iterrows():
    i = fullpos[r.day]
    pc = lastc[full[i - 1]]
    nd = n[n.day == r.day].set_index('hm').close
    t1 = (pd.Timestamp('2000-01-01 ' + r.time) + pd.Timedelta(minutes=1)).strftime('%H:%M')
    e0.append(abs((nd[r.time] / pc - 1) * 100 - r.nifty_chg))
    e1.append(abs((nd[t1] / pc - 1) * 100 - r.nifty_chg))
print('nifty_chg vs close@time: median abs err %.4f ; vs close@time+1: %.4f' % (np.median(e0), np.median(e1)))
ent = D['real'].o_entry_ts.str[11:16]
tp1 = (pd.to_datetime('2000-01-01 ' + D['real'].time) + pd.Timedelta(minutes=1)).dt.strftime('%H:%M')
print('real: entry minute == time+1 for %.3f of rows' % (ent == tp1).mean())

# ---------------------------------------------------------------- fresh option pricing vs cached opt_ columns
for s in H.SETS:
    d = D[s]
    for p in ('T1', 'T3', 'CLOSE_TR'):
        fresh = H.option_net(d, p)
        print('%-6s %-8s max |fresh option_net - cached opt_| = %.3g' % (s, p, np.abs(fresh - d['opt_' + p]).max()))
        d['fresh_' + p] = fresh


# ---------------------------------------------------------------- own pick + S1
def my_pick(df, score, thr=75, nmax=6):
    d = df.assign(_s=score.astype(float))
    d = d[d._s >= thr]
    d = d.sort_values(['day', 'time', '_s', 'symbol'], ascending=[True, True, False, True], kind='mergesort')
    d['_k'] = d.groupby('day').cumcount()
    return d[d._k < nmax]


def trades(df, which):
    if which == 'S1':
        t = my_pick(df, df.s_fable_op)
        t['pol'] = np.where(t.my_rv >= 1.0, 'T3', 'T1')
        t.loc[t.my_rv.isna(), 'pol'] = 'T3'
    elif which == 'FOP':
        t = my_pick(df, df.s_fable_op); t['pol'] = 'T3'
    elif which == 'V3':
        t = my_pick(df, df.s_opus_v3); t['pol'] = 'T1'
    elif which == 'SW1':
        a = my_pick(df[df.regime != 'Downtrend'], df.s_fable_op[df.regime != 'Downtrend']); a['pol'] = 'T3'
        b = my_pick(df[df.regime == 'Downtrend'], df.s_opus_v3[df.regime == 'Downtrend']); b['pol'] = 'T1'
        t = pd.concat([a, b])
    elif which == 'S3':
        t = my_pick(df, df.s_opus_v3); t['pol'] = np.where(t.my_rv >= 1.0, 'CLOSE_TR', 'T1')
    t['pnl'] = [r['fresh_' + p] for (_, r), p in zip(t.iterrows(), t.pol)]
    t['futn'] = [r['net_' + p] for (_, r), p in zip(t.iterrows(), t.pol)]
    return t


def st(t, days):
    by = t.pnl.groupby(t.day).sum().reindex(days).fillna(0.0)
    eq = by.cumsum()
    return dict(n=len(t), net=round(t.pnl.sum()), fut=round(t.futn.sum()), worst=round(by.min()), dd=round((eq - eq.cummax().clip(lower=0)).min()),
                maxper=int(t.groupby('day').size().max()) if len(t) else 0), by


# check own pick equals H.pick for S1 on every set
for s in H.SETS:
    a = my_pick(D[s], D[s].s_fable_op); b = H.pick(D[s], 's_fable_op', 75, 6)
    assert list(a.index) == list(b.index), s
print('own pick == H.pick on all sets')

parts = {'unseen': ('unseen', '2025-11-03', '2026-05-11'), 'unseen_h1': ('unseen', '2025-11-03', '2026-02-05'), 'unseen_h2': ('unseen', '2026-02-06', '2026-05-11'),
         'real_h1(design)': ('real', '2026-05-12', '2026-08-31'), 'real_h2': ('real', '2026-09-01', '2026-11-11'), 'real': ('real', '2026-05-12', '2026-11-11'),
         'known': ('known', '2026-05-12', '2026-10-19'), 'known_h1': ('known', '2026-05-12', '2026-07-31'), 'known_h2': ('known', '2026-08-01', '2026-10-19')}
BY = {}
print('\n%-16s %-4s %5s %9s %9s %9s %9s %s' % ('part', 'mdl', 'n', 'opt net', 'worst', 'maxDD', 'fut', 'max/day'))
for pn, (s, lo, hi) in parts.items():
    df = D[s]
    days = sorted(df.day.unique()); days = [x for x in days if lo <= x <= hi]
    for m in ('V3', 'FOP', 'SW1', 'S1', 'S3'):
        t = trades(df, m)
        t = t[(t.day >= lo) & (t.day <= hi)]
        r, by = st(t, days)
        BY[(pn, m)] = by
        print('%-16s %-4s %5d %+9d %+9d %+9d %+9d %d' % (pn, m, r['n'], r['net'], r['worst'], r['dd'], r['fut'], r['maxper']))

# ---------------------------------------------------------------- bootstrap of per-day differences
print('\nper-day difference S1 - baseline: mean/day, total, day-bootstrap 95% CI of total, P(total>0); also block bootstrap (5-day blocks)')
for pn in ('unseen', 'real_h2', 'real_h1(design)', 'known'):
    for b in ('FOP', 'V3', 'SW1'):
        dlt = (BY[(pn, 'S1')] - BY[(pn, b)]).to_numpy()
        N = len(dlt)
        bs = np.array([dlt[rng.integers(0, N, N)].sum() for _ in range(10000)])
        k = 5; nb = int(np.ceil(N / k))
        bb = []
        for _ in range(5000):
            st_ = rng.integers(0, N - k + 1, nb)
            bb.append(np.concatenate([dlt[i:i + k] for i in st_])[:N].sum())
        bb = np.array(bb)
        print('  %-16s S1-%-3s days %3d total %+9d  sd/day %7.0f  iid CI [%+9d, %+9d] P>0 %.3f | block CI [%+9d, %+9d] P>0 %.3f' % (
            pn, b, N, dlt.sum(), dlt.std(ddof=1), np.percentile(bs, 2.5), np.percentile(bs, 97.5), (bs > 0).mean(),
            np.percentile(bb, 2.5), np.percentile(bb, 97.5), (bb > 0).mean()))

# concentration: how many days carry the S1 - FOP gap on unseen / real_h2
for pn in ('unseen', 'real_h2'):
    dlt = (BY[(pn, 'S1')] - BY[(pn, 'FOP')])
    print('%s: days S1 differs from FOP: %d; 5 most negative days sum %+d, 5 most positive %+d' % (pn, int((dlt.abs() > 1).sum()), dlt.nsmallest(5).sum(), dlt.nlargest(5).sum()))
