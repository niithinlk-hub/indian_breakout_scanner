# NSE breakout scanner (EOD, long-only)

End-of-day scanner for Nifty 500 + Nifty Microcap 250 that looks for momentum leaders
breaking out of tight bases. Every signal will store the gate values that produced it,
and no performance figure is shown anywhere unless it comes from the backtest in this
folder.

## Status

| Step | What | State |
| --- | --- | --- |
| 1 | Data layer + QA | done: [`reports/step1_data_report.md`](reports/step1_data_report.md) |
| 2 | Base-rate study (benchmark a) | done: [`reports/step2_baserate.md`](reports/step2_baserate.md) |
| 3 | Rules engine + tests | waiting for go-ahead after step 2 |
| 4 | Backtest, ablation, walk-forward | not started |
| 5 | Daily scan job + GitHub Actions | not started (needs secrets: ask first) |
| 6 | Dashboard (`/web`) | not started |
| 7 | Meta-labeling | only on explicit go-ahead |

Supabase: schema drafted in `sql/001_schema.sql`, read policies drafted in
`sql/draft/002_rls_policies.sql`. Nothing has been applied and no project has been
created. Until then the local parquet store (`scanner/data/`, git-ignored) holds
everything, with the same tables.

## Layout

```
scanner/
  nsescan/
    config.py        every threshold (DEFAULTS) -> seeds the Supabase `config` table
    universe.py      NSE constituent CSVs, mirror fallback, committed snapshots
    fetch.py         batched yf.download, retry + exponential backoff
    pipeline.py      full-history load, incremental update (re-adjustment detection), benchmarks
    panel.py         session calendar (Yahoo stub handling), wide OHLCV panel
    qa.py            point-in-time data QA -> data_quality
    gates.py         liquidity gate (other gates arrive with step 3)
    regime.py        regime_daily (Nifty 500 vs SMA50, breadth, India VIX percentile)
    simulate.py      section-4 trade plan: one implementation for live, paper and backtest
    metrics.py       expectancy, profit factor, MFE/MAE, month-block bootstrap CIs
    baserate.py      benchmark (a)
    reports.py       step-1 / step-2 markdown reports
    store/           LocalStore (parquet) and SupabaseStore (supabase-py, service key)
  sql/               schema, draft RLS policies
  universe_snapshots/ constituent CSVs as downloaded (reproducible universe)
  reports/           generated reports (committed)
  tests/
```

## Running

```bash
python3.11 -m venv .venv && . .venv/bin/activate
pip install -r scanner/requirements.txt
cd scanner
python -m nsescan universe        # NSE lists -> universe (+ snapshot)
python -m nsescan history         # 10y daily bars for all symbols + benchmarks (~2 min)
python -m nsescan update          # incremental: new bars, revisions, re-adjusted symbols
python -m nsescan qa              # data_quality as of the latest session
python -m nsescan data-report     # reports/step1_data_report.md
python -m nsescan baserate        # reports/step2_baserate.md (+ json)
python -m nsescan config-sql      # SQL seeding the config table with every default
python -m pytest                  # tests
```

Without `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` the commands use the built-in config
defaults and the local store, and say so in the log.

## Rules that hold everywhere

* **No lookahead.** Every value at date T uses bars dated <= T; entries are at the T+1
  open. QA, liquidity and regime are computed as full point-in-time masks, and the live
  scan takes the last row of the same masks the backtest uses
  (`tests/test_point_in_time.py` perturbs bars after T and checks nothing at or before
  T moves).
* **No hardcoded thresholds.** Logic reads `Config`; `DEFAULTS` only seeds the table.
  Each scan run, signal and backtest run records the config hash.
* **One trade plan.** `simulate.py` is used for base rates, backtests and (later)
  paper-trade exits. Where the order of events inside a daily bar is unknowable, it
  assumes the worse outcome (stop before target on the same bar; breakeven stop active
  from the next bar).

## Data findings that shaped the code

* **Yahoo holiday stubs.** On NSE holidays Yahoo emits a bar for nearly every stock
  with volume 0 and open = high = low = close = previous close (2026-01-15, 05-01,
  05-28, 06-26, 09-14). Such dates are not sessions.
* **Yahoo gap sessions.** On real sessions Yahoo sometimes stubs most stocks
  (2025-03-18: 99%; 2024-01-15: 24%) while the index moves. The session is kept and
  the stub bars become missing bars (not zero-volume days). NSE's special Saturday
  session of 2024-01-20 is absent from Yahoo entirely.
* **Unadjusted corporate actions.** Yahoo does not adjust demergers (e.g. Tata
  Motors 2025-10-14, ABFRL 2025-05-22), and several large drops sit on 1 January.
  QA excludes a symbol for 252 sessions after any >25% day (both segments by default).
* **Constituent placeholders.** NSE lists carry `DUMMY*` rows for demerged entities
  awaiting listing; they are dropped.
* **NSE mirrors** answer 403 intermittently; each list is tried on three hosts over
  several rounds, with the last snapshot as a fallback.

## Known gaps (documented, not faked)

* **No delivery %.** Yahoo does not provide it.
* **No price-band / trade-for-trade (T2T) history.** The constituent CSV's `Series`
  (EQ/BE) is stored for today only. The circuit check (step 3) infers limit moves
  from price action.
* **NSE earnings dates from Yahoo are unreliable.** The earnings flag is best effort
  and never excludes a name.
* **Survivorship bias.** The universe is today's constituents; names that left the
  indices or delisted are absent from the backtest. This is worse for MICRO250 (higher
  index churn), so MICRO250 is always reported separately and should be read as
  optimistic.
* **Dividend-adjusted prices.** `auto_adjust=True` scales history for dividends, so
  past closes and traded values are slightly understated against the rupee floors.
* **Nominal rupee liquidity floors.** Applied unchanged across ten years, they admit
  far fewer names in 2017-2020 than today (see the step-1 report, section 7).
* **Costs and slippage** (0.25% round trip; slippage 0.10% N500 / 0.25% MICRO250 per
  side) are assumptions and are labelled as such in every report.
