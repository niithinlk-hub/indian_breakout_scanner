"""prior_compression: prior-day range compression bonus (NR4 / NR7 / triangle) and no same-direction trade after a prior
trend day (Zarattini et al. Table 5; Crabel; Unofficed NR7 F&O test). Pre-registered; implemented as specified.

Flags per (symbol, day d), pre-open, from the stock's CASH daily candles (H.minute_data(), from Jan 2024), candles dated
strictly before d only. Short sessions (fewer than 300 Nifty minute bars, e.g. Muhurat) are dropped before computing
patterns. Index the last full sessions before d as d-1, d-2, ...; rng = High - Low.
  NR4       rng[d-1] == min(rng[d-4..d-1])          NR7  rng[d-1] == min(rng[d-7..d-1])
  Triangle  High[d-1] < min(High[d-2], High[d-3]) and Low[d-1] > max(Low[d-2], Low[d-3])
  compressed = NR4 or NR7 or Triangle
  trend day, LONG : Open[d-1] <= Low + 0.15 rng and Close[d-1] >= Low + 0.85 rng and rng[d-1] > mean(rng[d-15..d-2])
  trend day, SHORT: Open[d-1] >= Low + 0.85 rng and Close[d-1] <= Low + 0.15 rng and the same range condition
  (trend_same = the trend-day flag in the row's trade direction). Fewer than 16 prior sessions: no flags.
Grid (adjust/mask before pick):
  S1 s_fable_op + 10*compressed, pick(75, 6), T3            S2 s_fable_op, NaN where trend_same, pick(75, 6), T3
  S3 S1 + S2 on s_fable_op, T3                               S4 S1 + S2 on s_opus_v3, T1
Choice on real 12 May-31 Aug 2026 by OPTION net, subject to design worst day and max DD no worse than 1.25x the better
design baseline (per metric); else highest net, flagged.
"""
import json, sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/prior_compression/verify'
sys.path.insert(0, SP + '/hunt')
import harness as H

assert H.METRIC == 'opt'
DESIGN = ('2026-05-12', '2026-08-31')
FULL_BARS, MIN_HIST, BONUS = 300, 16, 10.0

D = H.load_all()
need = {}                                                  # symbol -> set of days carrying signals (any set)
for s in H.SETS:
    for sym, g in D[s].groupby('symbol'):
        need.setdefault(sym, set()).update(g.day.unique())

# ------------------------------------------------------------------ data, loaded once
mins, daily, nifty, lot = H.minute_data()
del lot
nifty_cnt = pd.Series(nifty.index.tz_localize(None).normalize()).value_counts().sort_index()
NIFTY_FIRST = nifty_cnt.index.min()
SHORT_DAYS = set(nifty_cnt[nifty_cnt < FULL_BARS].index.strftime('%Y-%m-%d'))
print('Nifty minute days %d (%s..%s); short sessions (< %d Nifty bars) dropped from the daily history: %s' % (
    len(nifty_cnt), nifty_cnt.index.min().date(), nifty_cnt.index.max().date(), FULL_BARS,
    {k: int(nifty_cnt[pd.Timestamp(k)]) for k in sorted(SHORT_DAYS)}))
print('  (daily candles dated before %s have no Nifty minutes to count bars; they are kept as full sessions. The only special '
      'session in that span, Muhurat 1 Nov 2024, is > 200 sessions before the first signal day and cannot enter any lookback)'
      % NIFTY_FIRST.date())

# sanity: daily candle OHLC vs the cash minutes of the same day (09:15-15:29), random sample of full sessions
rng_ = np.random.default_rng(11)
diffs = []
syms = sorted(need)
for sym in map(str, rng_.choice(syms, 40, replace=False)):
    m, dl = mins[sym], daily[sym]
    ml = m.index.tz_localize(None)
    md = pd.Series(ml.normalize())
    dli = dl.index.tz_localize(None).normalize()
    for day in map(str, rng_.choice(sorted(set(md.dt.strftime('%Y-%m-%d')) - SHORT_DAYS), 5, replace=False)):
        x = m[(md == pd.Timestamp(day)).to_numpy()]
        x = x[(x.index.tz_localize(None).time >= pd.Timestamp('09:15').time()) & (x.index.tz_localize(None).time <= pd.Timestamp('15:29').time())]
        y = dl[dli == pd.Timestamp(day)]
        if len(x) < FULL_BARS or len(y) != 1:
            continue
        y = y.iloc[0]
        diffs.append([abs(x.open.iloc[0] / y.open - 1), abs(x.high.max() / y.high - 1), abs(x.low.min() / y.low - 1), abs(x.close.iloc[-1] / y.close - 1)])
diffs = np.array(diffs) * 100
print('daily candle vs minute-built OHLC on %d sampled stock-days: median abs diff %% O/H/L/C = %s, p95 = %s' % (
    len(diffs), np.round(np.median(diffs, 0), 4).tolist(), np.round(np.quantile(diffs, 0.95, axis=0), 4).tolist()))
del mins, nifty

# ------------------------------------------------------------------ flags
FLAGS = {}
stat = dict(stock_days_hist=0, short_dropped=0, no_hist=0, zero_rng=0)
for sym in sorted(need):
    dl = daily[sym]
    dts = dl.index.tz_localize(None).normalize().strftime('%Y-%m-%d').to_numpy()
    keep = ~np.isin(dts, list(SHORT_DAYS))
    stat['short_dropped'] += int((~keep).sum())
    dts = dts[keep]
    o, h, l, c = (dl[k].to_numpy(float)[keep] for k in ('open', 'high', 'low', 'close'))
    assert np.all(dts[1:] > dts[:-1]), sym
    stat['stock_days_hist'] += len(dts)
    r = h - l
    for day in need[sym]:
        j = int(np.searchsorted(dts, day, 'left'))          # number of full sessions strictly before d; d-1 = index j-1
        f = dict(nprior=j, nr4=False, nr7=False, tri=False, comp=False, trend_long=False, trend_short=False, has=False,
                 prev_close=c[j - 1] if j > 0 else np.nan, prev_day=dts[j - 1] if j > 0 else None)
        if j < MIN_HIST:
            stat['no_hist'] += 1
            FLAGS[(sym, day)] = f
            continue
        i1 = j - 1
        R1 = r[i1]
        stat['zero_rng'] += int(R1 <= 0)
        nr4 = R1 == r[j - 4:j].min()
        nr7 = R1 == r[j - 7:j].min()
        tri = (h[i1] < min(h[i1 - 1], h[i1 - 2])) and (l[i1] > max(l[i1 - 1], l[i1 - 2]))
        big = R1 > r[i1 - 14:i1].mean()                     # 14 sessions before d-1: d-15..d-2
        tl = (o[i1] <= l[i1] + 0.15 * R1) and (c[i1] >= l[i1] + 0.85 * R1) and big
        ts = (o[i1] >= l[i1] + 0.85 * R1) and (c[i1] <= l[i1] + 0.15 * R1) and big
        f.update(nr4=bool(nr4), nr7=bool(nr7), tri=bool(tri), comp=bool(nr4 or nr7 or tri), trend_long=bool(tl), trend_short=bool(ts), has=True)
        FLAGS[(sym, day)] = f
print('flag build: %d symbols, %d stock-day daily candles kept, %d short-session candles dropped, %d (symbol, signal day) pairs '
      'with < %d prior sessions (no flags), %d with zero prior-day range' % (len(need), stat['stock_days_hist'], stat['short_dropped'],
                                                                         stat['no_hist'], MIN_HIST, stat['zero_rng']))


def attach(df):
    df = df.copy()
    F = [FLAGS[(s, d)] for s, d in zip(df.symbol, df.day)]
    for k in ('nr4', 'nr7', 'tri', 'comp', 'has', 'nprior', 'prev_close', 'prev_day'):
        df['pc_' + k] = [f[k] for f in F]
    lg = (df.side == 'LONG').to_numpy()
    df['pc_trend_same'] = np.where(lg, [f['trend_long'] for f in F], [f['trend_short'] for f in F])
    df['pc_trend_opp'] = np.where(lg, [f['trend_short'] for f in F], [f['trend_long'] for f in F])
    return df


for s in H.SETS:
    D[s] = attach(D[s])

# ------------------------------------------------------------------ alignment / no-look-ahead checks
print('\n== alignment checks (d-1 must be the session before the signal day)')
for s in H.SETS:
    d = D[s]
    sg = np.where(d.side == 'LONG', 1.0, -1.0)
    implied_pc = d.price / (1 + sg * d.day_chg / 100)        # previous close implied by the row's own day_chg
    rel = (implied_pc / d.pc_prev_close - 1).abs() * 100
    print('  %-6s previous close implied by harness day_chg vs daily Close[d-1]: median abs diff %.3f%%, p95 %.3f%%, > 1%% %d of %d '
          '(%s); prior sessions min %d; rows without flags %d' % (s, rel.median(), rel.quantile(.95), int((rel > 1).sum()), len(d),
                                                                 'futures price vs cash close' if s == 'real' else 'cash vs cash',
                                                                 int(d.pc_nprior.min()), int((~d.pc_has).sum())))
    assert (d.pc_prev_day < d.day).all()                     # only candles dated before d are used
# brute-force recomputation of sampled rows from the raw daily candles (dated < d, short sessions removed)
chk = 0
for s in H.SETS:
    d = D[s]
    for r in d.sample(25, random_state={'real': 1, 'unseen': 2, 'known': 3}[s]).itertuples():
        dl = daily[r.symbol]
        x = dl[dl.index.tz_localize(None).normalize() < pd.Timestamp(r.day)]
        x = x[~x.index.tz_localize(None).normalize().strftime('%Y-%m-%d').isin(list(SHORT_DAYS))]
        R = (x.high - x.low).to_numpy()
        nr4 = R[-1] == R[-4:].min()
        nr7 = R[-1] == R[-7:].min()
        tri = x.high.iloc[-1] < min(x.high.iloc[-2], x.high.iloc[-3]) and x.low.iloc[-1] > max(x.low.iloc[-2], x.low.iloc[-3])
        o1, l1, c1 = x.open.iloc[-1], x.low.iloc[-1], x.close.iloc[-1]
        big = R[-1] > np.mean(R[-15:-1])
        if r.side == 'LONG':
            tr = o1 <= l1 + 0.15 * R[-1] and c1 >= l1 + 0.85 * R[-1] and big
        else:
            tr = o1 >= l1 + 0.85 * R[-1] and c1 <= l1 + 0.15 * R[-1] and big
        assert (bool(nr4 or nr7 or tri), bool(tr)) == (bool(r.pc_comp), bool(r.pc_trend_same)), (s, r.symbol, r.day)
        chk += 1
print('  brute-force recomputation from raw daily candles (dated < d, short sessions removed) matches on %d sampled rows' % chk)
del daily

# ------------------------------------------------------------------ flag frequencies
print('\n== flag frequencies (share of rows, %); fop = rows with s_fable_op >= 75, v3 = rows with s_opus_v3 >= 75')
print('  %-6s %-8s %6s %6s %6s %6s %6s %8s %8s' % ('set', 'rows', 'n', 'NR4', 'NR7', 'tri', 'comp', 'trendSame', 'trendOpp'))
freq = {}
for s in H.SETS:
    d = D[s]
    for lab, x in (('all', d), ('long', d[d.side == 'LONG']), ('short', d[d.side == 'SHORT']), ('fop>=75', d[d.s_fable_op >= 75]),
                   ('fop65-75', d[(d.s_fable_op >= 65) & (d.s_fable_op < 75)]), ('v3>=75', d[d.s_opus_v3 >= 75])):
        q = {k: round(100 * float(x['pc_' + k].mean()), 1) for k in ('nr4', 'nr7', 'tri', 'comp', 'trend_same', 'trend_opp')}
        q['n'] = int(len(x))
        freq['%s|%s' % (s, lab)] = q
        print('  %-6s %-8s %6d %6.1f %6.1f %6.1f %6.1f %8.1f %8.1f' % (s, lab, len(x), q['nr4'], q['nr7'], q['tri'], q['comp'], q['trend_same'], q['trend_opp']))


# ------------------------------------------------------------------ pre-registered grid
def adj(df, base, bonus=True, mask=True):
    sc = df[base].astype(float)
    if bonus:
        sc = sc + BONUS * df['pc_comp'].astype(float)
    if mask:
        sc = sc.where(~df['pc_trend_same'].astype(bool))
    return sc


def S1(df):
    t = H.pick(df, adj(df, 's_fable_op', True, False), 75, 6)
    t['pol'] = 'T3'
    return t


def S2(df):
    t = H.pick(df, adj(df, 's_fable_op', False, True), 75, 6)
    t['pol'] = 'T3'
    return t


def S3(df):
    t = H.pick(df, adj(df, 's_fable_op', True, True), 75, 6)
    t['pol'] = 'T3'
    return t


def S4(df):
    t = H.pick(df, adj(df, 's_opus_v3', True, True), 75, 6)
    t['pol'] = 'T1'
    return t


GRIDSPEC = {'S1 FOP+10comp T3': S1, 'S2 FOP no-trendSame T3': S2, 'S3 FOP+10comp,no-tS T3': S3, 'S4 v3+10comp,no-tS T1': S4}

print('\n== picks of each setting vs its base model (new = picked only by the setting, dropped = base picks it loses)')
for s in H.SETS:
    base_f = set(H.pick(D[s], 's_fable_op', 75, 6).index)
    base_v = set(H.pick(D[s], 's_opus_v3', 75, 6).index)
    parts = []
    for name, f in GRIDSPEC.items():
        t = f(D[s])
        b = base_v if name.startswith('S4') else base_f
        parts.append('%s: n %d, comp %d, new %d, dropped %d' % (name.split()[0], len(t), int(t.pc_comp.sum()), len(set(t.index) - b), len(b - set(t.index))))
    print('  %-6s %s' % (s, ' | '.join(parts)))

# ------------------------------------------------------------------ design-window choice (real 12 May - 31 Aug only)
assert tuple(H.halves('real')[0]) == DESIGN
_rd = H.evaluate(D, GRIDSPEC, sets=('real',))['real']
resd = {k: {'all': v['h1']} for k, v in _rd.items()}      # only the design-window half is read for the choice
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

# ------------------------------------------------------------------ full comparison
print('\n######## CANDIDATE (chosen on design window) vs baselines, all sets ########')
CAND = 'PC ' + CHOSEN
res = H.compare(D, {CAND: GRIDSPEC[CHOSEN]})

print('\n######## all four pre-registered grid settings (reference only; the choice above used the design window) ########')
res_grid = H.evaluate(D, GRIDSPEC)
H.show(res_grid)

# diagnostic: baseline picks split by flag (what the bonus / mask act on)
print('\n== diagnostic: baseline picks split by flag (option net / futures net)')
for s in H.SETS:
    for bname, spec in (('FOP T3', ('s_fable_op', 75, 'T3', 6)), ('v3 T1', ('s_opus_v3', 75, 'T1', 6))):
        t = H.run(D[s], spec)
        for lab, msk in (('compressed', t.pc_comp), ('not comp', ~t.pc_comp), ('trendSame', t.pc_trend_same.astype(bool))):
            x = t[msk]
            print('  %-6s %-6s %-10s n %4d  opt %+10d  (/trade %+6d)  fut %+10d  T1%% %5.1f' % (
                s, bname, lab, len(x), x.pnl.sum(), x.pnl.mean() if len(x) else 0, x.fut.sum(), 100 * (x.status_T1 == 'target').mean() if len(x) else 0))
# diagnostic: the S1 bonus entrants (picked by S1 only: base score 65-74.9 on a compressed day)
print('\n== diagnostic: trades that S1 adds / drops vs Fable-OP T3 (option net / futures net)')
for s in H.SETS:
    ta, tb = H.run(D[s], S1), H.run(D[s], ('s_fable_op', 75, 'T3', 6))
    add, drop = ta[~ta.index.isin(tb.index)], tb[~tb.index.isin(ta.index)]
    print('  %-6s added n %3d opt %+9d fut %+9d | dropped n %3d opt %+9d fut %+9d' % (s, len(add), add.pnl.sum(), add.fut.sum(), len(drop), drop.pnl.sum(), drop.fut.sum()))


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
           'evaluate': res, 'evaluate_grid_all': res_grid, 'rows': rows, 'flag_freq': freq, 'flag_build': stat,
           'bar': {'beats_both_unseen': bool(beat_u), 'beats_both_real_h2': bool(beat_r2), 'beats_switch1_both': bool(beat_sw), 'risk_ok': risk_ok, 'risk': risk}},
          open(OUT + '/results.json', 'w'), indent=1, default=float)
print('\nsaved', OUT + '/results.json')
