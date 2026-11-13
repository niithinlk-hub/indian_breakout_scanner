import numpy as np, pandas as pd


def live_df(df, col, thr, n=6):
    """Live rule on a frame: per day, time order (ties: higher score, symbol), first n with score >= thr. Returns index labels."""
    keep = []
    d = df.assign(_s=df[col]).sort_values(['day', 'time', '_s', 'symbol'], ascending=[True, True, False, True])
    for day, g in d.groupby('day', sort=True):
        q = g[g['_s'] >= thr]
        keep.extend(q.index[:n])
    return keep


def thr_for(df, col, target, n=6):
    """Lowest threshold whose live selection has at most `target` trades (searched over the score's own values)."""
    vals = np.unique(np.round(df[col].dropna().to_numpy(), 4))
    lo, hi = 0, len(vals) - 1
    while lo < hi:                       # count is non-increasing in thr (not strictly guaranteed with the cap, close enough)
        mid = (lo + hi) // 2
        if len(live_df(df, col, vals[mid], n)) <= target:
            hi = mid
        else:
            lo = mid + 1
    return float(vals[lo])


def stat(df, idx):
    t = df.loc[idx]
    n = len(t)
    if n == 0:
        return {'n': 0, 'hit%': 0, 'stop%': 0, 'won%': 0, 'T1': 0, 'per': 0, 'T2': 0, 'T3': 0, 'R': 0, 'longs': 0, 'days_up': 0, 'days_dn': 0, 'maxdd': 0}
    byday = t.groupby('day')['net1'].sum()
    eq = byday.cumsum()
    return {'n': n, 'hit%': round(100 * t.hit.mean(), 1), 'stop%': round(100 * t['stop'].mean(), 1), 'won%': round(100 * (t.net1 > 0).mean(), 1),
            'T1': int(round(t.net1.sum())), 'per': int(round(t.net1.mean())), 'T2': int(round(t.net2.sum())), 'T3': int(round(t.net3.sum())),
            'R': round(t.r1.sum(), 1), 'longs': int(t.long.sum()), 'days_up': int((byday > 0).sum()), 'days_dn': int((byday < 0).sum()),
            'maxdd': int(round((eq - eq.cummax().clip(lower=0)).min()))}


def line(name, s):
    return '%-40s n=%3d hit %5.1f%% stop %5.1f%% won %5.1f%% | T1 %+8d (%+5d/trade, R %+6.1f) T2 %+8d T3 %+8d | days +%d/-%d maxDD %+7d longs %d' % (
        name, s['n'], s['hit%'], s['stop%'], s['won%'], s['T1'], s['per'], s['R'], s['T2'], s['T3'], s['days_up'], s['days_dn'], s['maxdd'], s['longs'])


class Prep:
    """Clip to the 1st-99th percentile and standardise, constants taken from the fitting rows only."""
    def __init__(self, X):
        self.lo, self.hi = np.nanpercentile(X, 1, axis=0), np.nanpercentile(X, 99, axis=0)
        Z = np.clip(X, self.lo, self.hi)
        self.mu, self.sd = np.nanmean(Z, axis=0), np.nanstd(Z, axis=0) + 1e-9

    def __call__(self, X):
        Z = (np.clip(X, self.lo, self.hi) - self.mu) / self.sd
        return np.nan_to_num(Z, nan=0.0)


def logit_fit(Z, y, l2=10.0, iters=50):
    """L2-regularised logistic regression by Newton steps; intercept not penalised."""
    A = np.hstack([np.ones((len(Z), 1)), Z])
    w = np.zeros(A.shape[1])
    P = np.eye(A.shape[1]) * l2
    P[0, 0] = 0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-A @ w))
        g = A.T @ (p - y) + P @ w
        H = (A * (p * (1 - p))[:, None]).T @ A + P
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-8:
            break
    return w


def logit_pred(w, Z):
    return 1 / (1 + np.exp(-(np.hstack([np.ones((len(Z), 1)), Z]) @ w)))


def ridge_fit(Z, y, l2=10.0):
    A = np.hstack([np.ones((len(Z), 1)), Z])
    P = np.eye(A.shape[1]) * l2
    P[0, 0] = 0
    return np.linalg.solve(A.T @ A + P, A.T @ y)


def ridge_pred(w, Z):
    return np.hstack([np.ones((len(Z), 1)), Z]) @ w
