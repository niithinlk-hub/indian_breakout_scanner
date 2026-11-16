"""MedhaSuryan-M: the MedhaSuryan score with more weight on momentum.

    MedhaSuryan-M = (1 - w) x MedhaSuryan + w x Momentum

MedhaSuryan is unchanged (Fable-OP, or Opus v3 on Nifty downtrend days). Momentum is a 0-100 score from four parts
known at the signal minute, each a straight-line ramp between round anchor values fixed before any backtest:

  part                                                       points   full        nothing
  relative strength today: stock's day move minus Nifty's      35     2.5 %       0 % or worse
    (both in the trade's direction)
  20-day trend in the trade's direction (20-day return)        25     +10 %       0 % or against
  breakout breadth: prior bars broken (log scale)              20     60 bars     2 bars
  volume so far vs normal for the time of day (rel_vol)        20     2.0x        0.8x or less

A missing input scores that part 0.5 (neutral).
"""
import numpy as np
import pandas as pd

PARTS = {'rs': 35.0, 'trend20': 25.0, 'breadth': 20.0, 'volume': 20.0}


def _ramp(x, lo, hi):
    v = (np.asarray(x, float) - lo) / (hi - lo)
    return np.where(np.isfinite(v), np.clip(v, 0.0, 1.0), 0.5)


def momentum_parts(df: pd.DataFrame) -> pd.DataFrame:
    sg = np.where(df['side'] == 'LONG', 1.0, -1.0)
    rs = df['day_chg'] - sg * df['nifty_chg']                 # day_chg is already direction-adjusted
    trend = sg * df['ret20']                                  # ret20 is raw: flip for shorts
    nb = np.log(np.maximum(df['n_break'].astype(float), 1.0))
    p = pd.DataFrame({'rs': _ramp(rs, 0.0, 2.5),
                      'trend20': _ramp(trend, 0.0, 10.0),
                      'breadth': _ramp(nb, np.log(2.0), np.log(60.0)),
                      'volume': _ramp(df['rel_vol'], 0.8, 2.0)}, index=df.index)
    return p


def momentum_score(df: pd.DataFrame) -> pd.Series:
    p = momentum_parts(df)
    return sum(p[k] * w for k, w in PARTS.items())


def medhasuryan(df: pd.DataFrame) -> pd.Series:
    return pd.Series(np.where(df['regime'] == 'Downtrend', df['s_opus_v3'], df['s_fable_op']), index=df.index)


def medhasuryan_m(df: pd.DataFrame, w: float) -> pd.Series:
    return (1.0 - w) * medhasuryan(df) + w * momentum_score(df)
