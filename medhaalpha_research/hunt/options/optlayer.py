# Builds the option inputs for every signal row in harness sets real / unseen / known:
#   F0 (underlying at entry), entry_ts, risk_abs, and per exit policy P: F1_P (underlying at exit), exit_ts_P;
#   plus expiry (scanner's rule: monthly contract, next month once <= 4 sessions remain), qty (lots x lot), kind, iv.
# Proxy sets: entry/exit prices and times straight from the scanner's replay records.
# Real set: the scanner's real-futures R per policy, with exit times found by replaying the same stop/targets on cash
#   one-minute candles (the real record has no exit times).
import glob, json, sys, pickle
import numpy as np, pandas as pd
SP = sys.argv[1]
sys.path.insert(0, SP + '/hunt'); sys.path.insert(0, SP + '/v2/patched')
import harness as H
from scanner.equity.fills import run_policies
from scanner.equity.scan import lots_for
from scanner.equity.config import EqConfig
cfg = EqConfig()
POL = H.POL
D = H.load_all()

# ------------------------------------------------------------------ expiry calendar
nd = json.load(open(SP + '/v2/data/nifty_daily.json'))['data']['candles']
SESS = sorted({c[0][:10] for c in nd})
SSET, LAST = set(SESS), SESS[-1]


def is_session(d):
    ds = d.strftime('%Y-%m-%d')
    return ds in SSET if ds <= LAST else d.weekday() < 5


KNOWN_EXP = {'2026-11': '2026-11-23'}     # seen on the real option contracts (24 Nov 2026 is a holiday)


def month_expiry(y, m):
    k = '%04d-%02d' % (y, m)
    if k in KNOWN_EXP:
        return KNOWN_EXP[k]
    d = pd.Timestamp(y, m, 1) + pd.offsets.MonthEnd(0)
    while d.weekday() != 1:                 # last Tuesday (NSE stock derivatives from Sep 2025)
        d -= pd.Timedelta(days=1)
    while not is_session(d):
        d -= pd.Timedelta(days=1)
    return d.strftime('%Y-%m-%d')


def sessions_until(day, exp):
    return sum(1 for d in pd.date_range(day, exp) if is_session(d))


def expiry_for(day, roll=4):
    t = pd.Timestamp(day)
    e = month_expiry(t.year, t.month)
    if e < day or sessions_until(day, e) <= roll:
        n = t + pd.offsets.MonthBegin(1)
        e = month_expiry(n.year, n.month)
    return e


def next_expiry(exp):
    t = pd.Timestamp(exp) + pd.offsets.MonthBegin(1)
    return month_expiry(t.year, t.month)


EXP = {d: expiry_for(d) for s in D for d in D[s].day.unique()}

# ------------------------------------------------------------------ proxy sets
def proxy_inputs(name, pdir):
    df = D[name]
    rec = {}
    for p in sorted(glob.glob(pdir + '/proxy_*.json')):
        doc = json.load(open(p))
        for s in doc['signals']:
            if s['setup'] not in ('A', 'B') or s['fut']['T1']['status'] == 'no_data':
                continue
            k = (doc['day'], s['time'], s['symbol'], s['setup'])
            r = {'F0': s['fut']['T1']['entry'], 'qty': s['lot'] * s['lots'], 'risk_abs': s['risk']}
            for q in POL:
                o = s['fut'].get(q) or {}
                r['F1_' + q], r['exit_ts_' + q] = o.get('exit', np.nan), o.get('exit_ts')
            et = pd.Timestamp(doc['day'] + ' ' + s['time']).tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
            r['entry_ts'] = et.isoformat()
            assert k not in rec, k
            rec[k] = r
    rows = [rec[(r.day, r.time, r.symbol, r.setup)] for r in df.itertuples()]
    return pd.DataFrame(rows, index=df.index)


# ------------------------------------------------------------------ real set
def real_inputs():
    df = D['real']
    mins, daily, nifty, lot = H.minute_data()
    out, agree, tot = [], 0, 0
    for r in df.itertuples():
        m = mins.get(r.symbol)
        sign = 1 if r.side == 'LONG' else -1
        et = pd.Timestamp(r.day + ' ' + r.time).tz_localize('Asia/Kolkata') + pd.Timedelta(minutes=1)
        rec = {'entry_ts': et.isoformat(), 'F0': np.nan, 'qty': np.nan, 'risk_abs': np.nan}
        if m is not None and len(m):
            dm = m[(m.index >= et) & (m.index.date == et.date())]
            if len(dm):
                e0 = r.price
                risk = r.risk_pct / 100.0 * e0
                stop = e0 - sign * risk
                tg = [e0 + sign * k * risk for k in (cfg.t1_r, cfg.t2_r, cfg.t3_r)]
                res = run_policies(dm, r.side, stop, tg, dm.index[0], close_at_eod=True)
                F0 = float(dm.open.iloc[0])
                L, tick = lot.get(r.symbol, (np.nan, 0.05))
                n = lots_for(r.side, e0, stop, int(L), cfg) if L == L else 0
                # 0 lots = one lot already loses more than Rs 15,000 at the stop; the futures leg still traded, so take 1 lot
                rec.update({'F0': F0, 'qty': (n if n else 1) * L, 'risk_abs': abs(F0 - stop)})
                for q in POL:
                    o = res.get(q)
                    rr = getattr(r, 'r_' + q)
                    rec['F1_' + q] = F0 + sign * rr * abs(F0 - stop) if rr == rr else np.nan     # the REAL futures R, cash level
                    rec['exit_ts_' + q] = o.exit_ts if o is not None and o.status != 'no_data' else None
                    if o is not None and o.status != 'no_data' and rr == rr:
                        tot += 1
                        agree += (np.sign(round(o.r, 1)) == np.sign(round(rr, 1)))
        out.append(rec)
    print('real set: cash replay agrees with the real futures result in sign on %d of %d row-policies (%.0f%%)' % (agree, tot, 100 * agree / max(tot, 1)))
    return pd.DataFrame(out, index=df.index)


if __name__ == '__main__':
    I = {'unseen': proxy_inputs('unseen', SP + '/v2/proxy_unseen'), 'known': proxy_inputs('known', SP + '/v2/proxy_known'), 'real': real_inputs()}
    c = np.load(SP + '/hunt/options/ivfit2.npy')
    for s, X in I.items():
        df = D[s]
        X['expiry'] = df.day.map(EXP)
        X['next_expiry'] = X.expiry.map(next_expiry)
        X['kind'] = np.where(df.side == 'LONG', 'CE', 'PE')
        rv = df.atr_pct * np.sqrt(252) / 100 / 1.25
        X['iv'] = np.exp(c[0] + c[1] * np.log(rv) + c[2] * (X.kind == 'PE'))
        print(s, len(X), 'rows; missing F0 %d, qty %d; expiries %s' % (X.F0.isna().sum(), X.qty.isna().sum(), sorted(X.expiry.unique())[:3]))
    out = sys.argv[2] if len(sys.argv) > 2 else SP + '/hunt/opt_inputs.pkl'
    pickle.dump(I, open(out, 'wb'))
    print('saved', out)
