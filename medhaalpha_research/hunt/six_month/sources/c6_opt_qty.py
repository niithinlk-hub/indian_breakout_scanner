# Check 6: option quantity inputs on the picked real (and unseen) trades.
#  - o_qty NaN / 0 rows (option net forced to 0 while the futures net still counts)
#  - o_qty equal to exactly one lot of the symbol (possible 1-lot fallback)
#  - o_qty vs an independent lots_for re-computation (scanner sizing formula, cash price + stop, lot table)
#  - o_qty vs the futures quantity implied by the scanner's own real net/R (pull.json)
#  - rows whose option exit time is missing (option_net gives NaN -> 0)
#  - option net those rows contribute, per model
import json, sys, pickle, glob
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
OUT = SP + '/hunt/six_month/sources'
sys.path.insert(0, SP + '/hunt'); sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
cfg = EqConfig()
D = H.load_all()
J = json.load(open(SP + '/hunt/six_month/six_month.json'))

# lot table used by optlayer (replay_sep/minutes.pkl 'lot') and an independent one from the proxy files
late = pickle.load(open(SP + '/replay_sep/minutes.pkl', 'rb'))
LOT = {k: v[0] for k, v in late.get('lot', {}).items()}
del late
PLOT = {}
for p in sorted(glob.glob(SP + '/v2/proxy_unseen/proxy_*.json')) + sorted(glob.glob(SP + '/v2/proxy_known/proxy_*.json')):
    for s in json.load(open(p))['signals']:
        PLOT.setdefault(s['symbol'], set()).add(s['lot'])
multi = {k: v for k, v in PLOT.items() if len(v) > 1}
print('lot table (optlayer) symbols', len(LOT), '| proxy lot sizes symbols', len(PLOT), 'with >1 lot size across proxy days', len(multi))
dif = {k: (LOT.get(k), sorted(v)) for k, v in PLOT.items() if LOT.get(k) is not None and LOT[k] not in v}
print('symbols whose optlayer lot is not among proxy lot sizes:', len(dif), list(dif.items())[:10])

R = D['real'].copy()
R['L'] = R.symbol.map(LOT)
sign = np.where(R.side == 'LONG', 1, -1)
e0 = R.price.to_numpy(float)
stop = e0 - sign * R.risk_pct.to_numpy(float) / 100 * e0


def lots_for(side, entry, stop, L):
    if not (L == L) or L <= 0:
        return 0
    per = abs(entry - stop) * L + C.round_trip('FUT', entry, stop, int(L), side, cfg.brokerage_per_order, cfg.brokerage_pct) + C.slippage(entry, stop, int(L), cfg.slippage_pct)
    return int(cfg.risk_budget_rs // per) if per > 0 else 0


R['my_lots'] = [lots_for(sd, a, b, L) for sd, a, b, L in zip(R.side, e0, stop, R.L)]
R['my_qty'] = np.where(R.my_lots > 0, R.my_lots * R.L, np.nan)
R['o_lots'] = R.o_qty / R.L
# futures quantity implied by the scanner's real record: net ~ qty * r * risk_unit - costs  -> lots_est
ru = R.risk_pct / 100 * R.price
for p in ('T1', 'T3', 'CLOSE_TR'):
    R['imp_lots_' + p] = np.where(R['r_' + p].abs() >= 0.5, R['net_' + p] / (R['r_' + p] * ru * R.L), np.nan)
R['imp_lots'] = R[['imp_lots_T1', 'imp_lots_T3', 'imp_lots_CLOSE_TR']].median(axis=1)

print('\nREAL all rows: %d; o_qty NaN %d, o_qty 0 %d, lot unknown %d; my lots_for==0 %d; o_qty != my_qty (both finite) %d' % (
    len(R), R.o_qty.isna().sum(), (R.o_qty == 0).sum(), R.L.isna().sum(), (R.my_lots == 0).sum(),
    int(((R.o_qty - R.my_qty).abs() > 0.5).sum())))
fin = R.imp_lots.notna() & R.o_lots.notna()
rel = (R.o_lots[fin] - R.imp_lots[fin]) / R.imp_lots[fin]
print('o_qty vs futures qty implied by pull.json (|r|>=0.5 rows %d): median rel diff %.3f, |rel|>0.25 in %d rows, o_lots/imp_lots ratio quantiles %s' % (
    fin.sum(), rel.median(), int((rel.abs() > 0.25).sum()), np.round(np.nanquantile((R.o_lots / R.imp_lots)[fin], [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]), 3).tolist()))
print('implied lots for o_qty-NaN rows (does the futures leg trade them?):', np.round(R.loc[R.o_qty.isna(), 'imp_lots'].dropna().describe()[['count', 'min', '50%', 'max']].to_numpy(), 2).tolist())
print('implied lots < 0.5 (futures leg effectively 0 lots) rows:', int((R.imp_lots < 0.5).sum()))
# missing exit timestamps
for p in ('T1', 'T3', 'CLOSE_TR'):
    print('  rows with o_exit_ts_%s missing: %d, o_F1 NaN %d, o_F0 NaN %d' % (p, R['o_exit_ts_' + p].isna().sum(), R['o_F1_' + p].isna().sum(), R.o_F0.isna().sum()))

MODELS = {'Opus (T1), live model': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6)}
out = {}
for s in ('real', 'unseen'):
    df = D[s].copy()
    if s == 'real':
        df = R
    else:
        df['L'] = df['lot']
        df['o_lots'] = df.o_qty / df.L
    print('\n%s picked trades: per model' % s.upper())
    print('  %-44s %5s %6s %8s %10s %7s %11s %9s %10s %9s %11s' % ('model', 'n', 'qtyNaN', 'fut(NaN)', 'qty=1lot', 'opt1lot', 'fut(1lot)', 'noExitTs', 'opt(nf)', '!=lotsfor', 'opt(!=)'))
    out[s] = {}
    for name, spec in MODELS.items():
        t = H.run(df, spec)
        pol = t.pol
        qnan = t.o_qty.isna() | (t.o_qty <= 0)
        one = (t.o_lots.round(6) == 1.0)
        ex_missing = pd.Series([pd.isna(r['o_exit_ts_' + p]) for (_, r), p in zip(t.iterrows(), pol)], index=t.index) & ~qnan
        zero_opt = (t.pnl == 0)
        if s == 'real':
            neq = (t.o_qty - t.my_qty).abs() > 0.5
        else:
            neq = pd.Series(False, index=t.index)
        o = {'n': len(t), 'qty_nan_or_0': int(qnan.sum()), 'fut_of_qty_nan': round(float(t.fut[qnan].sum())),
             'one_lot': int(one.sum()), 'opt_one_lot': round(float(t.pnl[one].sum())), 'fut_one_lot': round(float(t.fut[one].sum())),
             'exit_ts_missing': int(ex_missing.sum()), 'opt_net_exact_zero': int(zero_opt.sum()), 'opt_total': round(float(t.pnl.sum())),
             'opt_json': J['models'][s][name]['opt_net'], 'qty_ne_lotsfor': int(neq.sum()), 'opt_ne_lotsfor': round(float(t.pnl[neq].sum()))}
        out[s][name] = o
        print('  %-44s %5d %6d %8d %10d %+7d %+11d %9d %+10d %9d %+11d   opt total %d (json %d)' % (
            name[:44], o['n'], o['qty_nan_or_0'], o['fut_of_qty_nan'], o['one_lot'], o['opt_one_lot'], o['fut_one_lot'], o['exit_ts_missing'], 0,
            o['qty_ne_lotsfor'], o['opt_ne_lotsfor'], o['opt_total'], o['opt_json']))
    # unseen: o_qty vs proxy lot*lots
    if s == 'unseen':
        print('  unseen o_qty vs proxy lot*lots: mismatches', int(((df.o_qty - df.lot * df.lots).abs() > 0.5).sum()), 'lots==0', int((df.lots == 0).sum()))

# detail of picked real rows with NaN qty
print('\nREAL picked rows with o_qty NaN (any model):')
allp = pd.concat([H.run(R, spec).assign(model=name) for name, spec in MODELS.items()])
nanrows = allp[allp.o_qty.isna()]
print(nanrows[['model', 'day', 'time', 'symbol', 'side', 'pol', 'price', 'risk_pct', 'L', 'my_lots', 'imp_lots', 'fut', 'pnl']].to_string() if len(nanrows) else '  none')
# what the NaN-qty rows would add with the implied futures lots (same lots as futures, as the brief says)
if len(nanrows):
    fix = []
    for name, spec in MODELS.items():
        t = H.run(R, spec)
        m = t.o_qty.isna() & t.imp_lots.notna()
        if m.any():
            q = (t.imp_lots[m].round().clip(lower=1) * t.L[m]).to_numpy()
            v = sum(float(H.option_net(t[m & (t.pol == p)], p, qty=q[(t.pol[m] == p).to_numpy()]).sum()) for p in t.pol[m].unique())
            fix.append((name, int(m.sum()), round(v)))
    print('option net those NaN-qty rows would add at the futures (implied) lots:', fix)
json.dump(out, open(OUT + '/c6_result.json', 'w'), indent=1)
R[['day', 'time', 'symbol', 'setup', 'side', 'price', 'risk_pct', 'L', 'my_lots', 'my_qty', 'o_qty', 'o_lots', 'imp_lots']].to_pickle(OUT + '/real_qty.pkl')
