"""Independent re-computation of prior_compression (reviewer). Uses harness.py directly, own flag code (pandas rolling +
merge_asof), own pick, own stats, option net recomputed with H.option_net. Writes nothing outside this folder."""
import sys, json
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt')
import harness as H

D = H.load_all()

# ---- 1. option columns really are H.option_net (no outcome shortcut)
for s in H.SETS:
    for p in ('T1', 'T3'):
        x = H.option_net(D[s], p)
        dif = (x - D[s]['opt_' + p]).abs().max()
        print('opt check %-6s %s max abs diff vs fresh option_net: %.6f' % (s, p, dif))

mins, daily, nifty, lot = H.minute_data()
del mins, lot

# ---- 2. short sessions from Nifty minutes (own way)
nl = nifty.index.tz_localize(None) if nifty.index.tz is not None else nifty.index
cnt = pd.Series(1, index=nl.strftime('%Y-%m-%d')).groupby(level=0).sum()
short = sorted(cnt[cnt < 300].index)
print('short sessions (Nifty bars < 300):', {k: int(cnt[k]) for k in short})
del nifty

# ---- 3. calendar of sessions (union over all symbols' daily candles), for the prev-session check
alld = set()
dd = {}
for sym, dl in daily.items():
    if dl is None or len(dl) == 0:
        continue
    idx = dl.index.tz_localize(None) if dl.index.tz is not None else dl.index
    x = pd.DataFrame({'date': idx.strftime('%Y-%m-%d'), 'o': dl.open.to_numpy(float), 'h': dl.high.to_numpy(float),
                      'l': dl.low.to_numpy(float), 'c': dl.close.to_numpy(float)})
    x = x[~x.date.isin(short)].drop_duplicates('date', keep='last').sort_values('date').reset_index(drop=True)
    dd[sym] = x
    alld.update(x.date)
cal = sorted(alld)
print('daily candles: %d symbols, calendar %s..%s, %d sessions' % (len(dd), cal[0], cal[-1], len(cal)))
calprev = {d: (cal[i - 1] if i > 0 else None) for i, d in enumerate(cal)}

# per-symbol flags valid for the session AFTER each candle row
FL = {}
for sym, x in dd.items():
    r = x.h - x.l
    y = pd.DataFrame({'adate': x.date})
    y['nr4'] = r == r.rolling(4).min()
    y['nr7'] = r == r.rolling(7).min()
    y['tri'] = (x.h < np.minimum(x.h.shift(1), x.h.shift(2))) & (x.l > np.maximum(x.l.shift(1), x.l.shift(2)))
    mean14 = r.shift(1).rolling(14).mean()
    big = r > mean14
    y['tl'] = (x.o <= x.l + 0.15 * r) & (x.c >= x.l + 0.85 * r) & big
    y['ts'] = (x.o >= x.l + 0.85 * r) & (x.c <= x.l + 0.15 * r) & big
    y['nhist'] = np.arange(1, len(x) + 1)       # sessions up to and including this row
    y['comp'] = y.nr4 | y.nr7 | y.tri
    FL[sym] = y
del daily


def attach(df):
    out = []
    for sym, g in df.groupby('symbol'):
        y = FL[sym]
        # last candle strictly before d: use the position via searchsorted on the sorted string dates
        pos = np.searchsorted(y.adate.to_numpy(), g.day.to_numpy(), 'left') - 1
        yy = y.iloc[pos].reset_index(drop=True)
        z = g.copy()
        for k in ('adate', 'nr4', 'nr7', 'tri', 'comp', 'tl', 'ts', 'nhist'):
            z['v_' + k] = yy[k].to_numpy()
        out.append(z)
    z = pd.concat(out).loc[df.index]
    lg = z.side == 'LONG'
    z['v_trend_same'] = np.where(lg, z.v_tl, z.v_ts).astype(bool)
    z['v_ok'] = z.v_nhist >= 16
    z.loc[~z.v_ok, ['v_comp', 'v_trend_same']] = False
    z['v_comp'] = z.v_comp.astype(bool)
    z['v_calprev'] = z.day.map(lambda d: calprev.get(d) if d in calprev else max([c for c in cal if c < d]))
    return z


for s in H.SETS:
    D[s] = attach(D[s])
    z = D[s]
    assert (z.v_adate < z.day).all()
    stale = (z.v_adate != z.v_calprev)
    print('%-6s rows %d  comp %.1f%%  trend_same %.1f%%  rows whose own last candle != calendar previous session: %d %s' % (
        s, len(z), 100 * z.v_comp.mean(), 100 * z.v_trend_same.mean(), int(stale.sum()),
        sorted(set(zip(z[stale].symbol, z[stale].day, z[stale].v_adate)))[:8]))


# ---- 4. own pick / stats
def mypick(df, sc, thr=75, n=6):
    d = df.assign(_s=sc.astype(float))
    d = d[d._s >= thr]
    d = d.sort_values(['day', 'time', '_s', 'symbol'], ascending=[True, True, False, True], kind='mergesort')
    d['_k'] = d.groupby('day').cumcount()
    return d[d._k < n]


def mystats(t, days, pnlcol):
    by = t.groupby('day')[pnlcol].sum().reindex(days).fillna(0.0)
    eq = by.cumsum()
    peak = np.maximum.accumulate(np.maximum(eq.to_numpy(), 0.0))
    return dict(n=len(t), net=round(float(t[pnlcol].sum())), worst_day=round(float(by.min())), maxdd=round(float((eq.to_numpy() - peak).min())),
                fut=round(float(t['_fut'].sum())))


def price(t, pol):
    t = t.copy()
    t['_opt'] = H.option_net(t, pol).to_numpy()      # fresh option pricing
    t['_fut'] = t['net_' + pol].to_numpy()
    return t


def spec(df, name):
    if name == 'FOP':
        return price(mypick(df, df.s_fable_op), 'T3')
    if name == 'V3':
        return price(mypick(df, df.s_opus_v3), 'T1')
    if name == 'S1':
        return price(mypick(df, df.s_fable_op + 10 * df.v_comp), 'T3')
    if name == 'S2':
        return price(mypick(df, df.s_fable_op.where(~df.v_trend_same)), 'T3')
    if name == 'S3':
        return price(mypick(df, (df.s_fable_op + 10 * df.v_comp).where(~df.v_trend_same)), 'T3')
    if name == 'S4':
        return price(mypick(df, (df.s_opus_v3 + 10 * df.v_comp).where(~df.v_trend_same)), 'T1')


HALF = {s: H.halves(s) for s in H.SETS}
OUT = {}
TR = {}
for s in H.SETS:
    df = D[s]
    days = sorted(df.day.unique())
    for name in ('V3', 'FOP', 'S1', 'S2', 'S3', 'S4'):
        t = spec(df, name)
        TR[(s, name)] = t
        assert t.groupby('day').size().max() <= 6
        r = {'all': mystats(t, days, '_opt')}
        for i, (lo, hi) in enumerate(HALF[s]):
            dd_ = [d for d in days if lo <= d <= hi]
            r['h%d' % (i + 1)] = mystats(t[(t.day >= lo) & (t.day <= hi)], dd_, '_opt')
        OUT[(s, name)] = r
        print('%-6s %-4s all n %3d net %+8d wd %+7d dd %+8d fut %+8d | h1 n %3d net %+8d wd %+7d dd %+8d | h2 n %3d net %+8d wd %+7d dd %+8d' % (
            s, name, r['all']['n'], r['all']['net'], r['all']['worst_day'], r['all']['maxdd'], r['all']['fut'],
            r['h1']['n'], r['h1']['net'], r['h1']['worst_day'], r['h1']['maxdd'], r['h2']['n'], r['h2']['net'], r['h2']['worst_day'], r['h2']['maxdd']))

# ---- 5. design choice re-done
b1, b2 = OUT[('real', 'V3')]['h1'], OUT[('real', 'FOP')]['h1']
wl, dl_ = 1.25 * max(b1['worst_day'], b2['worst_day']), 1.25 * max(b1['maxdd'], b2['maxdd'])
ok = {k: (OUT[('real', k)]['h1']['worst_day'] >= wl and OUT[('real', k)]['h1']['maxdd'] >= dl_) for k in ('S1', 'S2', 'S3', 'S4')}
print('design limits wd %.0f dd %.0f ; ok %s ; chosen %s' % (wl, dl_, ok, max([k for k in ok if ok[k]], key=lambda k: OUT[('real', k)]['h1']['net'])))

# ---- 6. bar
for s, part in (('unseen', 'all'), ('real', 'h2')):
    c, v3, f = OUT[(s, 'S2')][part], OUT[(s, 'V3')][part], OUT[(s, 'FOP')][part]
    print('BAR %s %s: S2 %+d vs V3 %+d FOP %+d -> beats both %s | wd %+d lim %+.0f | dd %+d lim %+.0f' % (
        s, part, c['net'], v3['net'], f['net'], c['net'] > max(v3['net'], f['net']), c['worst_day'], 1.25 * max(v3['worst_day'], f['worst_day']),
        c['maxdd'], 1.25 * max(v3['maxdd'], f['maxdd'])))

# ---- 7. per-day difference S2 - FOP, bootstrap; trades removed/added
rng = np.random.default_rng(7)
for s, lo, hi in (('unseen', '2025-11-03', '2026-05-11'), ('unseen', '2025-11-03', '2026-02-05'), ('unseen', '2026-02-06', '2026-05-11'),
                  ('real', '2026-05-12', '2026-08-31'), ('real', '2026-09-01', '2026-11-11'), ('known', '2026-05-12', '2026-10-19')):
    df = D[s]
    days = [d for d in sorted(df.day.unique()) if lo <= d <= hi]
    a, b = TR[(s, 'S2')], TR[(s, 'FOP')]
    a, b = a[(a.day >= lo) & (a.day <= hi)], b[(b.day >= lo) & (b.day <= hi)]
    da = a.groupby('day')._opt.sum().reindex(days).fillna(0) - b.groupby('day')._opt.sum().reindex(days).fillna(0)
    nz = da[da.abs() > 1e-6]
    bs = np.array([rng.choice(da.to_numpy(), len(da)).sum() for _ in range(20000)])
    rem = b[~b.index.isin(a.index)]
    add = a[~a.index.isin(b.index)]
    print('%-6s %s..%s diff S2-FOP %+8.0f on %d days (%d days differ); boot 90%% CI [%+.0f, %+.0f], P(diff<=0) %.3f; removed n %d opt %+d (wins %d) ; added n %d opt %+d' % (
        s, lo, hi, da.sum(), len(days), len(nz), np.quantile(bs, .05), np.quantile(bs, .95), (bs <= 0).mean(), len(rem), rem._opt.sum(), (rem._opt > 0).sum(), len(add), add._opt.sum()))
    if s in ('unseen', 'real') and (lo, hi) in (('2025-11-03', '2026-05-11'), ('2026-09-01', '2026-11-11')):
        print('    removed trades:', list(zip(rem.day, rem.symbol, rem.side, rem._opt.round())))
        # day-level std dev of FOP P&L for scale
        fb = b.groupby('day')._opt.sum().reindex(days).fillna(0)
        print('    FOP per-day P&L sd %.0f, sd of total over %d days %.0f' % (fb.std(), len(days), fb.std() * np.sqrt(len(days))))

# trend-same picks among FOP>=75 base picks, pooled over the three sets, with a sign test
pool = []
for s in H.SETS:
    b = TR[(s, 'FOP')]
    x = b[b.v_trend_same]
    pool.append(x._opt.to_numpy())
    print('%-6s FOP picks after same-dir trend day: n %d opt %+d, mean %+.0f, wins %d; other picks mean %+.0f' % (
        s, len(x), x._opt.sum(), x._opt.mean(), (x._opt > 0).sum(), b[~b.v_trend_same]._opt.mean()))
p = np.concatenate(pool[:2])
from scipy import stats as st
print('unseen+real trend-same FOP picks pooled n %d mean %+.0f t %.2f' % (len(p), p.mean(), p.mean() / (p.std(ddof=1) / np.sqrt(len(p)))))
