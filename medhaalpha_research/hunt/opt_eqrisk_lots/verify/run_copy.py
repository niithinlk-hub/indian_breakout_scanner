"""opt_eqrisk_lots: equal option-risk lot sizing at the baseline's total premium outlay.

Pre-registered test (implemented as specified; deviations listed in DEVIATIONS below and printed):
  Picks unchanged: t = H.pick(df, S, 75, 6), S = s_fable_op (exit T3) or s_opus_v3 (exit T1).
  Per picked row: ATM option (K = F0), p0 = B76 premium at entry, pS = B76 premium with the underlying at the futures
  stop and no decay. lot = 'lot' column (unseen/known); on real the known set's lot for the symbol on the nearest
  date <= day (else nearest after); if o_qty % lot != 0, lot = o_qty (one lot). fut_lots = o_qty / lot.
  Per-lot option loss at the stop Ll = 1.2*(p0-pS)*lot + opt_costs(p0, pS, lot).
  New lots L = clip(floor(B/Ll), 1, cap*fut_lots); pnl = option_net(t, pol, qty=L*lot);
  futures reference = net_<pol> * L / fut_lots.
  B_eq: bisection over Rs 1,000-60,000 (tol Rs 10) on the DESIGN-window picks of that setting so that
  sum(new outlay) = sum(p0 * o_qty); then frozen.
Grid: (a) Fable-OP T3 cap 2x B_eq  (b) Fable-OP T3 cap 3x B_eq  (c) Opus v3 T1 cap 3x B_eq (own)
      (d) Fable-OP T3 cap 3x B = Rs 15,000 (leverage variant, always reported separately, not eligible for the choice)
Choice on the design window (real 12 May-31 Aug 2026) by option net among (a)-(c) whose design option worst day and
max DD are no worse than 1.25x the better design baseline (else highest net, flagged).
"""
import json, os, sys
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/opt_eqrisk_lots/verify'
sys.path.insert(0, SP + '/hunt')
import harness as H

assert H.METRIC == 'opt'
pd.set_option('display.width', 220)
D = H.load_all()
DES_LO, DES_HI = '2026-05-12', '2026-08-31'
PAD = 1.2
B_LO, B_HI, B_TOL = 1000.0, 60000.0, 10.0

DEVIATIONS = [
    "Real-set lot fallback for symbols absent from the known set (no known lot on any date): the rule has no case for "
    "this; lot = o_qty (treated as one lot), the rule's own fallback for an unverifiable lot.",
    "Harness run() always recomputes 'fut' from net_<pol>; to show futures at the new lots in the harness 'futures' "
    "column, the trade function returns a copy whose net_<pol> = net_<pol> * L / fut_lots (the original column in D "
    "is untouched).",
]

# ------------------------------------------------------------------------------------------------ lots
_K = D['known'][['symbol', 'day', 'lot']].drop_duplicates().sort_values(['symbol', 'day'], kind='stable')
KLOT = {s: (g.day.to_numpy(), g.lot.to_numpy(float)) for s, g in _K.groupby('symbol')}


def row_lots(t):
    """lot per picked row and a flag ('' exact, 'absent' no known lot -> one lot, 'mismatch' o_qty % lot != 0 -> one lot)."""
    q = t['o_qty'].to_numpy(float)
    if 'lot' in t.columns:                                   # unseen / known: exact
        return t['lot'].to_numpy(float), np.array([''] * len(t), dtype=object)
    lots, flag = [], []
    for s, d, qq in zip(t['symbol'], t['day'], q):           # real: from the known set
        if s in KLOT:
            days, ls = KLOT[s]
            i = np.searchsorted(days, d, side='right') - 1
            l = ls[i] if i >= 0 else ls[0]
            if qq % l != 0:
                lots.append(qq); flag.append('mismatch')
            else:
                lots.append(l); flag.append('')
        else:
            lots.append(qq); flag.append('absent')
    return np.array(lots, float), np.array(flag, dtype=object)


def prep(t):
    """Per-row sizing inputs (independent of B and cap)."""
    call = (t['o_kind'] == 'CE').to_numpy()
    sgn = np.where(call, 1.0, -1.0)
    F0 = t['o_F0'].to_numpy(float)
    K = F0
    T0 = H._years(t['o_entry_ts'], t['o_expiry'])
    s = t['o_iv'].to_numpy(float)
    p0 = H._b76(F0, K, T0, s, call)
    pS = H._b76(F0 - sgn * t['o_risk_abs'].to_numpy(float), K, T0, s, call)
    lot, flag = row_lots(t)
    q0 = t['o_qty'].to_numpy(float)
    fut_lots = q0 / lot
    Ll = PAD * (p0 - pS) * lot + H.opt_costs(p0, pS, lot)
    return pd.DataFrame({'p0': p0, 'pS': pS, 'lot': lot, 'flag': flag, 'q0': q0, 'fut_lots': fut_lots, 'Ll': Ll}, index=t.index)


def new_lots(P, cap, B):
    return np.clip(np.floor(B / P['Ll'].to_numpy()), 1.0, cap * P['fut_lots'].to_numpy())


def make(score, pol, cap, B):
    def f(df):
        t = H.pick(df, score, 75, 6).copy()
        P = prep(t)
        L = new_lots(P, cap, B)
        qty = L * P['lot'].to_numpy()
        t['pol'] = pol
        t['new_lots'], t['fut_lots'], t['new_qty'], t['lot_used'], t['lot_flag'] = L, P['fut_lots'].to_numpy(), qty, P['lot'].to_numpy(), P['flag'].to_numpy()
        det = H.option_net(t, pol, qty=qty, detail=True)
        t['pnl'] = det['net'].to_numpy()
        t['outlay'] = det['outlay'].to_numpy()
        t['outlay_base'] = (P['p0'] * P['q0']).to_numpy()
        t['Ll'] = P['Ll'].to_numpy()
        t['fut_base'] = t['net_' + pol]
        t['net_' + pol] = t['net_' + pol] * L / P['fut_lots'].to_numpy()       # futures reference at the new lots
        return t
    return f


def design_df():
    d = D['real']
    return d[(d.day >= DES_LO) & (d.day <= DES_HI)]


def b_eq(score, cap):
    """Bisection on the DESIGN-window picks of this setting only."""
    t = H.pick(design_df(), score, 75, 6)
    P = prep(t)
    target = float((P.p0 * P.q0).sum())
    out = lambda B: float((P.p0 * new_lots(P, cap, B) * P.lot).sum())
    lo, hi = B_LO, B_HI
    note = ''
    if out(hi) < target:
        return hi, target, out(hi), 'outlay at Rs 60,000 still below target -> B = 60,000'
    if out(lo) > target:
        return lo, target, out(lo), 'outlay at Rs 1,000 already above target -> B = 1,000'
    while hi - lo > B_TOL:
        mid = 0.5 * (lo + hi)
        if out(mid) < target:
            lo = mid
        else:
            hi = mid
    B = 0.5 * (lo + hi)
    return B, target, out(B), note


# sanity: qty = o_qty reproduces the harness option column
for s in H.SETS:
    for sc, pol in (('s_fable_op', 'T3'), ('s_opus_v3', 'T1')):
        t = H.pick(D[s], sc, 75, 6)
        assert np.allclose(H.option_net(t, pol, qty=t['o_qty'].to_numpy(float)).to_numpy(), t['opt_' + pol].to_numpy()), (s, sc)

print('opt_eqrisk_lots -- equal option-risk lot sizing at the baseline premium outlay')
print('metric: harness METRIC = %r (option net, modelled); futures net shown for reference at the NEW lots' % H.METRIC)
print('\nDeviations:')
for x in DEVIATIONS:
    print('  -', x)

# ------------------------------------------------------------------------------------------------ B_eq on design window
SETTINGS = {}
print('\n== B_eq (design window real %s..%s, that setting\'s picks only) ==' % (DES_LO, DES_HI))
for key, (score, pol, cap) in {'a': ('s_fable_op', 'T3', 2), 'b': ('s_fable_op', 'T3', 3), 'c': ('s_opus_v3', 'T1', 3)}.items():
    B, target, got, note = b_eq(score, cap)
    SETTINGS[key] = dict(score=score, pol=pol, cap=cap, B=B, target_outlay=target, design_outlay=got, note=note)
    print('  (%s) %-10s %s cap %dx  B_eq = Rs %8.1f   design outlay target Rs %12.0f  achieved Rs %12.0f (%.4f) %s' % (key, score, pol, cap, B, target, got, got / target, note))
SETTINGS['d'] = dict(score='s_fable_op', pol='T3', cap=3, B=15000.0, target_outlay=np.nan, design_outlay=np.nan, note='leverage variant')
NAME = {k: '(%s) %s %s cap%dx B=%d' % (k, 'FableOP' if v['score'] == 's_fable_op' else 'OpusV3', v['pol'], v['cap'], round(v['B'])) for k, v in SETTINGS.items()}
FN = {k: make(v['score'], v['pol'], v['cap'], v['B']) for k, v in SETTINGS.items()}

# ------------------------------------------------------------------------------------------------ design-window choice
_dd = design_df()
_days = sorted(_dd.day.unique())
des = {}
for _n, _spec in list(H.BASE.items()) + [(NAME[k], FN[k]) for k in 'abcd']:
    des[_n] = {'all': H.stats(H.run(_dd, _spec), _days)}
    des[_n]['h1'], des[_n]['h2'] = des[_n]['all'], {'net': 0}
print('\n== DESIGN WINDOW ONLY (real %s..%s), option net == (table header below shows the harness span; every row here is the design window only, 2nd half column empty by construction)' % (DES_LO, DES_HI))
H.show({'real': des})
bo, bf = des['Opus v3 (T1)']['all'], des['Fable-OP (T3)']['all']
lim_wd = 1.25 * max(bo['worst_day'], bf['worst_day'])
lim_dd = 1.25 * max(bo['maxdd'], bf['maxdd'])
print('  limits: worst day >= %+d, max DD >= %+d (1.25x the better design baseline)' % (lim_wd, lim_dd))
elig = [k for k in 'abc' if des[NAME[k]]['all']['worst_day'] >= lim_wd and des[NAME[k]]['all']['maxdd'] >= lim_dd]
for k in 'abcd':
    a = des[NAME[k]]['all']
    print('  %-34s net %+9d  worst day %+8d  max DD %+8d  eligible=%s' % (NAME[k], a['net'], a['worst_day'], a['maxdd'], (k in elig) if k != 'd' else 'n/a (leverage variant)'))
pool = elig if elig else list('abc')
CH = max(pool, key=lambda k: des[NAME[k]]['all']['net'])
flag = '' if elig else '  [FLAG: no setting met the risk limits; highest net taken]'
print('  CHOSEN: %s%s' % (NAME[CH], flag))
d_would = max('abcd', key=lambda k: des[NAME[k]]['all']['net'])
print('  (if (d) had been eligible on net alone, the highest design net would be: %s)' % NAME[d_would])

# ------------------------------------------------------------------------------------------------ full comparison
CAND = 'EQRISK ' + NAME[CH]
LEV = 'LEVERAGE ' + NAME['d']
print('\n\n######## CANDIDATE vs BASELINES on every set (option net, modelled; futures column = futures at the new lots) ########')
res = H.compare(D, {CAND: FN[CH], LEV: FN['d']})

print('\n\n######## all four grid settings on every set (reference only; the choice above used the design window) ########')
ref = H.evaluate(D, {NAME[k]: FN[k] for k in 'abcd'}, with_base=False)
H.show(ref)

# ------------------------------------------------------------------------------------------------ outlay / capital report
BASEF = {'Opus v3 (T1)': ('s_opus_v3', 'T1'), 'Fable-OP (T3)': ('s_fable_op', 'T3')}


def trades_for(name, df):
    if name in BASEF:
        sc, pol = BASEF[name]
        t = H.pick(df, sc, 75, 6).copy()
        P = prep(t)
        t['pol'], t['outlay'], t['new_lots'], t['fut_lots'], t['fut_base'] = pol, (P.p0 * P.q0).to_numpy(), P.fut_lots.to_numpy(), P.fut_lots.to_numpy(), t['net_' + pol]
        t['pnl'] = t['opt_' + pol]
        return t
    k = CH if name == CAND else 'd'
    return FN[k](df)


def peak_concurrent(t):
    pol = t['pol'].iloc[0]
    st = pd.to_datetime(t['o_entry_ts'], utc=True)
    en = pd.to_datetime(t['o_exit_ts_' + pol], utc=True) + pd.Timedelta(minutes=1)
    best = 0.0
    for d, g in t.groupby('day'):
        s, e, o = st[g.index], en[g.index], g['outlay']
        for ts in s:
            best = max(best, float(o[(s <= ts) & (e > ts)].sum()))
    return best


OUTLAY = {}
print('\n\n######## premium outlay and size (Rs; outlay = entry premium x quantity) ########')
hdr = '  %-40s %5s %9s %9s %10s %11s %11s %14s %7s | %6s %6s %6s | %10s %10s'
print(hdr % ('model', 'n', 'mean', 'median', 'max', 'max day', 'max concur', 'total', 'x base', 'L/fl', '@1lot', '@cap', 'fut new', 'fut base'))
for s in H.SETS:
    print(' -- %s' % s)
    OUTLAY[s] = {}
    for name in ('Opus v3 (T1)', 'Fable-OP (T3)', CAND, LEV):
        t = trades_for(name, D[s])
        base = 'Opus v3 (T1)' if t['pol'].iloc[0] == 'T1' else 'Fable-OP (T3)'
        tot_base = OUTLAY[s][base]['total'] if name not in BASEF else float(t.outlay.sum())
        cap = SETTINGS[CH if name == CAND else 'd']['cap'] if name not in BASEF else 1
        r = {'n': len(t), 'mean': float(t.outlay.mean()), 'median': float(t.outlay.median()), 'max': float(t.outlay.max()),
             'max_day': float(t.groupby('day').outlay.sum().max()), 'max_concurrent': peak_concurrent(t), 'total': float(t.outlay.sum()),
             'x_base': float(t.outlay.sum()) / tot_base, 'lots_ratio_mean': float((t.new_lots / t.fut_lots).mean()),
             'pct_at_1lot': 100.0 * float((t.new_lots == 1).mean()), 'pct_at_cap': 100.0 * float((t.new_lots >= cap * t.fut_lots - 1e-9).mean()) if name not in BASEF else 0.0,
             'fut_new': float(t['net_' + t['pol'].iloc[0]].sum()) if name not in BASEF else float(t.fut_base.sum()), 'fut_base': float(t.fut_base.sum())}
        if name not in BASEF:
            r['lot_flags'] = {k: int(v) for k, v in pd.Series(t['lot_flag']).value_counts().items() if k}
        OUTLAY[s][name] = r
        print('  %-40s %5d %9d %9d %10d %11d %11d %14d %7.3f | %6.2f %6.1f %6.1f | %+10d %+10d'
              % (name[:40], r['n'], r['mean'], r['median'], r['max'], r['max_day'], r['max_concurrent'], r['total'], r['x_base'],
                 r['lots_ratio_mean'], r['pct_at_1lot'], r['pct_at_cap'], r['fut_new'], r['fut_base']))
    for name in (CAND, LEV):
        if OUTLAY[s][name].get('lot_flags'):
            print('     %s: lot fallback rows %s' % (name[:40], OUTLAY[s][name]['lot_flags']))
print('  (L/fl = mean new lots / futures lots; @1lot = % of trades at the 1-lot floor; @cap = % at the cap; fut new = futures net at the new lots, fut base = at the futures lots)')

# ------------------------------------------------------------------------------------------------ verdict
def g(s, name, part):
    return res[s][name][part]


rows_bar = [('unseen', 'all'), ('real', 'h2')]
beats = {sp: all(g(sp[0], CAND, sp[1])['net'] > g(sp[0], b, sp[1])['net'] for b in ('Opus v3 (T1)', 'Fable-OP (T3)')) for sp in rows_bar}
beats_sw = {sp: g(sp[0], CAND, sp[1])['net'] > g(sp[0], 'Switch-1', sp[1])['net'] for sp in rows_bar}
risk = {}
for sp in rows_bar:
    c = g(sp[0], CAND, sp[1])
    bw = max(g(sp[0], b, sp[1])['worst_day'] for b in ('Opus v3 (T1)', 'Fable-OP (T3)'))
    bd = max(g(sp[0], b, sp[1])['maxdd'] for b in ('Opus v3 (T1)', 'Fable-OP (T3)'))
    risk[sp] = (c['worst_day'] >= 1.25 * bw and c['maxdd'] >= 1.25 * bd, c['worst_day'], 1.25 * bw, c['maxdd'], 1.25 * bd)
print('\n\n######## verdict for %s ########' % CAND)
for sp in rows_bar:
    c = g(sp[0], CAND, sp[1])
    print('  %-6s %-3s option net %+9d | Opus v3 %+9d | Fable-OP %+9d | Switch-1 %+9d | beats both: %s, beats Switch-1: %s | risk ok: %s (worst %+d vs limit %+d, DD %+d vs limit %+d)'
          % (sp[0], sp[1], c['net'], g(sp[0], 'Opus v3 (T1)', sp[1])['net'], g(sp[0], 'Fable-OP (T3)', sp[1])['net'], g(sp[0], 'Switch-1', sp[1])['net'],
             beats[sp], beats_sw[sp], *risk[sp]))
print('  PASSES THE BAR: %s' % (all(beats.values()) and all(r[0] for r in risk.values())))
print('\n  the two test periods in detail (option net):')
print('  %-6s %-3s %-38s %5s %10s %10s %10s %10s' % ('set', 'per', 'model', 'n', 'net', 'worst day', 'max DD', 'futures'))
for sp in rows_bar:
    for name in res[sp[0]]:
        c = g(sp[0], name, sp[1])
        print('  %-6s %-3s %-38s %5d %+10d %+10d %+10d %+10d' % (sp[0], sp[1], name[:38], c['n'], c['net'], c['worst_day'], c['maxdd'], c['fut']))

print('\n  how often the new sizing differs from the futures lots (candidate / leverage variant):')
for s in H.SETS:
    for name, k in ((CAND, CH), (LEV, 'd')):
        t = FN[k](D[s])
        up, dn = (t.new_lots > t.fut_lots + 1e-9), (t.new_lots < t.fut_lots - 1e-9)
        diff = t['pnl'] - t['opt_' + t['pol'].iloc[0]]
        print('  %-6s %-40s more lots %3d (option net change %+9d) | fewer lots %3d (%+9d) | same %3d' % (s, name[:40], up.sum(), diff[up].sum(), dn.sum(), diff[dn].sum(), (~up & ~dn).sum()))

# ------------------------------------------------------------------------------------------------ exploratory sensitivity
print('\n\n######## EXPLORATORY (not pre-registered): real-set lots for the symbols absent from the known set taken from the scanner lot table ########')
try:
    import pickle
    sys.path.insert(0, SP + '/v2/patched')
    LT = pickle.load(open(SP + '/replay_sep/minutes.pkl', 'rb'))['lot']
    _orig = row_lots

    def row_lots_alt(t):
        lot, flag = _orig(t)
        if 'lot' not in t.columns:
            for i, (s, q, f) in enumerate(zip(t['symbol'], t['o_qty'].to_numpy(float), flag)):
                if f == 'absent' and s in LT and q % LT[s][0] == 0:
                    lot[i], flag[i] = float(LT[s][0]), 'absent->scanner lot'
        return lot, flag
    row_lots = row_lots_alt
    alt = H.evaluate({'real': D['real']}, {CAND + ' [alt lots]': make(SETTINGS[CH]['score'], SETTINGS[CH]['pol'], SETTINGS[CH]['cap'], SETTINGS[CH]['B']),
                                           LEV + ' [alt lots]': make('s_fable_op', 'T3', 3, 15000.0)}, sets=('real',))
    H.show(alt)
    row_lots = _orig
    del LT
except Exception as e:                                  # noqa
    print('  skipped:', e)

# ------------------------------------------------------------------------------------------------ save
json.dump(res, open(OUT + '/results.json', 'w'), indent=1, default=float)
json.dump({'settings': SETTINGS, 'chosen': CH, 'candidate_name': CAND, 'leverage_name': LEV, 'design': des, 'design_limits': {'worst_day': lim_wd, 'maxdd': lim_dd},
           'eligible': elig, 'all_grid': ref, 'outlay': OUTLAY, 'deviations': DEVIATIONS,
           'bar': {'beats_both': {'%s_%s' % k: v for k, v in beats.items()}, 'beats_switch1': {'%s_%s' % k: v for k, v in beats_sw.items()},
                   'risk_ok': {'%s_%s' % k: v[0] for k, v in risk.items()}}},
          open(OUT + '/extras.json', 'w'), indent=1, default=lambda x: x.item() if hasattr(x, 'item') else (None if x != x else str(x)))
print('\nsaved', OUT + '/results.json', 'and', OUT + '/extras.json')
