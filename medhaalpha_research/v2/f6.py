# Trade management test on the same trades and cash candles: move the stop to the entry price once the trade has gone
# part of the way to T1 (takes effect from the next candle; inside a candle the old stop applies, and stop beats target).
import dataclasses, gzip, json, os, pickle, sys, warnings
warnings.filterwarnings('ignore')
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
sys.path.insert(0, sys.argv[1] + '/v2')
import numpy as np, pandas as pd
from base import SP
from frame import load
from lab import *
from scanner.series import merge_frames
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.levels import build_levels
from scanner.equity.scan import lots_for
from scanner.equity.universe_upstox import parse

cfg = EqConfig()
df = load()
A = df[df.design | df.unseen].copy()
rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
A['v3'] = np.where(A.long == 1, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), np.maximum(A.t_opus, A.t_fable_op))
idx = live_df(A, 'v3', 75)
early = pickle.load(open(SP + '/v2/data/early.pkl', 'rb'))
late = pickle.load(open(SP + '/replay_sep/minutes.pkl', 'rb'))
uni = parse(json.loads(gzip.decompress(open(SP + '/test/NSE.json.gz', 'rb').read())))
mins = {}
for s in sorted({A.symbol[i] for i in idx}):
    k = early['keys'][s]
    m = regular(merge_frames(early['minutes'].get(k), late['minutes'].get(k)), cfg)
    mins[s] = {d: g for d, g in m.groupby(m.index.date)}
del early, late


def sim(m, side, stop, t1, trig, ets):
    m = m[m.index >= ets]
    o, h, l, c = m['open'].to_numpy(), m['high'].to_numpy(), m['low'].to_numpy(), m['close'].to_numpy()
    e, sg, cur, moved = float(o[0]), (1 if side == 'LONG' else -1), stop, False
    for i in range(len(m)):
        if sg * (o[i] - cur) <= 0:
            return ('be' if moved else 'stopped'), e, float(o[i])
        if (l[i] <= cur) if sg > 0 else (h[i] >= cur):
            return ('be' if moved else 'stopped'), e, cur
        if (h[i] >= t1) if sg > 0 else (l[i] <= t1):
            return 'target', e, (float(o[i]) if sg * (o[i] - t1) >= 0 else t1)
        if trig is not None and not moved and ((h[i] >= trig) if sg > 0 else (l[i] <= trig)):
            cur, moved = e, True
    return 'close', e, float(c[-1])


VAR = (('as now', None), ('stop to entry after 0.4R', 0.4), ('after 0.5R', 0.5), ('after 0.6R', 0.6), ('after 0.7R', 0.7), ('after 0.8R', 0.8))
res = {v: [] for v, _ in VAR}
for i in idx:
    r = rows[df.index.get_loc(i)]
    snap, side = r['f'], r['side']
    f = uni.pick_future(r['symbol'], pd.Timestamp('2026-11-13').date(), cfg.roll_sessions)
    m = mins[r['symbol']][pd.Timestamp(r['day']).date()]
    ets = pd.Timestamp('%sT%s:00+05:30' % (r['day'], r['time'])) + pd.Timedelta(minutes=1)
    lv = build_levels(side, snap['price'], snap.get('atr_pct') or 0.0, snap, f.tick, cfg)
    lots = lots_for(side, lv.entry_ref, lv.stop, f.lot_size, cfg)
    if lots == 0 or m[m.index >= ets].empty:
        continue
    sg = 1 if side == 'LONG' else -1
    qty = f.lot_size * lots
    for v, tr in VAR:
        st, e, x = sim(m, side, lv.stop, lv.t1, None if tr is None else lv.entry_ref + sg * tr * lv.risk, ets)
        net = sg * (x - e) * qty - C.round_trip('FUT', e, x, qty, side, cfg.brokerage_per_order, cfg.brokerage_pct) - C.slippage(e, x, qty, cfg.slippage_pct)
        res[v].append({'side': side, 'half': 'H1' if A.design[i] else 'H2', 'month': A.month[i], 'status': st, 'net': net})
print('%-26s %5s %6s %7s %8s %7s %6s %9s %9s %9s | months better than "as now"' % ('rule', 'n', 'hit%', 'stop%', 'scratch%', 'close%', 'won%', 'net', 'net H1', 'net H2'))
base = pd.DataFrame(res['as now']).groupby('month').net.sum()
out = {}
for v, _ in VAR:
    t = pd.DataFrame(res[v])
    bm = t.groupby('month').net.sum()
    out[v] = {'n': len(t), 'hit': 100 * (t.status == 'target').mean(), 'stop': 100 * (t.status == 'stopped').mean(), 'be': 100 * (t.status == 'be').mean(), 'net': t.net.sum(),
              'h1': t[t.half == 'H1'].net.sum(), 'h2': t[t.half == 'H2'].net.sum(), 'months_better': int((bm > base).sum())}
    print('%-26s %5d %6.1f %7.1f %8.1f %7.1f %6.1f %+9.0f %+9.0f %+9.0f | %d of 7' % (v, len(t), out[v]['hit'], out[v]['stop'], out[v]['be'], 100 * (t.status == 'close').mean(), 100 * (t.net > 0).mean(),
          out[v]['net'], out[v]['h1'], out[v]['h2'], out[v]['months_better']))
json.dump(out, open(SP + '/v2/f6.json', 'w'))
