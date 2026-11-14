# Does the patched scanner's medhasuryan reproduce the research's Switch-1? Six-month stored signals, the app's own code.
import json, sys
import pandas as pd
work, SP = sys.argv[1], sys.argv[2]
sys.path.insert(0, work + '/scanner')
from scanner.equity.backtest import unpack_signal_days, MODELS
from scanner.equity.config import EqConfig
from scanner.equity.features import nifty_regime
from scanner.equity.score import min_score
cfg = EqConfig()
doc = json.load(open(work + '/scanner/scanner/equity/reports/backtest6m_signals.json'))
days = unpack_signal_days(doc)
app = {}
pol_of = {}
for d in days:
    pool = [s for s in d['signals'] if s['setup'] in ('A', 'B') and s['fut']['T1']['status'] != 'no_data']
    thr = min_score(cfg, 'medhasuryan')
    live = []
    for s in sorted(pool, key=lambda s: (s['time'], -s['scores']['medhasuryan'], s['symbol'])):
        if s['scores']['medhasuryan'] >= thr and len(live) < cfg.top_n:
            live.append(s)
    for s in live:
        app[(d['day'], s['time'], s['symbol'], s['setup'])] = s
        pol_of[(d['day'], s['time'], s['symbol'], s['setup'])] = 'T1' if d.get('nifty_regime') == 'Downtrend' else 'T3'
sys.path.insert(0, SP + '/hunt')
import harness as H
R = H.load_all()['real']
t = H.switch1(R)
res = {(r.day, r.time, r.symbol, r.setup) for r in t.itertuples()}
print('app medhasuryan picks %d, research Switch-1 picks %d, same %d, only app %d, only research %d' % (
    len(app), len(res), len(set(app) & res), len(set(app) - res), len(res - set(app))))
PI = {p: i for i, p in enumerate(doc['policies'])}
fut = sum(app[k]['fut'][pol_of[k]]['net_rs'] for k in app)
print('app futures net with T3 / T1-on-downtrend exits: %+.0f  (research Switch-1: +8,11,393)' % fut)
reg = H.regime()
mism = [d['day'] for d in days if d.get('nifty_regime') != reg.loc[d['day'], 'A']]
print('trend labels: app vs research differ on %d of %d days %s' % (len(mism), len(days), mism[:5]))
