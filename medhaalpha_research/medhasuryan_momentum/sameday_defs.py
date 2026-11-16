# The four MedhaSuryan-M settings, declared before any outcome was looked at, and the trade rule they share.
import numpy as np
import harness as H
import momscore as M

# Cutoffs for S1-S3 give the same number of design-window (12 May-31 Aug 2026) trades as MedhaSuryan at 75 (160),
# found from the scores alone; S4 keeps MedhaSuryan's 75.
SETTINGS = {'S1 w=0.20 cut 72.5': (0.20, 72.5), 'S2 w=0.30 cut 72': (0.30, 72.0), 'S3 w=0.40 cut 71': (0.40, 71.0),
            'S4 w=0.30 cut 75': (0.30, 75.0)}


def make(w, cut):
    """First 6 signals a day with MedhaSuryan-M >= cut; exit T3, or T1 on Nifty downtrend days (as MedhaSuryan)."""
    def f(df):
        t = H.pick(df, M.medhasuryan_m(df, w), cut, 6)
        return t.assign(pol=np.where(t.regime == 'Downtrend', 'T1', 'T3'))
    return f
