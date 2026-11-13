# Stop placement test. Same trades (v2 + longs need relative volume >= 1 + shorts may qualify on Fable-OP), same entries;
# only the stop/target rules change. Levels are rebuilt with the scanner's level code at the signal minute and the day
# is replayed on the cash share's 1-minute candles (the expired futures cannot be read). Same-day exit at T1.
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
from scanner.equity.fills import run_policies
from scanner.equity.levels import build_levels
from scanner.equity.scan import lots_for
from scanner.equity.universe_upstox import parse

cfg0 = EqConfig()
df = load()
A = df[df.design | df.unseen].copy()
rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
assert len(rows) == len(df)
lgm = A.long == 1
A['v3'] = np.where(lgm, np.where(A.rel_vol < 1.0, 0.0, A.t_fable_op), np.maximum(A.t_opus, A.t_fable_op))
idx = live_df(A, 'v3', 75)
print('picks', len(idx), line('truth (real futures)', stat(A, idx))[40:150])
early = pickle.load(open(SP + '/v2/data/early.pkl', 'rb'))
late = pickle.load(open(SP + '/replay_sep/minutes.pkl', 'rb'))
uni = parse(json.loads(gzip.decompress(open(SP + '/test/NSE.json.gz', 'rb').read())))
need = sorted({A.symbol[i] for i in idx})
mins = {}
for s in need:
    k = early['keys'][s]
    m = regular(merge_frames(early['minutes'].get(k), late['minutes'].get(k)), cfg0)
    mins[s] = {d: g for d, g in m.groupby(m.index.date)}
del early, late
V = {'as now (stop 0.3-0.9 ATR, aim 0.5)': {},
     'floor 0.4 ATR': dict(stop_atr_min=0.4),
     'floor 0.5 ATR, aim 0.6': dict(stop_atr_min=0.5, stop_atr_target=0.6),
     'floor 0.6 ATR, aim 0.7': dict(stop_atr_min=0.6, stop_atr_target=0.7),
     'floor 0.7 ATR, aim 0.8, cap 1.1': dict(stop_atr_min=0.7, stop_atr_target=0.8, stop_atr_max=1.1),
     'aim 0.7 (floor 0.3)': dict(stop_atr_target=0.7),
     'as now, T1 at 0.8R': dict(t1_r=0.8),
     'floor 0.5 aim 0.6, T1 at 0.8R': dict(stop_atr_min=0.5, stop_atr_target=0.6, t1_r=0.8),
     'floor 0.6 aim 0.7, T1 at 0.7R': dict(stop_atr_min=0.6, stop_atr_target=0.7, t1_r=0.7)}
res = {v: [] for v in V}
for i in idx:
    r = rows[df.index.get_loc(i)]
    assert r['symbol'] == A.symbol[i] and r['day'] == A.day[i] and r['time'] == A.time[i]
    snap, side = r['f'], r['side']
    f = uni.pick_future(r['symbol'], pd.Timestamp('2026-11-13').date(), cfg0.roll_sessions)
    m = mins[r['symbol']][pd.Timestamp(r['day']).date()]
    ets = pd.Timestamp('%sT%s:00+05:30' % (r['day'], r['time'])) + pd.Timedelta(minutes=1)
    for v, kw in V.items():
        cfg = dataclasses.replace(cfg0, **kw)
        lv = build_levels(side, snap['price'], snap.get('atr_pct') or 0.0, snap, f.tick, cfg)
        lots = lots_for(side, lv.entry_ref, lv.stop, f.lot_size, cfg)
        o = run_policies(m, side, lv.stop, lv.targets, ets, close_at_eod=True)['T1']
        if o.status == 'no_data':
            continue
        one = o.points * f.lot_size - C.round_trip('FUT', o.entry, o.exit, f.lot_size, side, cfg.brokerage_per_order, cfg.brokerage_pct) - C.slippage(o.entry, o.exit, f.lot_size, cfg.slippage_pct)
        res[v].append({'i': i, 'side': side, 'half': 'H1' if A.design[i] else 'H2', 'status': o.status, 'r': o.r, 'lots': lots, 'net': one * lots, 'net1lot': one,
                       'stop_atr': lv.stop_atr, 'risk_pct': lv.risk / lv.entry_ref * 100, 'mins': (pd.Timestamp(o.exit_ts) - ets).total_seconds() / 60, 'true': A.out[i]})
out = {}
print('\n%-34s %5s %5s %6s %6s %6s %9s %9s %9s | %-21s | %s' % ('stop rule', 'taken', 'skip', 'hit%', 'stop%', 'won%', 'net', 'net H1', 'net H2', 'longs hit/stop/net', 'shorts hit/stop/net'))
for v, x in res.items():
    t = pd.DataFrame(x)
    k = t[t.lots > 0]
    s = {'taken': len(k), 'skipped': int((t.lots == 0).sum()), 'hit': 100 * (k.status == 'target').mean(), 'stop': 100 * (k.status == 'stopped').mean(), 'won': 100 * (k.net > 0).mean(),
         'net': k.net.sum(), 'h1': k[k.half == 'H1'].net.sum(), 'h2': k[k.half == 'H2'].net.sum(), 'stop_atr': k.stop_atr.median(), 'risk_pct': k.risk_pct.median(), 'lots': k.lots.mean()}
    lo, sh = k[k.side == 'LONG'], k[k.side == 'SHORT']
    out[v] = s
    print('%-34s %5d %5d %6.1f %6.1f %6.1f %+9.0f %+9.0f %+9.0f | %2.0f / %2.0f / %+8.0f | %2.0f / %2.0f / %+8.0f | median stop %.2f ATR = %.2f%%, lots %.2f' % (
        v, s['taken'], s['skipped'], s['hit'], s['stop'], s['won'], s['net'], s['h1'], s['h2'], 100 * (lo.status == 'target').mean(), 100 * (lo.status == 'stopped').mean(), lo.net.sum(),
        100 * (sh.status == 'target').mean(), 100 * (sh.status == 'stopped').mean(), sh.net.sum(), s['stop_atr'], s['risk_pct'], s['lots']))
b = pd.DataFrame(res['as now (stop 0.3-0.9 ATR, aim 0.5)'])
cm = pd.crosstab(b.true, b.status.map({'target': 'hit', 'stopped': 'stop', 'close': 'close'}))
print('\ncash replay "as now" against the real-futures outcome of the same trades:'); print(cm.to_string())
st = b[b.status == 'stopped']
print('\nwhen the stop-outs happen (as now): within 5 min %.0f%%, 5-15 min %.0f%%, 15-60 min %.0f%%, later %.0f%% | stopped trades by stop distance: <0.4 ATR %d, 0.4-0.5 %d, 0.5-0.6 %d, 0.6+ %d' % (
    100 * (st.mins <= 5).mean(), 100 * ((st.mins > 5) & (st.mins <= 15)).mean(), 100 * ((st.mins > 15) & (st.mins <= 60)).mean(), 100 * (st.mins > 60).mean(),
    (st.stop_atr < 0.4).sum(), ((st.stop_atr >= 0.4) & (st.stop_atr < 0.5)).sum(), ((st.stop_atr >= 0.5) & (st.stop_atr < 0.6)).sum(), (st.stop_atr >= 0.6).sum()))
print('all trades by stop distance (as now): <0.4 ATR %d, 0.4-0.5 %d, 0.5-0.6 %d, 0.6+ %d' % ((b.stop_atr < 0.4).sum(), ((b.stop_atr >= 0.4) & (b.stop_atr < 0.5)).sum(), ((b.stop_atr >= 0.5) & (b.stop_atr < 0.6)).sum(), (b.stop_atr >= 0.6).sum()))
json.dump(out, open(SP + '/v2/f5.json', 'w'))
pickle.dump(res, open(SP + '/v2/f5_res.pkl', 'wb'))
