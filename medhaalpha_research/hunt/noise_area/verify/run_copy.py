"""noise_area: stock-level noise-area filter (Zarattini-Aziz-Barbon) on the scanner's existing A/B signals (pre-registered).

Cash minutes from H.minute_data(), loaded once, used for ALL sets (a feature only; trades keep the harness results).
For stock s, day d, signal bar k (column 'time', the minute bar whose close fires the signal; entry is the next minute's open):
  O_d    = open of the 09:15 bar of d
  Cprev  = close of the last daily candle dated before d
  P      = close of bar k on d (forward-filled from the last earlier bar of d if bar k is missing)
  sigma_k= mean over the stock's 14 previous FULL sessions (>= 300 bars) of |close at bar k (ffilled) / that day's 09:15 open - 1|,
           at least 10 sessions else NaN
  LONG : noise_x = (P / max(O_d, Cprev) - 1) / sigma_k        SHORT: noise_x = (1 - P / min(O_d, Cprev)) / sigma_k
Grid (mask before pick; NaN noise_x passes the filter / is unadjusted):
  S1 s_fable_op where noise_x >= 1.0, pick(75, 6), T3        S2 as S1 with noise_x >= 1.5
  S3 s_fable_op + 10*clip(noise_x - 1, -1, 1), pick(75, 6), T3
  S4 s_opus_v3 where noise_x >= 1.0, pick(75, 6), T1
Choice on real 12 May-31 Aug 2026 by OPTION net, subject to design worst day and max DD no worse than 1.25x the better
design baseline (per metric); else highest net, flagged.
"""
import json, sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/noise_area/verify/rerun'
sys.path.insert(0, SP + '/hunt')
import harness as H

assert H.METRIC == 'opt'
DESIGN = ('2026-05-12', '2026-08-31')
LOOKBACK, MINP, FULL_BARS, NBARS = 14, 10, 300, 375      # 09:15 .. 15:29 = 375 one-minute bars

D = H.load_all()
need = {}                                                  # symbol -> set of days that carry signals (any set)
for s in H.SETS:
    for sym, g in D[s].groupby('symbol'):
        need.setdefault(sym, set()).update(g.day.unique())

# ------------------------------------------------------------------ cash minutes, loaded once
mins, daily, nifty, lot = H.minute_data()
del nifty, lot
print('minute data: %d symbols (%d empty); signal symbols %d, missing from minutes: %s' % (
    len(mins), sum(len(m) == 0 for m in mins.values()), len(need), sorted(set(need) - {k for k, m in mins.items() if len(m)})))

FEAT = {}            # (symbol, day) -> dict(Od, Cprev, Cff row, sigma row, nfull_hist)
stat = dict(stock_days=0, short_days=0, no0915_full=0, no0915_sig=0, dup_bars=0, out_window=0)
short_by_day = {}
for sym in sorted(need):
    m = mins.get(sym)
    if m is None or len(m) == 0:
        continue
    t = m.index.tz_localize(None).values                   # IST wall-clock (index is UTC+05:30)
    dd = t.astype('datetime64[D]')
    k = ((t - dd) // np.timedelta64(1, 'm')).astype(np.int64) - 555          # 09:15 -> 0
    keep = (k >= 0) & (k < NBARS)
    stat['out_window'] += int((~keep).sum())
    dd, k = dd[keep], k[keep]
    op, cl = m['open'].to_numpy(float)[keep], m['close'].to_numpy(float)[keep]
    days_u, first, inv = np.unique(dd, return_index=True, return_inverse=True)
    nd = len(days_u)
    C = np.full((nd, NBARS), np.nan)
    O = np.full((nd, NBARS), np.nan)
    C[inv, k] = cl
    O[inv, k] = op
    cnt = np.bincount(inv, minlength=nd)
    nuniq = np.isfinite(C).sum(1)
    stat['dup_bars'] += int((cnt - nuniq).sum())
    Od = O[:, 0].copy()
    no0915 = ~np.isfinite(Od)
    Od[no0915] = op[first[no0915]]                          # fallback (deviation, counted): first bar's open of that day
    Cff = pd.DataFrame(C).ffill(axis=1).to_numpy()
    full = nuniq >= FULL_BARS
    stat['stock_days'] += nd
    stat['short_days'] += int((~full).sum())
    stat['no0915_full'] += int((no0915 & full).sum())
    for d in days_u[~full]:
        short_by_day[str(d)] = short_by_day.get(str(d), 0) + 1
    A = np.abs(Cff[full] / Od[full, None] - 1.0)            # |close_k / open_0915 - 1| on full sessions
    FD = days_u[full]
    CS = np.vstack([np.zeros(NBARS), np.nancumsum(A, axis=0)])
    CN = np.vstack([np.zeros(NBARS), np.cumsum(np.isfinite(A), axis=0)])
    dl = daily.get(sym)
    ddates = dl.index.tz_localize(None).values.astype('datetime64[D]') if dl is not None and len(dl) else np.array([], 'datetime64[D]')
    dclose = dl['close'].to_numpy(float) if dl is not None and len(dl) else np.array([])
    for day in need[sym]:
        d64 = np.datetime64(day, 'D')
        i = np.searchsorted(days_u, d64)
        j = np.searchsorted(FD, d64, 'left')               # full sessions strictly before d
        j0 = max(0, j - LOOKBACK)
        nvalid = CN[j] - CN[j0]
        sig = np.where(nvalid >= MINP, (CS[j] - CS[j0]) / np.maximum(nvalid, 1), np.nan)
        pc = np.searchsorted(ddates, d64, 'left') - 1
        cprev = dclose[pc] if pc >= 0 else np.nan
        if i < nd and days_u[i] == d64:
            FEAT[(sym, day)] = dict(Od=Od[i], Cprev=cprev, Cff=Cff[i], sig=sig, nhist=j - j0, no0915=bool(no0915[i]))
            stat['no0915_sig'] += int(no0915[i])
        else:
            FEAT[(sym, day)] = dict(Od=np.nan, Cprev=cprev, Cff=np.full(NBARS, np.nan), sig=sig, nhist=j - j0, no0915=False)
print('stock-days %d, short sessions (<%d bars, excluded from histories) %d, by day (top): %s' % (
    stat['stock_days'], FULL_BARS, stat['short_days'], sorted(short_by_day.items(), key=lambda x: -x[1])[:6]))
print('bars outside 09:15-15:29 dropped %d, duplicate bars %d, full sessions without a 09:15 bar (first-bar open used) %d, '
      'signal days without a 09:15 bar %d' % (stat['out_window'], stat['dup_bars'], stat['no0915_full'], stat['no0915_sig']))


def attach(df):
    df = df.copy()
    kk = df['time'].str[:2].astype(int).to_numpy() * 60 + df['time'].str[3:5].astype(int).to_numpy() - 555
    P, Od, Cp, sg, nh = (np.full(len(df), np.nan) for _ in range(5))
    for r, (sym, day, kb) in enumerate(zip(df.symbol, df.day, kk)):
        f = FEAT.get((sym, day))
        if f is None or not (0 <= kb < NBARS):
            continue
        P[r], Od[r], Cp[r], sg[r], nh[r] = f['Cff'][kb], f['Od'], f['Cprev'], f['sig'][kb], f['nhist']
    lg = (df['side'] == 'LONG').to_numpy()
    up, dn = np.fmax(Od, Cp), np.fmin(Od, Cp)                  # NaN-safe only if one side missing -> handled below
    up = np.where(np.isfinite(Od) & np.isfinite(Cp), up, np.nan)
    dn = np.where(np.isfinite(Od) & np.isfinite(Cp), dn, np.nan)
    with np.errstate(invalid='ignore', divide='ignore'):
        nx = np.where(lg, (P / up - 1.0) / sg, (1.0 - P / dn) / sg)
    nx[~np.isfinite(nx)] = np.nan
    df['cash_P'], df['cash_O'], df['cash_Cprev'], df['sigma_k'], df['nhist'], df['noise_x'] = P, Od, Cp, sg, nh, nx
    return df


for s in H.SETS:
    D[s] = attach(D[s])

# ------------------------------------------------------------------ sanity / no-look-ahead checks
print('\n== feature checks')
for s in H.SETS:
    d = D[s]
    rel = (d.cash_P / d.price - 1).abs() * 100
    gap_c = np.where(d.side == 'LONG', 1, -1) * (d.cash_O / d.cash_Cprev - 1) * 100
    gdiff = (gap_c - d.gap).abs()
    fo = d.dropna(subset=['s_fable_op'])
    fsel = d[d.s_fable_op >= 75]
    print('%-6s rows %5d | noise_x NaN %4d (sigma NaN %d, P NaN %d) | |cash P - row price| median %.3f%% p95 %.3f%% | '
          'gap vs harness gap: median abs diff %.3f pp, >0.5pp %d | hist sessions min %d' % (
              s, len(d), d.noise_x.isna().sum(), d.sigma_k.isna().sum(), d.cash_P.isna().sum(), rel.median(), rel.quantile(0.95),
              np.nanmedian(gdiff), int((gdiff > 0.5).sum()), int(np.nanmin(d.nhist))))
    q = d.noise_x
    print('        noise_x all rows: median %.2f, >=1.0 %.1f%%, >=1.5 %.1f%% | Fable-OP>=75 rows %d: median %.2f, >=1.0 %.1f%%, >=1.5 %.1f%%, NaN %d' % (
        q.median(), 100 * (q >= 1).mean(), 100 * (q >= 1.5).mean(), len(fsel), fsel.noise_x.median(), 100 * (fsel.noise_x >= 1).mean(),
        100 * (fsel.noise_x >= 1.5).mean(), fsel.noise_x.isna().sum()))

# brute-force recomputation of a few rows straight from the raw minutes (only bars <= k of d, earlier full sessions)
rng = np.random.default_rng(7)
chk = 0
for s in H.SETS:
    d = D[s].dropna(subset=['noise_x'])
    for r in d.sample(4, random_state=int(rng.integers(1e6))).itertuples():
        m = mins[r.symbol]
        loc = m.index.tz_localize(None)
        mday = m[(loc.normalize() == pd.Timestamp(r.day))]
        ts_k = pd.Timestamp(r.day + ' ' + r.time)
        upto = mday[mday.index.tz_localize(None) <= ts_k]
        P = upto.close.iloc[-1]
        o = mday.open.iloc[0]                    # = the 09:15 bar's open when present (fallback otherwise, as in the main code)
        dl = daily[r.symbol]
        cp = dl[dl.index.tz_localize(None) < pd.Timestamp(r.day)].close.iloc[-1]
        alld = pd.Series(loc.normalize()).value_counts()
        fulls = sorted(x for x in alld[alld >= FULL_BARS].index if x < pd.Timestamp(r.day))[-LOOKBACK:]
        vals = []
        for fd in fulls:
            x = m[loc.normalize() == fd]
            xl = x.index.tz_localize(None)
            c = x[xl <= fd + (ts_k - pd.Timestamp(r.day))].close.iloc[-1]
            vals.append(abs(c / x.open.iloc[0] - 1))
        sg = np.mean(vals)
        nx = (P / max(o, cp) - 1) / sg if r.side == 'LONG' else (1 - P / min(o, cp)) / sg
        assert abs(nx - r.noise_x) < 1e-9, (s, r.symbol, r.day, r.time, nx, r.noise_x)
        chk += 1
print('brute-force recomputation from raw minutes (bars <= signal minute, 14 earlier full sessions) matches on %d sampled rows' % chk)
del mins, daily

pd.to_pickle({s: D[s][['day', 'time', 'symbol', 'side', 'cash_P', 'cash_O', 'cash_Cprev', 'sigma_k', 'nhist', 'noise_x']] for s in H.SETS},
             OUT + '/noise_x.pkl')


# ------------------------------------------------------------------ pre-registered grid
def keep_mask(df, vm):
    return ~(df['noise_x'] < vm)                 # NaN noise_x passes


def S1(df):
    t = H.pick(df, df['s_fable_op'].where(keep_mask(df, 1.0)), 75, 6)
    t['pol'] = 'T3'
    return t


def S2(df):
    t = H.pick(df, df['s_fable_op'].where(keep_mask(df, 1.5)), 75, 6)
    t['pol'] = 'T3'
    return t


def S3(df):
    adj = (10.0 * (df['noise_x'] - 1.0).clip(-1.0, 1.0)).fillna(0.0)    # NaN -> unadjusted
    t = H.pick(df, df['s_fable_op'] + adj, 75, 6)
    t['pol'] = 'T3'
    return t


def S4(df):
    t = H.pick(df, df['s_opus_v3'].where(keep_mask(df, 1.0)), 75, 6)
    t['pol'] = 'T1'
    return t


GRIDSPEC = {'S1 FOP & nx>=1.0 T3': S1, 'S2 FOP & nx>=1.5 T3': S2, 'S3 FOP+10clip(nx-1) T3': S3, 'S4 v3 & nx>=1.0 T1': S4}

print('\n== NaN noise_x among each setting\'s picks (passed the filter / unadjusted), and how many picks differ from the base model')
for s in H.SETS:
    base_f = set(H.pick(D[s], 's_fable_op', 75, 6).index)
    base_v = set(H.pick(D[s], 's_opus_v3', 75, 6).index)
    parts = []
    for name, f in GRIDSPEC.items():
        t = f(D[s])
        b = base_v if name.startswith('S4') else base_f
        parts.append('%s: n %d, NaN %d, new %d, dropped %d' % (name.split()[0], len(t), int(t.noise_x.isna().sum()), len(set(t.index) - b), len(b - set(t.index))))
    print('  %-6s %s' % (s, ' | '.join(parts)))

# ------------------------------------------------------------------ design-window choice (real 12 May - 31 Aug only)
assert tuple(H.halves('real')[0]) == DESIGN          # harness 'h1' of real == the design window
_rd = H.evaluate(D, GRIDSPEC, sets=('real',))['real']
resd = {k: {'all': v['h1']} for k, v in _rd.items()}  # only the design-window part is read for the choice
b1, b2 = resd['Opus v3 (T1)']['all'], resd['Fable-OP (T3)']['all']
wd_lim = 1.25 * max(b1['worst_day'], b2['worst_day'])
dd_lim = 1.25 * max(b1['maxdd'], b2['maxdd'])
print('\n== DESIGN WINDOW: real %s..%s, OPTION net (modelled). Risk limits: worst day >= %+d, max DD >= %+d (1.25x the better baseline per metric)' % (
    DESIGN[0], DESIGN[1], wd_lim, dd_lim))
print('  %-30s %5s %10s %8s %6s %10s %10s %10s %s' % ('model', 'n', 'opt net', '/trade', 'T1%', 'worst day', 'max DD', 'futures', 'risk ok'))
elig = {}
for name, r in resd.items():
    a = r['all']
    ok = a['worst_day'] >= wd_lim and a['maxdd'] >= dd_lim
    if name in GRIDSPEC:
        elig[name] = (ok, a['net'])
    print('  %-30s %5d %+10d %+8d %6.1f %+10d %+10d %+10d %s' % (name, a['n'], a['net'], a['per_trade'], a['hit_T1%'], a['worst_day'], a['maxdd'], a['fut'],
                                                              ('yes' if ok else 'NO') if name in GRIDSPEC else '(baseline)'))
ok_names = [k for k, (ok, _) in elig.items() if ok]
if ok_names:
    CHOSEN, flag = max(ok_names, key=lambda k: elig[k][1]), ''
else:
    CHOSEN, flag = max(elig, key=lambda k: elig[k][1]), '  [FLAG: no setting met the design risk limits; highest net taken]'
print('CHOSEN on design window: %s (opt net %+d)%s' % (CHOSEN, elig[CHOSEN][1], flag))

# ------------------------------------------------------------------ full comparison (candidate vs the three baselines, every set)
print('\n######## CANDIDATE (chosen on design window) vs baselines, all sets ########')
CAND = 'NA ' + CHOSEN
res = H.compare(D, {CAND: GRIDSPEC[CHOSEN]})

print('\n######## all four pre-registered grid settings (reference only; the choice above used the design window) ########')
res_grid = H.evaluate(D, GRIDSPEC)
H.show(res_grid)

# diagnostic: the Fable-OP baseline picks split by noise_x (what the filter removes), all sets
print('\n== diagnostic: Fable-OP (T3) baseline picks split by noise_x (option net / futures net)')
for s in H.SETS:
    t = H.run(D[s], ('s_fable_op', 75, 'T3', 6))
    for lab, msk in (('nx<1.0', t.noise_x < 1.0), ('1.0<=nx<1.5', (t.noise_x >= 1.0) & (t.noise_x < 1.5)), ('nx>=1.5', t.noise_x >= 1.5), ('nx NaN', t.noise_x.isna())):
        x = t[msk]
        print('  %-6s %-12s n %4d  opt %+10d  (/trade %+6d)  fut %+10d  T1%% %5.1f' % (s, lab, len(x), x.pnl.sum(), x.pnl.mean() if len(x) else 0, x.fut.sum(),
                                                                                 100 * (x.status_T1 == 'target').mean() if len(x) else 0))


# ------------------------------------------------------------------ the bar
def g(s, m, part='all'):
    return res[s][m][part]


ub, rb = 'Opus v3 (T1)', 'Fable-OP (T3)'
beat_u = g('unseen', CAND)['net'] > max(g('unseen', ub)['net'], g('unseen', rb)['net'])
beat_r2 = g('real', CAND, 'h2')['net'] > max(g('real', ub, 'h2')['net'], g('real', rb, 'h2')['net'])
beat_sw = g('unseen', CAND)['net'] > g('unseen', 'Switch-1')['net'] and g('real', CAND, 'h2')['net'] > g('real', 'Switch-1', 'h2')['net']
risk = {}
for s, part in (('unseen', 'all'), ('real', 'h2')):
    bw = max(g(s, ub, part)['worst_day'], g(s, rb, part)['worst_day'])
    bd = max(g(s, ub, part)['maxdd'], g(s, rb, part)['maxdd'])
    c = g(s, CAND, part)
    risk[s + '_' + part] = {'worst_day': c['worst_day'], 'lim_wd': 1.25 * bw, 'maxdd': c['maxdd'], 'lim_dd': 1.25 * bd,
                            'ok': bool(c['worst_day'] >= 1.25 * bw and c['maxdd'] >= 1.25 * bd)}
risk_ok = all(v['ok'] for v in risk.values())
print('\n== BAR (option net): beats both on unseen: %s | beats both on real 2nd half: %s | beats Switch-1 on both: %s | risk ok: %s' % (beat_u, beat_r2, beat_sw, risk_ok))
for k, v in risk.items():
    print('   %-12s worst day %+d (limit %+d)  max DD %+d (limit %+d)  ok=%s' % (k, v['worst_day'], v['lim_wd'], v['maxdd'], v['lim_dd'], v['ok']))

rows = []
for s in H.SETS:
    for mname in [CAND, 'Opus v3 (T1)', 'Fable-OP (T3)', 'Switch-1']:
        r = res[s][mname]
        for part, lab in (('all', s), ('h1', s + '_h1'), ('h2', s + '_h2')):
            a = r[part]
            rows.append({'set': lab, 'model': mname, 'n': a['n'], 'net': a['net'], 'fut_net': a['fut'], 'per_trade': a['per_trade'], 'hit_T1_pct': a['hit_T1%'],
                         'stop_pct': a['stop%'], 'days_up': a['days_up'], 'days_dn': a['days_dn'], 'worst_day': a['worst_day'], 'maxdd': a['maxdd'],
                         'h1_net': r['h1']['net'] if part == 'all' else (a['net'] if part == 'h1' else 0),
                         'h2_net': r['h2']['net'] if part == 'all' else (a['net'] if part == 'h2' else 0)})
json.dump({'chosen': CHOSEN, 'chosen_flag': flag.strip(), 'design': resd, 'design_limits': {'worst_day': wd_lim, 'maxdd': dd_lim},
           'evaluate': res, 'evaluate_grid_all': res_grid, 'rows': rows, 'feature_stats': stat,
           'bar': {'beats_both_unseen': bool(beat_u), 'beats_both_real_h2': bool(beat_r2), 'beats_switch1_both': bool(beat_sw), 'risk_ok': risk_ok, 'risk': risk}},
          open(OUT + '/results.json', 'w'), indent=1, default=float)
print('\nsaved', OUT + '/results.json')
