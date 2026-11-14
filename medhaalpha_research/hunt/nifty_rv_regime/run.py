"""nifty_rv_regime: Nifty intraday realised-volatility state as an exit switch / day filter (pre-registered test).

RV(d,t)   = sqrt(sum r_i^2), r_0 = ln(C_0915/O_0915), r_i = ln(C_i/C_{i-1}) for bars 09:16..t (t = signal bar, inclusive).
rv_ratio  = RV(d,t) / mean RV(d',t) at the same clock bar over the 14 previous full sessions (>= 10 needed, else NaN).
pd_ratio  = full-session RV of d-1 / mean full-session RV over the 14 sessions before d-1 (>= 10 needed, else NaN).
Sessions with < 300 Nifty bars (Muhurat) are dropped from every history.
q33       = 33rd percentile of rv_ratio over ALL A/B rows of real 12 May-31 Aug 2026 (design window), frozen.
Grid (chosen on the design window by option net, subject to worst day / max DD <= 1.25x the better design baseline):
  S1 Fable-OP>=75, T3 if rv_ratio>=1 else T1 (NaN -> T3)
  S2 Fable-OP masked where rv_ratio<q33 (before pick), T3
  S3 Opus v3>=75, CLOSE_TR if rv_ratio>=1 else T1 (NaN -> T1)
  S4 = S1 with pd_ratio
"""
import json, os, sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/nifty_rv_regime'
sys.path.insert(0, SP + '/hunt')
import harness as H

assert H.METRIC == 'opt'
DESIGN = ('2026-05-12', '2026-08-31')
LOOKBACK, MINP = 14, 10

# ------------------------------------------------------------------ Nifty realised volatility (loaded once)
mins, daily, nifty, lot = H.minute_data()
del mins, daily, lot
nf = nifty.copy()
nf['day'] = nf.index.strftime('%Y-%m-%d')
nf['hm'] = nf.index.strftime('%H:%M')
cnt = nf.groupby('day').size()
full_days = sorted(cnt[cnt >= 300].index)
dropped = sorted(cnt[cnt < 300].index)
print('Nifty minutes: %d sessions, %d full (>=300 bars); dropped: %s' % (len(cnt), len(full_days), ', '.join('%s (%d bars)' % (d, cnt[d]) for d in dropped)))

GRID = pd.date_range('2000-01-01 09:15', '2000-01-01 15:29', freq='1min').strftime('%H:%M')
HM_IDX = {h: i for i, h in enumerate(GRID)}
rv = np.full((len(full_days), len(GRID)), np.nan)
n_missing = 0
for k, d in enumerate(full_days):
    x = nf[nf.day == d].set_index('hm')
    x = x[~x.index.duplicated()]
    xr = x.reindex(GRID)
    n_missing += int(xr.close.isna().sum())
    c = xr.close.ffill().to_numpy(float)          # a missing bar contributes 0 and the next return spans the gap
    o0 = float(xr.open.iloc[0]) if np.isfinite(xr.open.iloc[0]) else float(x.open.iloc[0])
    r = np.empty(len(GRID))
    r[0] = np.log(c[0] / o0)
    r[1:] = np.log(c[1:] / c[:-1])
    r = np.nan_to_num(r)
    rv[k] = np.sqrt(np.cumsum(r * r))
print('missing bars inside full sessions (forward-filled):', n_missing)
RV = pd.DataFrame(rv, index=full_days, columns=GRID)
BASEMEAN = RV.rolling(LOOKBACK, min_periods=MINP).mean().shift(1)     # 14 previous full sessions, same clock bar
RATIO = RV / BASEMEAN
FS = RV[GRID[-1]]                                                        # full-session RV (09:15-15:29)
PD = FS.shift(1) / FS.rolling(LOOKBACK, min_periods=MINP).mean().shift(2)  # d-1 vs the 14 sessions before d-1

# no-look-ahead self check: ratio at (d,t) recomputed from bars <= t of d and earlier sessions only
_chk_d, _chk_t = full_days[40], '10:31'
_sub = nf[(nf.day == _chk_d) & (nf.hm <= _chk_t)]
_r = np.r_[np.log(_sub.close.iloc[0] / _sub.open.iloc[0]), np.diff(np.log(_sub.close.to_numpy()))]
_prev = [RV.loc[full_days[j], _chk_t] for j in range(40 - LOOKBACK, 40)]
assert abs(np.sqrt((_r ** 2).sum()) / np.mean(_prev) - RATIO.loc[_chk_d, _chk_t]) < 1e-12
pd.to_pickle({'RATIO': RATIO, 'PD': PD, 'RV': RV}, OUT + '/ratios.pkl')    # for the exploratory diagnostics (diag.py)


def attach(df):
    df = df.copy()
    ti = df['time'].map(HM_IDX).to_numpy()
    di = df['day'].map({d: i for i, d in enumerate(full_days)})
    ok = di.notna().to_numpy()
    v = np.full(len(df), np.nan)
    v[ok] = RATIO.to_numpy()[di[ok].astype(int).to_numpy(), ti[ok]]
    df['rv_ratio'] = v
    df['pd_ratio'] = df['day'].map(PD).astype(float)
    return df


D = H.load_all()
for s in H.SETS:
    D[s] = attach(D[s])
    d = D[s]
    print('%-6s rows %5d  rv_ratio NaN %d  median %.3f  >=1: %.1f%%  | pd_ratio NaN %d  median %.3f' % (
        s, len(d), d.rv_ratio.isna().sum(), d.rv_ratio.median(), 100 * (d.rv_ratio >= 1).mean(), d.pd_ratio.isna().sum(), d.pd_ratio.median()))

dz = D['real']
dz = dz[(dz.day >= DESIGN[0]) & (dz.day <= DESIGN[1])]
Q33 = float(np.nanpercentile(dz.rv_ratio, 33))
print('q33 (33rd pct of rv_ratio over all %d A/B rows of real %s..%s, %d non-NaN) = %.4f  (frozen)' % (len(dz), DESIGN[0], DESIGN[1], dz.rv_ratio.notna().sum(), Q33))


# ------------------------------------------------------------------ pre-registered grid
def S1(df):
    t = H.pick(df, 's_fable_op', 75, 6)
    t['pol'] = np.where(t.rv_ratio < 1.0, 'T1', 'T3')         # NaN -> T3 (base)
    return t


def S2(df):
    sc = df['s_fable_op'].where(~(df['rv_ratio'] < Q33))       # NaN rv_ratio is not masked
    t = H.pick(df, sc, 75, 6)
    t['pol'] = 'T3'
    return t


def S3(df):
    t = H.pick(df, 's_opus_v3', 75, 6)
    t['pol'] = np.where(t.rv_ratio >= 1.0, 'CLOSE_TR', 'T1')   # NaN -> T1 (base)
    return t


def S4(df):
    t = H.pick(df, 's_fable_op', 75, 6)
    t['pol'] = np.where(t.pd_ratio < 1.0, 'T1', 'T3')         # NaN -> T3 (base)
    return t


GRIDSPEC = {'S1 FOP T3|T1 by rv_ratio': S1, 'S2 FOP skip rv<q33 T3': S2, 'S3 v3 CLOSE_TR|T1 by rv': S3, 'S4 FOP T3|T1 by pd_ratio': S4}

# ------------------------------------------------------------------ design-window choice (real 12 May - 31 Aug only)
assert tuple(H.halves('real')[0]) == DESIGN          # harness 'h1' of real == the design window
_rd = H.evaluate(D, GRIDSPEC, sets=('real',))['real']
resd = {k: {'all': v['h1']} for k, v in _rd.items()}  # only the design-window part is read for the choice
b1, b2 = resd['Opus v3 (T1)']['all'], resd['Fable-OP (T3)']['all']
wd_lim = 1.25 * max(b1['worst_day'], b2['worst_day'])
dd_lim = 1.25 * max(b1['maxdd'], b2['maxdd'])
print('\n== DESIGN WINDOW: real %s..%s, OPTION net (modelled). Risk limits: worst day >= %+d, max DD >= %+d (1.25x the better baseline per metric)' % (DESIGN[0], DESIGN[1], wd_lim, dd_lim))
print('  %-30s %5s %10s %8s %6s %10s %10s %10s %s' % ('model', 'n', 'opt net', '/trade', 'T1%', 'worst day', 'max DD', 'futures', 'risk ok'))
elig = {}
for name, r in resd.items():
    a = r['all']
    ok = a['worst_day'] >= wd_lim and a['maxdd'] >= dd_lim
    if name in GRIDSPEC:
        elig[name] = (ok, a['net'])
    print('  %-30s %5d %+10d %+8d %6.1f %+10d %+10d %+10d %s' % (name, a['n'], a['net'], a['per_trade'], a['hit_T1%'], a['worst_day'], a['maxdd'], a['fut'], ('yes' if ok else 'NO') if name in GRIDSPEC else '(baseline)'))
ok_names = [k for k, (ok, _) in elig.items() if ok]
if ok_names:
    CHOSEN = max(ok_names, key=lambda k: elig[k][1])
    flag = ''
else:
    CHOSEN = max(elig, key=lambda k: elig[k][1])
    flag = '  [FLAG: no setting met the design risk limits; highest net taken]'
print('CHOSEN on design window: %s (opt net %+d)%s' % (CHOSEN, elig[CHOSEN][1], flag))

# policy mix of the chosen setting on each set (diagnostic)
for s in H.SETS:
    t = GRIDSPEC[CHOSEN](D[s])
    print('  %-6s chosen picks %4d, pol mix %s, NaN ratio rows %d' % (s, len(t), dict(t['pol'].value_counts()), int(t[['rv_ratio', 'pd_ratio']].isna().any(axis=1).sum())))

# ------------------------------------------------------------------ full comparison (candidate vs the three baselines, every set)
print('\n######## CANDIDATE (chosen on design window) vs baselines, all sets ########')
CAND = 'RV ' + CHOSEN
res = H.compare(D, {CAND: GRIDSPEC[CHOSEN]})

print('\n######## all four pre-registered grid settings (reference only; the choice above used the design window) ########')
res_grid = H.evaluate(D, GRIDSPEC)
H.show(res_grid)

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

json.dump({'q33': Q33, 'chosen': CHOSEN, 'chosen_flag': flag.strip(), 'design': resd, 'evaluate': res, 'evaluate_grid_all': res_grid,
           'bar': {'beats_both_unseen': bool(beat_u), 'beats_both_real_h2': bool(beat_r2), 'beats_switch1_both': bool(beat_sw), 'risk_ok': risk_ok, 'risk': risk}},
          open(OUT + '/results.json', 'w'), indent=1, default=float)
print('\nsaved', OUT + '/results.json')
