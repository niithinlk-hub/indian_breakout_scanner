# Held-across-days results (target or stop, sold 15:15 the session before expiry) for every A/B signal whose MedhaSuryan
# score is at least 50, so any cutoff from 50 up can be priced. Same simulation as held4.py.
import json, sys, pickle
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity.fills import run_policies
from scanner.equity.scan import lots_for
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
cfg = EqConfig()
D = H.load_all()
mins, daily, nifty, lot = H.minute_data()
counts = pd.Series(nifty.index.date).value_counts()
SESS = sorted(d for d in counts.index if counts[d] >= 300)


def sessions_between(d0, d1):
    return sum(1 for d in SESS if d0 < d <= d1)


def cutoff_for(expiry):
    e = pd.Timestamp(expiry).date()
    before = [d for d in SESS if d < e]
    return pd.Timestamp(f"{before[-1] if before else e} 15:15").tz_localize('Asia/Kolkata')


out = {}
for s in ('real', 'unseen'):
    df = D[s]
    ms = np.where(df.regime == 'Downtrend', df.s_opus_v3, df.s_fable_op)
    rows = df.index[ms >= 50]
    res_s = {}
    for i in rows:
        r = df.loc[i]
        sign = 1 if r.side == 'LONG' else -1
        et = pd.Timestamp(f"{r.day} {r.time}").tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
        if s == 'unseen':
            e0, stop, tg = float(r.entry_ref), float(r.stop), [float(r.t1), float(r.t2), float(r.t3)]
        else:
            e0 = float(r.price); risk = float(r.risk_pct) / 100 * e0; stop = e0 - sign * risk
            tg = [e0 + sign * k * risk for k in (cfg.t1_r, cfg.t2_r, cfg.t3_r)]
        m = mins.get(r.symbol)
        if m is None or m.empty:
            continue
        dm = m[(m.index >= et) & (m.index <= cutoff_for(r.o_expiry))]
        dm = dm[(dm.index.time >= pd.Timestamp('09:15').time()) & (dm.index.time <= pd.Timestamp('15:29').time())]
        if dm.empty:
            continue
        res = run_policies(dm, r.side, stop, tg, dm.index[0], close_at_eod=False)
        L = lot.get(r.symbol, (np.nan, 0.05))[0]
        n = lots_for(r.side, e0, stop, int(L), cfg) if L == L else 0
        qty = (n if n else 1) * (int(L) if L == L else 0)
        rec = {}
        for p in ('T1', 'T3'):
            o = res[p]
            net = (o.points * qty - C.round_trip('FUT', o.entry, o.exit, qty, r.side, cfg.brokerage_per_order, cfg.brokerage_pct)
                   - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct)) if qty else 0.0
            rec[p] = {'status': o.status, 'net': round(net, 2), 'days': sessions_between(et.date(), pd.Timestamp(o.exit_ts).date()) if o.exit_ts else None}
        res_s[int(i)] = rec
    out[s] = res_s
    print(s, 'signals with MedhaSuryan score >= 50:', len(rows), 'simulated:', len(res_s), flush=True)
pickle.dump(out, open(SP + '/hunt/cutoff/held_all.pkl', 'wb'))
