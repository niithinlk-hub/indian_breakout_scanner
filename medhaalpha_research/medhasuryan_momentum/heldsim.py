"""Held-across-days simulation (target or fixed stop, carried overnight, sold 15:15 on the session before expiry), rebuilt
without the scanner's source so it can run from this repository. It follows the research's held4.py:
  * cash one-minute candles stand in for futures; entry = open of the minute after the signal;
  * stop and targets from the signal price (real set: price and risk_pct, T1/T2/T3 = 1.0/1.9/2.6 R; unseen set: the
    replay's stored entry_ref, stop, t1-t3);
  * per bar: the stop is checked first (a bar touching both is a stop); a bar that opens beyond a level fills at the open;
  * lots: whole futures lots so the loss at the stop incl. charges and 0.02 % slippage a side is at most Rs 15,000,
    at least 1 lot; lot sizes from the replay data (as held4.py);
  * futures charges: Rs 20 brokerage an order, exchange 0.00173 %, SEBI 0.0001 %, stamp 0.002 % on the buy, STT
    0.05 % on the sell, 18 % GST on brokerage+exchange+SEBI, plus 0.02 % slippage a side.
Validated trade by trade against the research's stored held results (medhasuryan/bt4.json); see validate_held.py."""
import pickle
import numpy as np, pandas as pd

RISK_RS = 15000.0
T_R = (1.0, 1.9, 2.6)


def fut_costs(entry, exit_, qty, side):
    buy, sell = (entry, exit_) if side == 'LONG' else (exit_, entry)
    bv, sv = buy * qty, sell * qty
    brk = 40.0
    exch = (bv + sv) * 0.00173 / 100
    sebi = (bv + sv) * 1e-6
    stamp = bv * 0.002 / 100
    stt = sv * 0.05 / 100
    gst = 0.18 * (brk + exch + sebi)
    slip = (entry + exit_) * qty * 0.02 / 100
    return brk + exch + sebi + stamp + stt + gst + slip


def lots_for(side, entry, stop, lot):
    per = abs(entry - stop) * lot + fut_costs(entry, stop, lot, side)
    return int(RISK_RS // per) if per > 0 else 0


def _merge(frames):
    fr = [f for f in frames if f is not None and len(f)]
    if not fr:
        return None
    m = pd.concat(fr)
    m = m[~m.index.duplicated(keep='last')].sort_index()
    return m


class Data:
    def __init__(self, rp):
        parts = [pickle.load(open(rp + '/v2/data/' + f, 'rb')) for f in ('pre.pkl', 'early.pkl')]
        late = pickle.load(open(rp + '/replay_sep/minutes.pkl', 'rb'))
        keys = parts[-1]['keys']
        self.mins = {}
        for s, k in keys.items():
            m = _merge([p['minutes'].get(k) for p in parts] + [late['minutes'].get(k)])
            if m is not None:
                t = m.index.time
                m = m[(t >= pd.Timestamp('09:15').time()) & (t <= pd.Timestamp('15:29').time())]
            self.mins[s] = m
        self.lot = late['lot']
        nifty = _merge([p['nifty'] for p in parts])
        cnt = pd.Series(nifty.index.date).value_counts()
        self.sess = sorted(d for d in cnt.index if cnt[d] >= 300)
        del parts, late

    def sessions_between(self, d0, d1):
        return sum(1 for d in self.sess if d0 < d <= d1)

    def sell_by(self, expiry):
        e = pd.Timestamp(expiry).date()
        before = [d for d in self.sess if d < e]
        return pd.Timestamp(f"{before[-1] if before else e} 15:15").tz_localize('Asia/Kolkata')


def walk(o, h, l, c, sgn, stop, target):
    if sgn > 0:
        sh, th = (o <= stop) | (l <= stop), (o >= target) | (h >= target)
    else:
        sh, th = (o >= stop) | (h >= stop), (o <= target) | (l <= target)
    n = len(o)
    i_s = int(np.argmax(sh)) if sh.any() else n
    i_t = int(np.argmax(th)) if th.any() else n
    if i_s < n and i_s <= i_t:
        gap = (o[i_s] <= stop) if sgn > 0 else (o[i_s] >= stop)
        return (float(o[i_s]) if gap else float(stop)), i_s, 'stopped'
    if i_t < n:
        gap = (o[i_t] >= target) if sgn > 0 else (o[i_t] <= target)
        return (float(o[i_t]) if gap else float(target)), i_t, 'target'
    return float(c[-1]), n - 1, 'expiry'


def levels(r, setname):
    sgn = 1 if r.side == 'LONG' else -1
    if setname == 'real':
        e0 = float(r.price)
        risk = float(r.risk_pct) / 100 * e0
        return e0, e0 - sgn * risk, [e0 + sgn * k * risk for k in T_R]
    return float(r.entry_ref), float(r.stop), [float(r.t1), float(r.t2), float(r.t3)]


def held_trade(DT, r, setname, pols=('T1', 'T2', 'T3')):
    sgn = 1 if r.side == 'LONG' else -1
    e0, stop, tg = levels(r, setname)
    et = pd.Timestamp(f"{r.day} {r.time}").tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
    m = DT.mins.get(r.symbol)
    if m is None or m.empty:
        return None
    dm = m[(m.index >= et) & (m.index <= DT.sell_by(r.o_expiry))]
    if dm.empty:
        return None
    o, h, l, c = (dm[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
    L = DT.lot.get(r.symbol, (np.nan, 0.05))[0]
    if L != L:
        return None
    n = lots_for(r.side, e0, stop, int(L))
    qty = (n if n else 1) * int(L)
    out = {'qty': qty, 'entry': float(o[0])}
    for p in pols:
        x, i, st = walk(o, h, l, c, sgn, stop, tg[int(p[1]) - 1])
        net = sgn * (x - o[0]) * qty - fut_costs(o[0], x, qty, r.side)
        out[p] = {'status': st, 'exit': x, 'net': round(net, 2), 'days': DT.sessions_between(et.date(), dm.index[i].date()),
                  'at': dm.index[i].isoformat()}
    return out
