# MEDHAALPHA research backtester

Backtest of the *MEDHAALPHA — EMA 20/50 Adaptive Trend Trading Algorithm* blueprint (v1.0,
16 Nov 2026) on NSE single-stock F&O names, 18 Nov 2024 – 13 Nov 2026, for a ₹3,00,000 account.

## Pipeline

```bash
pip install -r requirements.txt -r requirements-research.txt
python -m medhaalpha.data.bhavcopy --start 2024-09-01 --end 2026-11-13       # NSE F&O + cash bhavcopies
python -c "import pandas as pd; f=pd.read_parquet('data/medhaalpha/bhav/futures_all.parquet'); \
s=sorted(f[f.date>='2024-11-01'].symbol.unique())+['NIFTY50','NIFTYBANK']; \
open('data/medhaalpha/universe_symbols.txt','w').write('\n'.join(s))"   # every stock with F&O in the window
python -m medhaalpha.data.upstox --symbols-file data/medhaalpha/universe_symbols.txt \
       --intervals days,minutes5,minutes3 --start 2024-09-01 --daily-start 2023-01-01 --end 2026-11-13
python -m medhaalpha.data.earnings                                           # results dates (earnings blackout)
python -m medhaalpha.run_study --stage all                                   # stages 1-5
python -m medhaalpha.report                                                  # HTML report
```

## Modules

| Module | Role |
|---|---|
| `data/bhavcopy.py` | NSE UDiFF F&O and cash bhavcopies: point-in-time F&O list, lot sizes, option chains, traded value |
| `data/upstox.py` | Upstox V3 public historical candles (daily, 5-min, 3-min; corporate-action adjusted) |
| `data/loader.py` | session filtering, 15/60-min resampling anchored at 09:15, point-in-time universe |
| `indicators.py` | EMA, Wilder ATR/ADX, session VWAP, same-slot relative volume (numba) |
| `features.py` | 100-point trend score (25/20/20/15/10/10), regimes, leak-free HTF and daily-context joins, sector RS |
| `signals.py` | Strategy A0 (raw crossover), A (filtered crossover), B (pullback), C (breakout), regime-adaptive |
| `simulate.py` | bar-by-bar simulator on 3/5-min base bars: gaps, stop/target precedence, trails, EMA exits, partials |
| `costs.py` | date-aware Indian cost model (see `docs/medhaalpha/COST_ASSUMPTIONS.md`) |
| `portfolio.py` | account rules: ₹3k risk, ₹6k daily / ₹12k weekly limits, ₹6k open risk, ₹75k per stock, sector exposure |
| `options.py` | contract selection from real bhavcopy chains, IV repricing, debit spreads, strict max-loss sizing |
| `experiments.py` | experiment grids, development/holdout windows, walk-forward selection |
| `run_study.py` | stages 1–5 |

## Conventions that matter

* Every feature is evaluated on a *completed* bar; orders become active on the next bar. Higher
  timeframe and daily values are joined by bar end time (`merge_asof` backward), and the daily
  context for a session is the previous session's candle.
* Universe on day D: in the F&O bhavcopy of D-1, 20-day average traded value ≥ ₹20 crore, ≥ 200
  daily sessions of history.
* Development window 18 Nov 2024 – 15 May 2026 (walk-forward 6-month train / 3-month test inside it);
  holdout 18 May – 13 Nov 2026 is only evaluated after all selections are frozen.
