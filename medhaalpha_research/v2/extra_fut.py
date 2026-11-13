import gzip, json, sys, time, urllib.parse, urllib.request
import pandas as pd
from scanner.series import candles_to_df, merge_frames
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import run_policies
from scanner.equity.universe_upstox import parse
sp = sys.argv[1]
cfg = EqConfig()
day, sym, setup, tm = '2026-10-28', 'RELIANCE', 'B', '13:21'
j = json.load(open(sp + '/replay_oct/replay_%s.json' % day))
s = next(x for x in j['signals'] if x['symbol'] == sym and x['setup'] == setup and x['time'] == tm)
uni = parse(json.loads(gzip.decompress(open(sp + '/test/NSE.json.gz', 'rb').read())))
fut = uni.pick_future(sym, pd.Timestamp(day).date(), cfg.roll_sessions)
assert fut.trading_symbol == s['fut_symbol']


def get(url):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'curl/8'})
    return json.load(urllib.request.urlopen(req, timeout=40))['data']['candles']


k = urllib.parse.quote(fut.key, safe='')
m = regular(merge_frames(candles_to_df(get('https://api.upstox.com/v3/historical-candle/%s/minutes/1/2026-11-12/%s' % (k, day))),
                         candles_to_df(get('https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/1' % k))), cfg)
ets = pd.Timestamp('%sT%s:00+05:30' % (day, tm)) + pd.Timedelta(minutes=1)
outs = run_policies(m, s['side'], s['stop'], [s['t1'], s['t2'], s['t3']], ets, close_at_eod=False, trail=True)
assert abs(outs['T1'].entry - s['fut']['T1']['entry']) < 1e-6
full = sorted(d for d, n in m.groupby(m.index.date).size().items() if n >= cfg.min_session_candles)
qty = s['lot'] * s['lots']
res = {}
for pol, o in outs.items():
    net = round(o.points * qty - C.round_trip('FUT', o.entry, o.exit, qty, s['side'], cfg.brokerage_per_order, cfg.brokerage_pct) - C.slippage(o.entry, o.exit, qty, cfg.slippage_pct), 2)
    xd = pd.Timestamp(o.exit_ts).date()
    res[pol] = {'status': o.status, 'entry': o.entry, 'exit': o.exit, 'exit_ts': o.exit_ts, 'reason': o.reason, 'r': o.r, 'net_rs': net,
                'sessions': sum(1 for d in full if ets.date() < d <= xd) + (1 if xd not in full and xd > ets.date() else 0)}
row = {'day': day, 'time': tm, 'symbol': sym, 'setup': setup, 'side': s['side'], 'qty': qty, 'lot': s['lot'], 'lots': s['lots'], 'models': ['split'], 'scores': s['scores'],
       'basis': 'futures', 'stop': s['stop'], 't1': s['t1'], 't2': s['t2'], 't3': s['t3'], 'entry_ts': ets.isoformat(), 'res': res}
json.dump({'rows': [row]}, open(sp + '/v2/hold_extra_fut.json', 'w'))
print(sym, {p: (r['status'], r['net_rs'], r['sessions']) for p, r in res.items() if p in ('T1', 'T2', 'T3')})
