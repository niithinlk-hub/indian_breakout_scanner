import pickle, numpy as np, pandas as pd
n = pickle.load(open('nifty_min.pkl','rb'))
n = n.copy(); n['day']=n.index.strftime('%Y-%m-%d'); n['hm']=n.index.strftime('%H:%M')
g = n.groupby('day')
c = g.size()
print(c.describe()); print(c[c<370])
print('first bars', g.hm.first().value_counts().head()); print('last bars', g.hm.last().value_counts().head())
print('out of session', ((n.hm<'09:15')|(n.hm>'15:29')).sum())
# flat-bar fraction per day
flat = g.apply(lambda x: (x.close.diff()==0).mean())
print(flat.sort_values().tail(15))
print(n.index.is_monotonic_increasing, n.index.duplicated().sum())
