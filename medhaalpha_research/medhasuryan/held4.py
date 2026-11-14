# Held-across-days backtest of the four app models (Opus T1, Opus v3 T1, Fable-OP T3, MedhaSuryan T3 / T1 on Nifty
# downtrend days), both six-month periods. Each pick is followed on the stock's cash one-minute candles from the minute
# after the signal until its target or its fixed stop, carried overnight, and sold at 15:15 on the session before the
# contract's expiry (the app's rule for scanner trades). Records when T1, T2 and T3 were reached and in how many
# trading sessions. Cash candles stand in for futures (no multi-day futures history is kept).
import json, sys
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
nd = sorted({d for d in pd.Series(nifty.index.date).unique()})
counts = pd.Series(nifty.index.date).value_counts()
SESS = sorted(d for d in nd if counts[d] >= 300)            # full sessions (Muhurat etc. left out)
SIDX = {d: i for i, d in enumerate(SESS)}


def sessions_between(d0, d1):
    """Trading sessions after d0 up to and including d1 (0 = same day)."""
    return sum(1 for d in SESS if d0 < d <= d1)


def cutoff_for(expiry: str):
    """15:15 IST on the last full session before the expiry date."""
    e = pd.Timestamp(expiry).date()
    before = [d for d in SESS if d < e]
    d = before[-1] if before else e
    return pd.Timestamp(f"{d} 15:15").tz_localize('Asia/Kolkata')


MODELS = {'Opus': lambda df: H.pick(df, 's_opus', 75).assign(pol='T1'),
          'Opus v3': lambda df: H.pick(df, 's_opus_v3', 75).assign(pol='T1'),
          'Fable-OP': lambda df: H.pick(df, 's_fable_op', 75).assign(pol='T3'),
          'MedhaSuryan': H.switch1}
out = {'generated': pd.Timestamp.now(tz='Asia/Kolkata').isoformat(timespec='seconds'), 'sets': {}}
for s, label in (('real', '12 May - 11 Nov 2026'), ('unseen', '3 Nov 2025 - 11 May 2026')):
    df = D[s]
    picks = {m: f(df) for m, f in MODELS.items()}
    rows = sorted(set().union(*[set(p.index) for p in picks.values()]))
    sim = {}
    for i in rows:
        r = df.loc[i]
        m = mins.get(r.symbol)
        sign = 1 if r.side == 'LONG' else -1
        et = pd.Timestamp(f"{r.day} {r.time}").tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
        if s == 'unseen':
            e0, stop, tg = float(r.entry_ref), float(r.stop), [float(r.t1), float(r.t2), float(r.t3)]
        else:
            e0 = float(r.price)
            risk = float(r.risk_pct) / 100 * e0
            stop = e0 - sign * risk
            tg = [e0 + sign * k * risk for k in (cfg.t1_r, cfg.t2_r, cfg.t3_r)]
        cut = cutoff_for(r.o_expiry)
        rec = {'day': r.day, 'time': r.time, 'symbol': r.symbol, 'side': r.side, 'setup': r.setup, 'regime': r.regime,
               'entry_ref': round(e0, 2), 'stop': round(stop, 2), 't1': round(tg[0], 2), 't2': round(tg[1], 2),
               't3': round(tg[2], 2), 'expiry': r.o_expiry, 'sell_by': cut.isoformat()}
        if m is None or m.empty:
            rec['status'] = 'no_data'
            sim[i] = rec
            continue
        dm = m[(m.index >= et) & (m.index <= cut)]
        dm = dm[(dm.index.time >= pd.Timestamp('09:15').time()) & (dm.index.time <= pd.Timestamp('15:29').time())]
        if dm.empty:
            rec['status'] = 'no_data'
            sim[i] = rec
            continue
        res = run_policies(dm, r.side, stop, tg, dm.index[0], close_at_eod=False)
        L = lot.get(r.symbol, (np.nan, 0.05))[0]
        n = lots_for(r.side, e0, stop, int(L), cfg) if L == L else 0
        qty = (n if n else 1) * (int(L) if L == L else 0)
        rec['qty'] = qty
        for p in ('T1', 'T2', 'T3'):
            o = res[p]
            st = o.status if o.status != 'open' else 'expiry'
            xd = pd.Timestamp(o.exit_ts).date() if o.exit_ts else None
            net = None
            if qty and o.status != 'no_data':
                net = round(o.points * qty - C.round_trip('FUT', o.entry, o.exit, qty, r.side, cfg.brokerage_per_order, cfg.brokerage_pct)
                            - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
            rec[p] = {'status': st, 'at': o.exit_ts, 'days': sessions_between(et.date(), xd) if xd else None,
                      'r': o.r, 'exit': o.exit, 'net': net}
        rec['entry'] = res['T1'].entry
        rec['status'] = 'ok'
        sim[i] = rec
    S = {'label': label, 'sessions': int(df.day.nunique()), 'models': {}}
    for mname, p in picks.items():
        trades = []
        for i, pol in zip(p.index, p.pol):
            rec = dict(sim[i], exit_plan=pol)
            trades.append(rec)
        ok = [t for t in trades if t['status'] == 'ok']
        n = len(ok)
        summ = {'trades': len(trades), 'priced': n}
        for q in ('T1', 'T2', 'T3'):
            hit = [t[q]['days'] for t in ok if t[q]['status'] == 'target']
            summ[q] = {'hit': len(hit), 'pct': round(100 * len(hit) / n, 1) if n else 0, 'same_day': sum(d == 0 for d in hit),
                       'median_days': float(np.median(hit)) if hit else None, 'max_days': max(hit) if hit else None,
                       'by_days': {str(k): int(v) for k, v in pd.Series(hit).value_counts().sort_index().items()}}
        summ['stopped_before_T1'] = sum(t['T1']['status'] == 'stopped' for t in ok)
        own = [t[t['exit_plan']] for t in ok]
        summ['own_exit'] = {'net': round(sum(o['net'] or 0 for o in own)), 'targets': sum(o['status'] == 'target' for o in own),
                            'stopped': sum(o['status'] == 'stopped' for o in own), 'sold_before_expiry': sum(o['status'] == 'expiry' for o in own),
                            'median_days_held': float(np.median([o['days'] for o in own])) if own else None}
        S['models'][mname] = {'summary': summ, 'trades': trades}
        print(s, mname, json.dumps(summ)[:600])
    out['sets'][s] = S
json.dump(out, open(SP + '/hunt/held4/held4.json', 'w'), default=str)
