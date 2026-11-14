import sys, pickle
SP='/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad'
sys.path.insert(0, SP+'/hunt'); import harness as H
import pandas as pd
D = H.load_all()
for k,d in D.items():
    print(k, d.shape, d[['day','time']].head(3).values.tolist(), d.time.dtype)
mins, daily, nifty, lot = H.minute_data()
print(type(nifty), nifty.shape)
print(nifty.head()); print(nifty.tail()); print(nifty.index.dtype)
pickle.dump(nifty, open('nifty_min.pkl','wb'))
