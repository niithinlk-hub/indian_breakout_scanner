import math
import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

IST = 'Asia/Kolkata'


def price(F, K, T, s, kind):
    if T <= 0 or s <= 0:
        return max(0.0, F - K) if kind == 'CE' else max(0.0, K - F)
    v = s * math.sqrt(T)
    d1 = (math.log(F / K) + 0.5 * v * v) / v
    d2 = d1 - v
    return F * norm.cdf(d1) - K * norm.cdf(d2) if kind == 'CE' else K * norm.cdf(-d2) - F * norm.cdf(-d1)


def iv(P, F, K, T, kind):
    intr = max(0.0, F - K) if kind == 'CE' else max(0.0, K - F)
    if P <= intr + 1e-6 or T <= 0:
        return np.nan
    try:
        return brentq(lambda s: price(F, K, T, s, kind) - P, 1e-3, 5.0)
    except ValueError:
        return np.nan


def years(ts, expiry, mode='cal', sessions=None):
    """Time to expiry (expiry day 15:30 IST). mode 'cal': calendar time / 365. mode 'trd': trading minutes left / (252 * 375),
    sessions = sorted list of session dates (strings) used to count whole sessions in between (weekdays if None)."""
    t = pd.Timestamp(ts)
    if t.tzinfo is None:
        t = t.tz_localize(IST)
    e = pd.Timestamp(expiry + ' 15:30').tz_localize(IST)
    if mode == 'cal':
        return max((e - t).total_seconds(), 0) / (365.0 * 86400)
    day = t.strftime('%Y-%m-%d')
    left_today = max(0.0, (pd.Timestamp(day + ' 15:30').tz_localize(IST) - t).total_seconds() / 60.0)
    if day >= expiry:
        return left_today / (252 * 375)
    d = pd.bdate_range(pd.Timestamp(day) + pd.Timedelta(days=1), pd.Timestamp(expiry))
    n = len(d) if sessions is None else sum(1 for x in d if x.strftime('%Y-%m-%d') in sessions or x.strftime('%Y-%m-%d') > sessions[-1])
    return (left_today + 375.0 * n) / (252 * 375)
