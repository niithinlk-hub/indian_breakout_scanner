# Check 6b: confirm the 1-lot fallback rows with the scanner's own lots_for, size of the over-budget,
# and per-model counts / option net / futures net of those rows (real and unseen).
import sys, json
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt'); sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity.scan import lots_for
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
cfg = EqConfig()
print('cfg risk_budget_rs', cfg.risk_budget_rs, 'lots_per_trade', cfg.lots_per_trade, 'slippage', cfg.slippage_pct)
D = H.load_all()
Q = pd.read_pickle(SP + '/hunt/six_month/sources/real_qty.pkl')
R = D['real'].copy()
R['L'] = Q.L.values
sign = np.where(R.side == 'LONG', 1, -1)
e0 = R.price.to_numpy(float); stop = e0 - sign * R.risk_pct.to_numpy(float) / 100 * e0
R['sc_lots'] = [lots_for(s, a, b, int(L), cfg) for s, a, b, L in zip(R.side, e0, stop, R.L)]
R['per_lot'] = [abs(a - b) * L + C.round_trip('FUT', a, b, int(L), s, cfg.brokerage_per_order, cfg.brokerage_pct) + C.slippage(a, b, int(L), cfg.slippage_pct)
                for s, a, b, L in zip(R.side, e0, stop, R.L)]
R['o_lots'] = R.o_qty / R.L
print('scanner lots_for==0 rows:', int((R.sc_lots == 0).sum()), '| agrees with my reimplementation:', bool((R.sc_lots.values == Q.my_lots.values).all()))
fb = (R.sc_lots == 0)
print('o_lots on those rows:', R.o_lots[fb].value_counts().to_dict())
print('o_lots == sc_lots on the other rows:', bool((R.o_lots[~fb] == R.sc_lots[~fb]).all()))
print('per-lot risk at stop on fallback rows (Rs): min %.0f median %.0f max %.0f (budget 15000)' % tuple(np.percentile(R.per_lot[fb], [0, 50, 100])))
print('fallback rows by symbol (top):', R[fb].symbol.value_counts().head(12).to_dict())
J = json.load(open(SP + '/hunt/six_month/six_month.json'))
MODELS = {'Opus (T1), live model': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6)}
out = {}
print('\nREAL picked trades with the 1-lot fallback (scanner sizing on cash price/stop = 0 lots, o_qty = 1 lot):')
print('  %-44s %4s %5s %10s %10s %10s %11s %8s' % ('model', 'n', 'fb', 'opt fb', 'fut fb', 'opt total', 'opt ex-fb', 'qty NaN'))
for name, spec in MODELS.items():
    t = H.run(R, spec)
    f = t.sc_lots == 0
    o = {'n': len(t), 'fallback_rows': int(f.sum()), 'opt_fallback': round(float(t.pnl[f].sum())), 'fut_fallback': round(float(t.fut[f].sum())),
         'opt_total': round(float(t.pnl.sum())), 'opt_excl_fallback': round(float(t.pnl[~f].sum())), 'qty_nan_or_0': int((t.o_qty.isna() | (t.o_qty <= 0)).sum()),
         'premium_fallback': round(float(H.option_net(t[f], 'T1', detail=True).outlay.sum())) if f.any() else 0}
    out[name] = o
    print('  %-44s %4d %5d %+10d %+10d %+10d %+11d %8d' % (name[:44], o['n'], o['fallback_rows'], o['opt_fallback'], o['fut_fallback'], o['opt_total'], o['opt_excl_fallback'], o['qty_nan_or_0']))
json.dump(out, open(SP + '/hunt/six_month/sources/c6b_result.json', 'w'), indent=1)
# unseen: proxy sizing is the scanner's own (0-lot rows were dropped as over_budget), so no fallback possible
U = D['unseen']
print('\nUNSEEN: o_qty == lot*lots for all rows:', bool(((U.o_qty - U.lot * U.lots).abs() < 0.5).all()), '| lots min', int(U.lots.min()))
