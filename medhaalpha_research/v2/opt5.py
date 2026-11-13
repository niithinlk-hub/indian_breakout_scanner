# Options, 21 Oct - 13 Nov 2026, all five models. Each trade's option (monthly, strike nearest the signal price, CE for a
# long and PE for a short, as the scanner picks it) is priced on its own 1-minute candles: bought at the open of the futures
# entry minute, sold at the open of the first option candle after the futures leg exits (fills.option_leg). Charges and
# 0.25 % slippage a side as the scanner costs them. Done twice: futures leg squared off at the close, and held across days.
import gzip, json, os, sys, time, urllib.parse, urllib.request
os.environ["DATABASE_URL"] = "sqlite:////tmp/claude-0/v2_unused.db"
os.environ["ENGINE_URL"] = "http://127.0.0.1:9"; os.environ["SCANNER_TOKEN"] = ""
import pandas as pd
from scanner.series import candles_to_df, merge_frames
from scanner.equity import costs as C
from scanner.equity.config import EqConfig
from scanner.equity.features import regular
from scanner.equity.fills import Outcome, option_leg
from scanner.equity.universe_upstox import parse

sp = sys.argv[1]
cfg = EqConfig()
H = json.load(open(sp + '/v2/hold4.json'))
rows = H['rows']
uni = parse(json.loads(gzip.decompress(open(sp + '/test/NSE.json.gz', 'rb').read())))
today = pd.Timestamp.now(tz='Asia/Kolkata').date()
y = str((pd.Timestamp(today) - pd.Timedelta(days=1)).date())
snap = {}
import glob
for d in ('replay_oct', 'replay_nov2', 'replay7'):
    for p in glob.glob(sp + '/' + d + '/replay_*.json'):
        j = json.load(open(p))
        for s in j['signals']:
            snap[(j['day'], s['symbol'], s['setup'], s['time'])] = s


def get(url):
    for a in range(4):
        try:
            time.sleep(0.22)
            req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'curl/8'})
            return json.load(urllib.request.urlopen(req, timeout=40))['data']['candles']
        except Exception as e:  # noqa: BLE001
            if getattr(e, 'code', None) == 400 or a == 3:
                raise
            time.sleep(1.5 * (a + 1))


cache = {}


def series(key, d0):
    if key not in cache:
        k = urllib.parse.quote(key, safe='')
        hist = candles_to_df(get('https://api.upstox.com/v3/historical-candle/%s/minutes/1/%s/%s' % (k, y, d0)) if d0 <= y else [])
        live = candles_to_df(get('https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/1' % k))
        cache[key] = regular(merge_frames(hist, live), cfg)
    return cache[key]


def leg(om, status, ets, xts, qty):
    o = Outcome('x', status, ets, 0.0, xts, 0.0, '', 0.0, 0.0)
    L = option_leg(om, o)
    if L.get('status') in (None, 'no_data'):
        return None
    L['rs'] = round((L['exit'] - L['entry']) * qty, 2)
    L['costs'] = C.round_trip('OPT', L['entry'], L['exit'], qty, 'LONG', cfg.brokerage_per_order, cfg.brokerage_pct)
    L['slip_rs'] = C.slippage(L['entry'], L['exit'], qty, cfg.opt_slippage_pct)
    L['net_rs'] = round(L['rs'] - L['costs'] - L['slip_rs'], 2)
    L['outlay'] = round(L['entry'] * qty, 2)
    return L


out, nofind, tie_n, tie_bad = [], 0, 0, 0
for r in rows:
    s = snap[(r['day'], r['symbol'], r['setup'], r['time'])]
    fut = uni.pick_future(r['symbol'], pd.Timestamp(r['day']).date(), cfg.roll_sessions)
    o = uni.pick_option(r['symbol'], fut.expiry, 'CE' if r['side'] == 'LONG' else 'PE', s['snapshot']['price'])
    if o is None:
        nofind += 1
        continue
    if s.get('option'):
        assert o.trading_symbol == s['option']['symbol'], (o.trading_symbol, s['option']['symbol'])
    om = series(o.key, r['day'])
    qty = o.lot_size * r['lots']
    ets = r['entry_ts']
    rec = {'day': r['day'], 'time': r['time'], 'symbol': r['symbol'], 'side': r['side'], 'models': r['models'], 'option': o.trading_symbol, 'strike': o.strike, 'qty': qty, 'lots': r['lots'],
           'entry_ts': ets, 'same': {}, 'held': {}, 'fut_same': {}, 'fut_held': {}}
    for pol in ('T1', 'T3'):
        f = s['fut'][pol]
        a = leg(om[om.index.date == pd.Timestamp(r['day']).date()], f['status'], ets, f['exit_ts'], qty)
        b = leg(om, r['res'][pol]['status'], ets, r['res'][pol]['exit_ts'], qty)
        rec['fut_same'][pol] = {'status': f['status'], 'net_rs': f['net_rs']}
        rec['fut_held'][pol] = {'status': r['res'][pol]['status'], 'net_rs': r['res'][pol]['net_rs'], 'exit_ts': r['res'][pol]['exit_ts'], 'sessions': r['res'][pol]['sessions']}
        if a:
            rec['same'][pol] = {k: a[k] for k in ('status', 'entry', 'exit', 'exit_ts', 'net_rs', 'outlay', 'ret_pct', 'stale_entry_min')}
            st = (s.get('option') or {}).get('legs', {}).get(pol)
            if st and st.get('status') not in (None, 'no_data'):
                tie_n += 1
                tie_bad += abs(st['net_rs'] - a['net_rs']) > 0.01
        if b:
            rec['held'][pol] = {k: b[k] for k in ('status', 'entry', 'exit', 'exit_ts', 'net_rs', 'outlay', 'ret_pct', 'stale_entry_min')}
    out.append(rec)
print('trades', len(rows), '| option found', len(out), '| not found', nofind, '| option series fetched', len(cache))
print('same-day legs checked against the replay\'s own stored option result:', tie_n, '| different:', tie_bad)
print('no same-day price: T1 %d, T3 %d | no held price: T1 %d, T3 %d' % (sum('T1' not in r['same'] for r in out), sum('T3' not in r['same'] for r in out), sum('T1' not in r['held'] for r in out), sum('T3' not in r['held'] for r in out)))
json.dump({'days': H['days'], 'rows': out}, open(sp + '/v2/opt5.json', 'w'))
