# vwap_trail: VWAP trailing exit, no target, flat at 15:29, on Fable-OP (S1-S3) / Opus v3 (S4) picks.
# Pre-registered test (see task). Exit policy 'VW': structural stop always live; at CHECK bars, a close beyond the
# session VWAP against the trade exits at the open of the next bar; anything open is squared off at 15:29 as
# scanner.equity.fills.simulate does for the CLOSE policy. Option leg priced with harness.option_net (1-minute lag).
# Grid (declared in advance, chosen on the design window real 12 May-31 Aug 2026 only):
#   S1 s_fable_op>=75, checks at bars 09:44,10:14,...,15:14 (30-minute marks), active from entry
#   S2 s_fable_op>=75, checks at every 1-minute close from the entry bar
#   S3 s_fable_op>=75, 1-minute checks, active only once MFE >= +0.5R (bar highs/lows since entry, in R)
#   S4 s_opus_v3>=75, as S1
import sys, json, time
import numpy as np
import pandas as pd

SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/vwap_trail/verify/rerun'
sys.path.insert(0, SP + '/hunt')
sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.fills import simulate as fills_simulate

pd.set_option('display.width', 250)
cfg = EqConfig()
T0 = time.time()
D = H.load_all()
mins, daily, nifty, lot = H.minute_data()          # loaded once
print('loaded data in %.0fs' % (time.time() - T0))

DESIGN = ('2026-05-12', '2026-08-31')
REAL_H2 = ('2026-09-01', '2026-11-11')
CHECK30 = set(range(9 * 60 + 44, 15 * 60 + 15, 30))     # 09:44, 10:14, ..., 15:14 (minute of day)
assert min(CHECK30) == 584 and max(CHECK30) == 914 and len(CHECK30) == 12
RULES = ('CLOSE', 'T1', 'T3', 'VW30', 'VW1', 'VW1M')     # engine rules; CLOSE/T1/T3 = re-sims of the harness policies
OFF = np.int64(19800 * 10 ** 9)                          # +05:30 in ns


# ---------------------------------------------------------------------------------------------- engine
def first(mask):
    return int(np.argmax(mask)) if mask.any() else None


def walk(o, h, l, c, vw, mod, ts, sgn, stop, R, target=None, check=None, mfe_gate=None):
    """Bars o..ts start at the entry bar e and run to the session's last bar. Returns (X, exit_ts, reason).
    Stop first (fills.simulate gap rule); target (fills.simulate: stop wins a shared bar); VWAP rule at check bars,
    only if not stopped in that bar, exit at the next bar's open; else square off at the last close."""
    n = len(o)
    if sgn > 0:
        stop_hit = (o <= stop) | (l <= stop)
    else:
        stop_hit = (o >= stop) | (h >= stop)
    i_s = first(stop_hit)
    i_t = None
    if target is not None:
        tgt_hit = ((o >= target) | (h >= target)) if sgn > 0 else ((o <= target) | (l <= target))
        i_t = first(tgt_hit)
    i_v = None
    if check is not None:
        with np.errstate(invalid='ignore'):
            against = (c < vw) if sgn > 0 else (c > vw)
        against &= np.isfinite(vw)
        if check == '30':
            chk = np.isin(mod, list(CHECK30))
        else:
            chk = np.ones(n, bool)
        trig = against & chk
        if mfe_gate is not None:
            fav = np.maximum.accumulate((h - o[0]) if sgn > 0 else (o[0] - l))
            trig &= (fav >= mfe_gate * R) if R > 0 else np.zeros(n, bool)
        i_v = first(trig)
    big = n + 10
    s_, t_, v_ = (i_s if i_s is not None else big), (i_t if i_t is not None else big), (i_v if i_v is not None else big)
    if i_s is not None and s_ <= t_ and s_ <= v_:
        gap = (o[i_s] <= stop) if sgn > 0 else (o[i_s] >= stop)
        return (float(o[i_s]) if gap else float(stop)), ts[i_s], ('stop_gap' if gap else 'stop')
    if i_t is not None and t_ <= v_:
        gap = (o[i_t] >= target) if sgn > 0 else (o[i_t] <= target)
        return (float(o[i_t]) if gap else float(target)), ts[i_t], ('target_gap' if gap else 'target')
    if i_v is not None and i_v + 1 < n:
        return float(o[i_v + 1]), ts[i_v + 1], 'vwap'
    return float(c[-1]), ts[-1], 'close'


def fut_net(sgn, side, F0, F1, qty):
    if not (np.isfinite(F0) and np.isfinite(F1) and qty and qty > 0):
        return np.nan
    gross = sgn * (F1 - F0) * qty
    return gross - C.round_trip('FUT', F0, F1, qty, side, cfg.brokerage_per_order, cfg.brokerage_pct) - C.slippage(F0, F1, qty, cfg.slippage_pct)


def run_engine(setname, df):
    """Adds per rule r: o_F1_E<r>, o_exit_ts_E<r>, netE_<r>, rE_<r>, optE_<r>, whyE_<r>, holdE_<r>; plus E_entry, E_stop."""
    real = setname == 'real'
    res = {r: {'F1': np.full(len(df), np.nan), 'ts': [None] * len(df), 'net': np.full(len(df), np.nan), 'r': np.full(len(df), np.nan),
               'why': [None] * len(df)} for r in RULES}
    Ecol, Scol, miss = np.full(len(df), np.nan), np.full(len(df), np.nan), 0
    pos = {ix: k for k, ix in enumerate(df.index)}
    for sym, g in df.groupby('symbol', sort=False):
        m = mins.get(sym)
        if m is None or not len(m):
            miss += len(g)
            continue
        assert m.index.is_monotonic_increasing
        ns = m.index.asi8 + OFF
        lmin = ns // (60 * 10 ** 9)
        dint, mod_all = lmin // 1440, lmin % 1440
        O, Hh, L, Cc, V = (m[k].to_numpy(float) for k in ('open', 'high', 'low', 'close', 'volume'))
        IDX = m.index
        for ix, r in g.iterrows():
            k = pos[ix]
            di = (pd.Timestamp(r.day) - pd.Timestamp('1970-01-01')).days
            lo, hi = np.searchsorted(dint, di, 'left'), np.searchsorted(dint, di, 'right')
            sel = np.arange(lo, hi)
            sel = sel[(mod_all[sel] >= 555) & (mod_all[sel] <= 929)]           # regular session 09:15-15:29
            if not len(sel):
                miss += 1
                continue
            o, h, l, c, v, mod = O[sel], Hh[sel], L[sel], Cc[sel], V[sel], mod_all[sel]
            tp = (h + l + c) / 3.0
            cv = np.cumsum(v)
            with np.errstate(invalid='ignore', divide='ignore'):
                vw = np.where(cv > 0, np.cumsum(tp * v) / np.where(cv > 0, cv, 1.0), np.nan)
            hh, mm = map(int, r.time.split(':'))
            e = int(np.searchsorted(mod, hh * 60 + mm + 1, 'left'))          # first bar after the signal bar
            if e >= len(sel):
                miss += 1
                continue
            sgn = 1 if r.side == 'LONG' else -1
            E = float(o[e])
            # real: stop_c = E*(1 - sgn*o_risk_abs/o_F0) exactly as specified (no rounding). Float noise decides a few
            # exact-touch bars (stop = bar high/low to the tick) differently from the harness's own cash replay; counted
            # in the engine check below (rounding to 4 decimals was tried and matched the harness replay less often).
            stop = E * (1 - sgn * r.o_risk_abs / r.o_F0) if real else float(r.stop)
            R = abs(E - stop)
            if real:
                e0 = float(r.price)
                rk = r.risk_pct / 100.0 * e0
                tg = {'T1': e0 + sgn * cfg.t1_r * rk, 'T3': e0 + sgn * cfg.t3_r * rk}
            else:
                tg = {'T1': float(r.t1), 'T3': float(r.t3)}
            ts = IDX[sel[e:]]
            a = (o[e:], h[e:], l[e:], c[e:], vw[e:], mod[e:], ts, sgn, stop, R)
            outs = {'CLOSE': walk(*a), 'T1': walk(*a, target=tg['T1']), 'T3': walk(*a, target=tg['T3']),
                    'VW30': walk(*a, check='30'), 'VW1': walk(*a, check='1'), 'VW1M': walk(*a, check='1', mfe_gate=0.5)}
            Ecol[k], Scol[k] = E, stop
            for rule, (X, xts, why) in outs.items():
                F1 = r.o_F0 * X / E                    # cash move mapped onto the scanner's underlying (exact on unseen/known)
                d = res[rule]
                d['F1'][k], d['ts'][k], d['why'][k] = F1, xts.isoformat(), why
                d['r'][k] = sgn * (X - E) / R if R > 0 else 0.0
                if real:
                    d['net'][k] = fut_net(sgn, r.side, r.o_F0, F1, r.o_qty)
                else:
                    d['net'][k] = fut_net(sgn, r.side, E, X, r.o_qty)
    df['E_entry'], df['E_stop'] = Ecol, Scol
    for rule, d in res.items():
        df['o_F1_E' + rule] = d['F1']
        df['o_exit_ts_E' + rule] = d['ts']
        df['netE_' + rule] = d['net']
        df['rE_' + rule] = d['r']
        df['whyE_' + rule] = d['why']
        df['optE_' + rule] = H.option_net(df, 'E' + rule)
        df['holdE_' + rule] = (pd.to_datetime(df['o_exit_ts_E' + rule], utc=True) - pd.to_datetime(df['o_entry_ts'], utc=True)).dt.total_seconds() / 60
    return miss


for s in H.SETS:
    t1 = time.time()
    miss = run_engine(s, D[s])
    print('engine %s: %d rows, %d without minute data, %.0fs' % (s, len(D[s]), miss, time.time() - t1))


# ---------------------------------------------------------------------------------------------- engine check
def picked_union(df):
    return sorted(set(H.pick(df, 's_fable_op', 75, 6).index) | set(H.pick(df, 's_opus_v3', 75, 6).index))


print('\n================ ENGINE CHECK (VWAP rule disabled) =================')
CHECK = {}
for s in H.SETS:
    df = D[s]
    for scope, idx in (('all rows', df.index), ('picked rows (fable_op/opus_v3)', picked_union(df))):
        d = df.loc[idx]
        line = {'rows': len(d)}
        for rule in ('CLOSE', 'T1', 'T3'):
            ts_ok = (d['o_exit_ts_E' + rule] == d['o_exit_ts_' + rule]).mean() * 100
            f1d = (d['o_F1_E' + rule] - d['o_F1_' + rule]).abs()
            optd = (d['optE_' + rule] - d['opt_' + rule]).abs()
            netd = (d['netE_' + rule] - d['net_' + rule]).abs()
            line[rule] = {'exit_ts_match_pct': round(float(ts_ok), 2), 'F1_maxabs_diff': round(float(f1d.max()), 4),
                          'opt_sum_engine': round(float(d['optE_' + rule].sum())), 'opt_sum_harness': round(float(d['opt_' + rule].sum())),
                          'opt_maxabs_diff': round(float(optd.max()), 2), 'fut_sum_engine': round(float(d['netE_' + rule].sum())),
                          'fut_sum_harness': round(float(d['net_' + rule].sum())), 'fut_maxabs_diff': round(float(netd.max()), 2)}
        CHECK['%s | %s' % (s, scope)] = line
        print('\n-- %s, %s: %d rows' % (s, scope, len(d)))
        for rule in ('CLOSE', 'T1', 'T3'):
            x = line[rule]
            print('   %-5s exit_ts match %6.2f%% | F1 max|diff| %9.4f | option sum engine %+11d harness %+11d (max row |diff| %8.2f) | futures sum engine %+11d harness %+11d (max row |diff| %8.2f)'
                  % (rule, x['exit_ts_match_pct'], x['F1_maxabs_diff'], x['opt_sum_engine'], x['opt_sum_harness'], x['opt_maxabs_diff'],
                     x['fut_sum_engine'], x['fut_sum_harness'], x['fut_maxabs_diff']))
# second check: the engine's CLOSE/T3 against scanner.equity.fills.simulate itself on the picked rows of every set
nbad = {}
for s in H.SETS:
    df = D[s]
    bad = 0
    idx = picked_union(df)
    for ix in idx:
        r = df.loc[ix]
        m = mins[r.symbol]
        st = pd.Timestamp(r.day + ' ' + r.time).tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
        dm = m[m.index.date == st.date()]
        for rule, tgt in (('CLOSE', None), ('T3', None if s == 'real' else float(r.t3))):
            if rule == 'T3' and s == 'real':
                sgn = 1 if r.side == 'LONG' else -1
                tgt = r.price + sgn * cfg.t3_r * r.risk_pct / 100.0 * r.price
            stt, xts, px, why, e, ets = fills_simulate(dm, r.side, r.E_stop, tgt, st)
            if stt == 'no_data':
                bad += 1
                continue
            if xts.isoformat() != r['o_exit_ts_E' + rule] or abs(r.o_F0 * px / e - r['o_F1_E' + rule]) > 1e-6:
                bad += 1
    nbad[s] = (bad, 2 * len(idx))
    print('engine vs scanner fills.simulate (CLOSE and T3, same stop), %s picked rows: %d mismatches of %d row-rules' % (s, bad, 2 * len(idx)))
CHECK['vs_fills_simulate'] = nbad


# ---------------------------------------------------------------------------------------------- candidates
def cand(score, rule, label='VW'):
    def f(df):
        t = H.pick(df, score, 75, 6).copy()
        t['net_' + label], t['r_' + label], t['pnl'] = t['netE_' + rule], t['rE_' + rule], t['optE_' + rule]
        t['pol'] = label
        return t
    return f


GRID = {'S1': ('s_fable_op', 'VW30', 'S1 Fable-OP VW 30-min checks'),
        'S2': ('s_fable_op', 'VW1', 'S2 Fable-OP VW 1-min checks'),
        'S3': ('s_fable_op', 'VW1M', 'S3 Fable-OP VW 1-min, MFE>=0.5R'),
        'S4': ('s_opus_v3', 'VW30', 'S4 Opus v3 VW 30-min checks')}
ENG = {'ENG re-sim Opus v3 T1': cand('s_opus_v3', 'T1', 'ENG'), 'ENG re-sim Fable-OP T3': cand('s_fable_op', 'T3', 'ENG'),
       'ENG re-sim Fable-OP CLOSE': cand('s_fable_op', 'CLOSE', 'ENG'), 'ENG re-sim Opus v3 CLOSE': cand('s_opus_v3', 'CLOSE', 'ENG')}
HCLOSE = {'harness Fable-OP CLOSE': ('s_fable_op', 75, 'CLOSE', 6), 'harness Opus v3 CLOSE': ('s_opus_v3', 75, 'CLOSE', 6)}

# ---------------------------------------------------------------------------------------------- design-window choice
print('\n================ DESIGN WINDOW (real %s to %s, cash re-sim of the real picks) =================' % DESIGN)
Dd = {'real': D['real'][(D['real'].day >= DESIGN[0]) & (D['real'].day <= DESIGN[1])].copy()}
cands_d = {v[2]: cand(v[0], v[1]) for v in GRID.values()}
cands_d.update(ENG)
ddays = sorted(Dd['real'].day.unique())
resd = {}
for name, spec in list(H.BASE.items()) + list(cands_d.items()):
    resd[name] = {'all': H.stats(H.run(Dd['real'], spec), ddays)}       # harness run/stats on the design-window rows only
print('  %-34s %5s %10s %10s %10s %10s' % ('model', 'n', 'opt net', 'worst day', 'max DD', 'futures'))
for name, r in resd.items():
    a = r['all']
    print('  %-34s %5d %+10d %+10d %+10d %+10d' % (name[:34], a['n'], a['net'], a['worst_day'], a['maxdd'], a['fut']))
bw = max(resd['Opus v3 (T1)']['all']['worst_day'], resd['Fable-OP (T3)']['all']['worst_day'])
bd = max(resd['Opus v3 (T1)']['all']['maxdd'], resd['Fable-OP (T3)']['all']['maxdd'])
lim_w, lim_d = 1.25 * bw, 1.25 * bd
print('  limits: worst day >= %+d (1.25 x better baseline %+d), max DD >= %+d (1.25 x better baseline %+d)' % (lim_w, bw, lim_d, bd))
qual = {}
for k, v in GRID.items():
    a = resd[v[2]]['all']
    qual[k] = (a['worst_day'] >= lim_w) and (a['maxdd'] >= lim_d)
    print('  %s: net %+d worst %+d maxDD %+d -> %s' % (k, a['net'], a['worst_day'], a['maxdd'], 'qualifies' if qual[k] else 'fails risk limit'))
pool = [k for k in GRID if qual[k]]
flag = False
if not pool:
    pool, flag = list(GRID), True
CH = max(pool, key=lambda k: resd[GRID[k][2]]['all']['net'])
print('  CHOSEN: %s (%s)%s' % (CH, GRID[CH][2], '  [FLAG: no setting met the risk limits; highest net taken]' if flag else ''))
design = {'limits': {'worst_day': lim_w, 'maxdd': lim_d}, 'qualifies': qual, 'chosen': CH, 'flag_no_qualifier': flag,
          'stats': {k: resd[GRID[k][2]]['all'] for k in GRID},
          'baselines': {k: resd[k]['all'] for k in ('Opus v3 (T1)', 'Fable-OP (T3)', 'Switch-1')},
          'engine_resims': {k: resd[k]['all'] for k in ENG}}

# ---------------------------------------------------------------------------------------------- full comparison
CNAME = 'VW trail %s (chosen)' % CH
print('\n================ CANDIDATE vs BASELINES (OPTION net; harness.compare) =================')
print('candidate = %s: %s' % (CH, GRID[CH][2]))
cands = {CNAME: cand(GRID[CH][0], GRID[CH][1])}
cands.update(ENG)
cands.update(HCLOSE)
res = H.compare(D, cands)
json.dump(res, open(OUT + '/results.json', 'w'), indent=1)


def halves_table(res, title):
    print('\n-- %s: per half (option net / worst day / max DD / futures net)' % title)
    for s, rows in res.items():
        print('  %s' % s.upper())
        for name, r in rows.items():
            print('    %-34s' % name[:34] + ' | '.join(' %s %+9d wd %+8d dd %+9d fut %+9d' % (h, r[h]['net'], r[h]['worst_day'], r[h]['maxdd'], r[h]['fut'])
                                                    for h in ('all', 'h1', 'h2')))


halves_table(res, 'chosen candidate, baselines and engine re-sims')

print('\n================ the other declared settings (NOT chosen; for information only) =================')
others = {GRID[k][2] + ('' if k != CH else ' [chosen]'): cand(GRID[k][0], GRID[k][1]) for k in GRID}
res_o = H.evaluate(D, others, with_base=False)
H.show(res_o)
halves_table(res_o, 'all four settings')
json.dump(res_o, open(OUT + '/results_all_settings.json', 'w'), indent=1)

# ---------------------------------------------------------------------------------------------- verdict
def g(set_, name, h='all'):
    return res[set_][name][h]


ob, fb, sw = 'Opus v3 (T1)', 'Fable-OP (T3)', 'Switch-1'
beats_unseen = g('unseen', CNAME)['net'] > max(g('unseen', ob)['net'], g('unseen', fb)['net'])
beats_h2 = g('real', CNAME, 'h2')['net'] > max(g('real', ob, 'h2')['net'], g('real', fb, 'h2')['net'])
beats_sw = g('unseen', CNAME)['net'] > g('unseen', sw)['net'] and g('real', CNAME, 'h2')['net'] > g('real', sw, 'h2')['net']
risk = {}
for set_, h in (('unseen', 'all'), ('real', 'h2')):
    bw_ = max(g(set_, ob, h)['worst_day'], g(set_, fb, h)['worst_day'])
    bd_ = max(g(set_, ob, h)['maxdd'], g(set_, fb, h)['maxdd'])
    c_ = g(set_, CNAME, h)
    risk[set_ + '_' + h] = {'worst_day': c_['worst_day'], 'limit_wd': 1.25 * bw_, 'maxdd': c_['maxdd'], 'limit_dd': 1.25 * bd_,
                            'ok': bool(c_['worst_day'] >= 1.25 * bw_ and c_['maxdd'] >= 1.25 * bd_)}
risk_ok = all(v['ok'] for v in risk.values())
# like-for-like on real: candidate vs the engine's own re-sim of the same picks
eng_same = 'ENG re-sim Fable-OP T3' if GRID[CH][0] == 's_fable_op' else 'ENG re-sim Opus v3 T1'
print('\n================ VERDICT (bar: OPTION net, unseen and real 2nd half) =================')
for set_, h in (('unseen', 'all'), ('real', 'h2'), ('real', 'h1'), ('real', 'all'), ('known', 'all')):
    print('  %-6s %-3s cand %+9d | Opus v3 T1 %+9d | Fable-OP T3 %+9d | Switch-1 %+9d | engine re-sim %s %+9d | ENG Opus v3 T1 %+9d'
          % (set_, h, g(set_, CNAME, h)['net'], g(set_, ob, h)['net'], g(set_, fb, h)['net'], g(set_, sw, h)['net'], eng_same,
             g(set_, eng_same, h)['net'], g(set_, 'ENG re-sim Opus v3 T1', h)['net']))
print('  beats both baselines on unseen: %s | on real 2nd half: %s | beats Switch-1 on both: %s' % (beats_unseen, beats_h2, beats_sw))
for k, v in risk.items():
    print('  risk %-10s worst day %+d (limit %+d), max DD %+d (limit %+d) -> %s' % (k, v['worst_day'], v['limit_wd'], v['maxdd'], v['limit_dd'], 'ok' if v['ok'] else 'FAILS'))
print('  risk_ok: %s' % risk_ok)

# exit mix and holding time of the chosen setting vs the engine's T3 on the same picks
print('\n-- exit reasons / holding minutes, chosen setting on its picks (engine T3 / CLOSE on the same picks for reference)')
for s in H.SETS:
    t = H.pick(D[s], GRID[CH][0], 75, 6)
    for rule in (GRID[CH][1], 'T3' if GRID[CH][0] == 's_fable_op' else 'T1', 'CLOSE'):
        vc = t['whyE_' + rule].value_counts().to_dict()
        print('  %-6s %-5s n %3d  %s  median hold %5.0f min  mean option net/trade %+7.0f' % (s, rule, len(t), vc, t['holdE_' + rule].median(), t['optE_' + rule].mean()))

json.dump({'engine_check': CHECK, 'design': design, 'chosen': CH, 'candidate_name': CNAME, 'beats_both_unseen': bool(beats_unseen),
           'beats_both_real_h2': bool(beats_h2), 'beats_switch1_both': bool(beats_sw), 'risk': risk, 'risk_ok': bool(risk_ok)},
          open(OUT + '/design_and_checks.json', 'w'), indent=1, default=str)
print('\nsaved results.json (evaluate dict: chosen + baselines + engine re-sims), results_all_settings.json, design_and_checks.json; %.0fs' % (time.time() - T0))
