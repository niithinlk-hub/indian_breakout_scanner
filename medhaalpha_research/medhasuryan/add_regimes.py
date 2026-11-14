# Adds each stored day's Nifty trend ("nifty_regime", known before the open) to the scanner's two stored backtest files,
# using the scanner's own features.nifty_regime on Nifty 50 daily closes (Upstox NSE_INDEX|Nifty 50, the research data).
import json, sys
import pandas as pd
work, nifty = sys.argv[1], sys.argv[2]
sys.path.insert(0, work + '/scanner')
from scanner.equity.features import nifty_regime
nd = json.load(open(nifty))['data']['candles']
N = pd.DataFrame(nd, columns=['ts', 'open', 'high', 'low', 'close', 'volume', 'oi'])
N.index = pd.to_datetime(N.ts)
N = N.sort_index()
rep = work + '/scanner/scanner/equity/reports/'
for f in ('backtest.json', 'backtest6m_signals.json'):
    doc = json.load(open(rep + f))
    labs = {}
    for d in doc['days']:
        d['nifty_regime'] = nifty_regime(N, pd.Timestamp(d['day']).date())
        labs[d['nifty_regime']] = labs.get(d['nifty_regime'], 0) + 1
    with open(rep + f, 'w', encoding='utf-8') as fh:
        json.dump(doc, fh, separators=(',', ':'), ensure_ascii=False)
    print(f, len(doc['days']), 'days', labs)
