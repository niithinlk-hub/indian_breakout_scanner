import sys, pickle
SP='/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP+'/hunt'); import harness as H
import pandas as pd
D = H.load_all()
n = pickle.load(open('nifty_min.pkl','rb'))
ndays = set(n.index.strftime('%Y-%m-%d'))
for k,d in D.items():
    print(k, d[['day','time','o_entry_ts']].head(3).values.tolist())
    print('  time range', d.time.min(), d.time.max(), 'days missing in nifty', sorted(set(d.day)-ndays))
    print('  nifty_chg sample', d[['day','time','nifty_chg']].head(2).values.tolist())
