import sys, numpy as np, pandas as pd
from b76 import price, iv, years
df = pd.read_pickle('legs.pkl')
for mode in ('cal', 'trd'):
    d = df.copy()
    d['T0'] = [years(a, e, mode) for a, e in zip(d.o_entry_ts, d.expiry)]
    d['T1'] = [years(a, e, mode) for a, e in zip(d.o_exit_ts, d.expiry)]
    d['iv0'] = [iv(p, F, K, T, k) for p, F, K, T, k in zip(d.o_entry, d.f_entry, d.strike, d.T0, d.kind)]
    d['pred_exit'] = [price(F, K, T, s, k) for F, K, T, s, k in zip(d.f_exit, d.strike, d.T1, d.iv0, d.kind)]
    ok = d.iv0.notna() & (d.stale.fillna(0) <= 5)
    e = (d.pred_exit - d.o_exit)[ok]
    qty = (d.lot * d.lots)[ok]
    print(mode, 'legs ok', ok.sum(), '/', len(d), '| IV median %.3f' % d.iv0[ok].median(),
          '| exit premium error: median %.2f%%, mean %.2f%% of entry premium' % (100 * (e / d.o_entry[ok]).median(), 100 * (e / d.o_entry[ok]).mean()),
          '| Rs error sum %+.0f vs real gross %+.0f' % ((e * qty).sum(), ((d.o_exit - d.o_entry)[ok] * qty).sum()))
    if mode == 'cal':
        d.to_pickle('legs_iv.pkl')
        x = d[ok & (d.pol == 'T1')].drop_duplicates(['day', 'time', 'symbol'])
        x = x.assign(rv=x.atr_pct * np.sqrt(252) / 100 / 1.25)  # ATR% to an annual vol (ATR ~ 1.25 x mean abs move ~ sd)
        b = np.polyfit(np.log(x.rv), np.log(x.iv0), 1)
        pr = np.exp(np.polyval(b, np.log(x.rv)))
        print('  log IV = %.3f + %.3f log(rv) ; R2 %.2f ; median IV/rv %.2f ; median abs err of fitted IV %.1f%%' % (b[1], b[0], 1 - np.var(np.log(x.iv0) - np.log(pr)) / np.var(np.log(x.iv0)), (x.iv0 / x.rv).median(), 100 * np.median(abs(pr / x.iv0 - 1))))
        np.save('ivfit.npy', b)
        print('  IV by kind:', x.groupby('kind').iv0.median().round(3).to_dict(), '| IV/rv by kind:', (x.iv0 / x.rv).groupby(x.kind).median().round(2).to_dict())
