import sys, pickle, numpy as np
SP='/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP+'/hunt'); import harness as H
import pandas as pd
D = H.load_all()
n = pickle.load(open('nifty_min.pkl','rb'))
n['day']=n.index.strftime('%Y-%m-%d'); n['hm']=n.index.strftime('%H:%M')
for k,d in D.items():
    print(k, 'muhurat rows', d.day.isin(['2025-10-21','2026-11-08']).sum())
# nifty_chg check: nifty close at signal minute vs prev session close
days = sorted(n.day.unique())
last = n.groupby('day').close.last()
x = D['unseen'].drop_duplicates(['day','time']).sample(8, random_state=1)
for _,r in x.iterrows():
    i = days.index(r.day); pc = last[days[i-1]] if days[i-1] not in ('2025-10-21','2026-11-08') else last[days[i-2]]
    c = n[(n.day==r.day)&(n.hm==r.time)].close.iloc[0]
    tm1 = (pd.Timestamp('2000-01-01 '+r.time)-pd.Timedelta(minutes=1)).strftime('%H:%M')
    cm1 = n[(n.day==r.day)&(n.hm==tm1)].close.iloc[0]
    print(r.day, r.time, r.nifty_chg, round((c/pc-1)*100,4), 'prev-bar', round((cm1/pc-1)*100,4))
