import pickle, sys
import numpy as np
import pandas as pd
from base import SP, PI, DESIGN, UNSEEN


def load():
    rows = pickle.load(open(SP + '/v2/data/feat.pkl', 'rb'))
    recs = []
    for r in rows:
        d = {'day': r['day'], 'time': r['time'], 'symbol': r['symbol'], 'setup': r['setup'], 'side': r['side'], 'out': r['out'],
             'r1': r['r'][PI['T1']], 'net1': r['net'][PI['T1']], 'net2': r['net'][PI['T2']], 'net3': r['net'][PI['T3']], 'netc': r['net'][PI['CLOSE']],
             'rc': r['r'][PI['CLOSE']]}
        for m in ('opus', 'fable', 'fable_op'):
            d['t_' + m] = r['true'][m]
            d['c_' + m] = r['cash'][m]
            for k, v in r['cash_parts'][m].items():
                d['p_%s_%s' % (m, k)] = v
        for k, v in r['f'].items():
            if k not in ('prev_day', 'price_basis', 'stop_at'):
                d[k] = v
        d['stop_at'] = r['f'].get('stop_at')
        recs.append(d)
    df = pd.DataFrame(recs)
    df['hit'] = (df['out'] == 'hit').astype(int)
    df['stop'] = (df['out'] == 'stop').astype(int)
    df['long'] = (df['side'] == 'LONG').astype(int)
    df['month'] = df['day'].str[:7]
    df['design'] = (df['day'] >= DESIGN[0]) & (df['day'] <= DESIGN[1])
    df['unseen'] = (df['day'] >= UNSEEN[0]) & (df['day'] <= UNSEEN[1])
    df['move_atr'] = df['day_chg'] / df['atr_pct']
    df['open_atr'] = df['from_open'] / df['atr_pct']
    df['vwap_atr'] = df['beyond_vwap'] / df['atr_pct']
    df['gap_atr'] = df['gap'] / df['atr_pct']
    df['rsi_room'] = np.where(df['long'] == 1, 70 - df['rsi14'], df['rsi14'] - 30)
    df['ext52'] = np.where(df['long'] == 1, df['from_52w_high'], -df['from_52w_low'])     # 0 = at the 52-week extreme, negative = away
    df['vs20_dir'] = np.where(df['long'] == 1, df['vs20'], -df['vs20'])
    df['ret5_dir'] = np.where(df['long'] == 1, df['ret5'], -df['ret5'])
    df['ret20_dir'] = np.where(df['long'] == 1, df['ret20'], -df['ret20'])
    df['log_open_min'] = np.log(df['minutes_since_open'].clip(lower=1))
    df['log_stale'] = np.log1p(df['mins_since_extreme'].clip(lower=0))
    df['risk_atr'] = df['risk_pct'] / df['atr_pct']
    return df
