# Check 6c: does the option quantity o_qty equal the futures quantity the scanner actually traded (real set)?
# The real record (pull.json) has no quantity. Infer it from the costs: per row, the 7 exit policies give
# net_p = A * r_p - c_p (A = qty x risk per unit, c_p = charges + slippage, almost constant across policies).
# OLS of net on r over the policies with distinct r gives A (slope) and c (cost at r=0). Charges scale with qty,
# so qty_fut = the lot multiple whose modelled cost (scanner's costs.round_trip + slippage) is closest to c.
import sys, json
import numpy as np, pandas as pd
SP = '/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP + '/hunt'); sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
cfg = EqConfig()
D = H.load_all()
Q = pd.read_pickle(SP + '/hunt/six_month/sources/real_qty.pkl')
R = D['real'].copy()
R['L'] = Q.L.values
R['o_lots'] = R.o_qty / R.L
POL = H.POL


def cost(P, n, L, side):
    q = n * L
    return C.round_trip('FUT', P, P, q, side, cfg.brokerage_per_order, cfg.brokerage_pct) + C.slippage(P, P, q, cfg.slippage_pct)


est, fitA, fitc, resid = [], [], [], []
for r in R.itertuples():
    rr = np.array([getattr(r, 'r_' + p) for p in POL], float)
    nn = np.array([getattr(r, 'net_' + p) for p in POL], float)
    u = pd.DataFrame({'r': rr, 'n': nn}).drop_duplicates()
    if len(u) < 2 or (u.r.max() - u.r.min()) < 0.3:
        est.append(np.nan); fitA.append(np.nan); fitc.append(np.nan); resid.append(np.nan)
        continue
    A, b = np.polyfit(u.r, u.n, 1)
    c = -b
    cands = np.arange(1, 61)
    cm = np.array([cost(r.price, k, r.L, r.side) for k in cands])
    k = int(cands[np.argmin(np.abs(cm - c))])
    est.append(k); fitA.append(A); fitc.append(c); resid.append((c - cost(r.price, k, r.L, r.side)) / max(cost(r.price, 1, r.L, r.side), 1))
R['fut_lots_est'], R['A'], R['c'], R['cres'] = est, fitA, fitc, resid
ok = R.fut_lots_est.notna()
good = ok & (R.cres.abs() < 0.35)          # cost fits a lot multiple to within 35 % of one lot's cost
print('rows with >=2 distinct R across policies: %d of %d; clean lot fit: %d' % (ok.sum(), len(R), good.sum()))
agree = (R.fut_lots_est == R.o_lots)
print('clean-fit rows where inferred futures lots == option lots: %d of %d (%.1f%%)' % ((agree & good).sum(), good.sum(), 100 * (agree & good).sum() / good.sum()))
print('ratio option lots / futures lots on clean-fit rows: quantiles', np.round(np.quantile((R.o_lots / R.fut_lots_est)[good], [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]), 3).tolist())
print('A (Rs at stop) on clean-fit rows: median %.0f, share > 15,500: %.1f%%' % (R.A[good].median(), 100 * (R.A[good] > 15500).mean()))
# check the method on unseen, where the true qty is known (proxy lot x lots)
U = D['unseen'].copy()
ue = []
for r in U.sample(600, random_state=1).itertuples():
    rr = np.array([getattr(r, 'r_' + p) for p in POL], float); nn = np.array([getattr(r, 'net_' + p) for p in POL], float)
    u = pd.DataFrame({'r': rr, 'n': nn}).drop_duplicates()
    if len(u) < 2 or (u.r.max() - u.r.min()) < 0.3:
        continue
    A, b = np.polyfit(u.r, u.n, 1)
    cands = np.arange(1, 61)
    cm = np.array([cost(r.entry_ref, k, r.lot, r.side) for k in cands])
    k = int(cands[np.argmin(np.abs(cm + b))])
    res = (-b - cost(r.entry_ref, k, r.lot, r.side)) / max(cost(r.entry_ref, 1, r.lot, r.side), 1)
    ue.append((k, r.lots, abs(res) < 0.35))
ue = pd.DataFrame(ue, columns=['est', 'true', 'clean'])
print('method check on unseen (true lots known): clean fits %d of %d, exact %.1f%% of clean' % (ue.clean.sum(), len(ue), 100 * (ue.est == ue.true)[ue.clean].mean()))

MODELS = {'Opus (T1), live model': ('s_opus', 75, 'T1', 6), 'Opus v2 (T1)': ('s_opus_v2', 75, 'T1', 6), 'Opus v3 (T1)': ('s_opus_v3', 75, 'T1', 6),
          'Fable (T3)': ('s_fable', 75, 'T3', 6), 'Fable-OP (T3)': ('s_fable_op', 75, 'T3', 6), 'Switch-1': H.switch1,
          'Opus v3, trailing stop to close (CLOSE_TR)': ('s_opus_v3', 75, 'CLOSE_TR', 6)}
out = {}
print('\npicked real trades: option lots vs inferred futures lots (clean fits only)')
for name, spec in MODELS.items():
    t = H.run(R, spec)
    g = t.fut_lots_est.notna() & (t.cres.abs() < 0.35)
    more, less = g & (t.o_lots > t.fut_lots_est), g & (t.o_lots < t.fut_lots_est)
    # option net if the option used the inferred futures lots on the mismatched rows
    adj = 0.0
    for p in t.pol.unique():
        m = (more | less) & (t.pol == p)
        if m.any():
            adj += float(H.option_net(t[m], p, qty=(t.fut_lots_est[m] * t.L[m]).to_numpy()).sum()) - float(t.pnl[m].sum())
    out[name] = {'n': len(t), 'clean': int(g.sum()), 'equal': int((g & (t.o_lots == t.fut_lots_est)).sum()), 'opt_more_lots': int(more.sum()), 'opt_fewer_lots': int(less.sum()),
                 'opt_net_mismatched_rows': round(float(t.pnl[more | less].sum())), 'opt_change_if_fut_lots': round(adj)}
    print('  %-44s %s' % (name[:44], out[name]))
json.dump(out, open(SP + '/hunt/six_month/sources/c6c_result.json', 'w'), indent=1)
R[['day', 'time', 'symbol', 'side', 'price', 'L', 'o_lots', 'fut_lots_est', 'A', 'c', 'cres']].to_pickle(SP + '/hunt/six_month/sources/real_fut_lots.pkl')
