# Brief: hunt for a better intraday algorithm than Opus v3 and Fable-OP

## THE CLIENT TRADES OPTIONS. Optimise OPTION profit (updated 14 Nov 2026)

For every signal the client buys the at-the-money CALL (long signal) or PUT (short signal) of the stock's monthly contract (next month once 4 or fewer sessions remain to expiry), the SAME number of lots as the futures sizing gives, enters the minute after the signal, and sells at the open of the minute after the FUTURES leg exits under the chosen exit policy (stop / target / trail / 15:29 square-off). No stop on the premium itself.

`harness.py` now reports **modelled option net** by default (`H.METRIC = 'opt'`; columns `opt_<P>`), with futures net alongside. Option prices are Black-76 with an IV fitted from the stock's ATR and intraday time decay fitted on 1,960 real option exits the scanner recorded 21 Oct-13 Nov 2026 (correlation 0.97 per trade with the real option result; every exit policy's total within 1-7 %). `H.option_net(df, pol, strike_pct=…, expiry='std'|'next', lots_mult=…, qty=…, iv_mult=…, decay=…)` reprices any variant: in/out of the money strikes, next-month expiry, different lot counts. Option figures are estimates good to roughly +-10 %; there is no volatility skew and no day-by-day real IV.

**Option baselines (modelled option net Rs)**

| Set | Opus v3 (exit T1) | Fable-OP (exit T3) | Switch-1 |
|---|---|---|---|
| real, 12 May-11 Nov 2026 | +4,23,981 (worst day -18,863, max DD -36,768) | +5,45,031 (-26,335, -37,024) | +5,82,910 |
| real 1st half / 2nd half | +2,39,288 / +1,84,693 | +3,47,343 / +1,97,688 | +3,39,868 / +2,43,042 |
| unseen, 3 Nov 2025-11 May 2026 | +84,362 (-25,651, -63,667) | +2,02,948 (-16,461, -48,875) | +2,67,606 |
| known, 12 May-19 Oct 2026 | +1,99,051 | +1,83,848 | +1,84,194 |

**The bar is now on OPTION net**: beat both Opus v3 (T1) and Fable-OP (T3) on option net on BOTH `unseen` and `real` 2nd half, worst day and max drawdown (option) no worse than 1.25x the better baseline. Futures figures are secondary. Option-specific levers are fair game: which exit policy suits a bought option (theta vs letting winners run), strike (ITM/ATM/OTM), expiry month, avoiding the last days before expiry, time of day, lot count for the same Rs 15,000 risk now that a bought option loses far less than the future at the stop, and selection rules that prefer moves big and fast enough to beat time decay. A different lot count changes capital and risk: report premium outlay per trade (`option_net(..., detail=True)`) when you change it.

(The futures-based sections below still describe the system and the futures baselines.)

`SP` below = `/tmp/claude-0/-home-user-indian-breakout-scanner/f54e4084-33bd-532c-b38a-bd64a5b4292e/scratchpad`.
Python: `$SP/venv/bin/python` (numpy, pandas, scipy, scikit-learn, lightgbm, statsmodels installed). 4 CPUs, 15 GB RAM shared with one other agent: load the minute data at most once per process, never in parallel loops.

## The system being improved

An intraday scanner for NSE (India) single-stock futures, about 200 F&O stocks. It scans one-minute candles 09:17-14:15 IST and emits signals of two setups:
- **A, Trend breakout (LONG)**: price above its 20-day average, daily RSI(14) 50-65, up >= 0.6 % on the day, above the previous day's high and VWAP, in the top 30 % of today's range, breaking at least 2 prior bars.
- **B, Breakdown (SHORT)**: Nifty down >= 0.25 % on the day, stock below its 20-day average, RSI < 50, down >= 0.9 %, below the previous day's low and VWAP, in the bottom 10 % of today's range, breaking at least 5 prior bars.

Each signal gets a structural stop (a nearby support/resistance level, kept between 0.3 and 0.9 daily ATR from entry; else 0.5 ATR) and targets T1/T2/T3 = 1.0R / 1.9R / 2.6R. Entry is the open of the next minute. Position size: whole futures lots so that the loss at the stop (points + charges + 0.02 % slippage each side) is at most Rs 15,000. Positions still open at 15:29 are squared off.

**Live rule**: each day, in time order, trade the first 6 signals whose score is at least the model's threshold (75).

Score models (0-100) already built:
- **Opus**: move from the open, distance beyond VWAP, small opening gap, RSI room, stop at a real level.
- **Fable-OP**: move today in daily ATRs (30), closed a little off the day's extreme (20), the day's extreme made within the last few minutes (20), early in the session (15), stock moving without the index (15). Built on 12 May-31 Aug 2026.
- **Opus v2**: longs scored by Fable-OP, shorts by Opus.
- **Opus v3**: Opus v2, but a long with rel_vol < 1 scores 0. Built looking at 12 May-11 Nov 2026.

## Futures baselines (Rs, futures, after all costs; for reference, the bar is on OPTION net above)

| Set | Opus v3 (exit T1) | Fable-OP (exit T3) | Switch-1 |
|---|---|---|---|
| real, 12 May-11 Nov 2026, real futures | +5,89,038 (335 trades, worst day -41,636, max DD -98,136) | +7,02,290 (233, -56,275, -80,919) | +8,11,393 |
| real 1st half (12 May-31 Aug) / 2nd half (1 Sep-11 Nov) | +3,08,996 / +2,80,042 | +4,33,707 / +2,68,584 | +4,20,965 / +3,90,428 |
| unseen, 3 Nov 2025-11 May 2026, cash stand-in | -1,28,597 (366, -57,143, -2,65,310) | +78,849 (232, -36,437, -1,38,938) | +1,78,272 |
| known, 12 May-19 Oct 2026, cash stand-in | +1,52,729 | +42,654 | +69,567 |

Switch-1 = Fable-OP exiting at T3, except on downtrend days (Nifty's previous close below its 20-day average and that below its 50-day average) where Opus v3 exiting at T1 is used. It was chosen after seeing the data.

## Already tried (do not resubmit unchanged)

rel_vol gate on longs (that is v3); side split (v2); every Fable-OP part; regime switch by Nifty 20/50-day averages and by 20-day change; a wider stop floor (0.4-0.7 ATR); T1 at 0.7-0.8R; stop to breakeven after 0.4-0.8R; per-month gates picked from 22 features; L2 logistic fits on ~20 snapshot features to predict reaching T1. Trailing-stop exits T2_TR / T3_TR / CLOSE_TR and CLOSE exist as columns but have not been compared systematically against the baselines. A plain grid of exit policy x strike (-1/0/+1/+2 % in the money) x expiry (std/next) on the two baselines' OWN picks is being run separately by the lead analyst: do not spend a test slot on only that grid (combining one of those levers with a new selection rule is fine).

## Test bench: `$SP/hunt/harness.py` (read it, do not edit it)

```python
import sys; sys.path.insert(0, SP + '/hunt'); import harness as H
D = H.load_all()            # {'real','unseen','known'}: one row per A/B signal, features + result of every exit policy
H.compare(D, {'my rule': ('my_score_col', 75, 'T3', 6)})   # prints candidate next to the baselines on all sets + halves
res = H.evaluate(D, {...})  # same as a dict
```
A candidate spec is `(score_column_or_Series, threshold, exit_policy, max_trades_per_day)`, or a function `df -> trades` (rows of df, with a `pol` column naming each row's exit policy). Exit policies available per row: `T1, T2, T3, CLOSE, T2_TR, T3_TR, CLOSE_TR` (columns `net_<P>` in Rs and `r_<P>` in R). Features per row are listed at the top of harness.py (`COMMON` are in every set; `REAL_ONLY` only in `real`). `H.regime()` gives a per-day Nifty trend label (column `A`) known before the open; its `chg` column is that day's move = hindsight, never use it to decide.

New entry signals (not just re-ranking the scanner's): `mins, daily, nifty, lot = H.minute_data()` gives cash one-minute candles 15 Oct 2025-12 Nov 2026 for 218 F&O stocks, daily candles from Jan 2024, Nifty index minutes, and lot size/tick per symbol. Price trades with the scanner's own code (`sys.path.insert(0, SP + '/v2/patched')`; `scanner.equity.fills.simulate/run_policies`, `scanner.equity.scan.lots_for`, `scanner.equity.costs.round_trip` + `costs.slippage(…, 0.02)`, `scanner.equity.config.EqConfig()`), same Rs 15,000 risk sizing, max 6 trades a day, entry at the next minute's open. Compare a new generator against the baselines on the cash stand-in sets (`unseen`, `known`), since it runs on cash candles.

## Rules for a fair test (anti-overfitting)

1. **Design window = `real` 12 May-31 Aug 2026 only.** Any parameter choice, threshold or model fit uses only those rows. Declare at most 4 settings in advance and pick on the design window.
2. **What counts:** `unseen` (3 Nov 2025-11 May 2026, no model was built on it) and `real` 2nd half (1 Sep-11 Nov 2026). Report every set and half anyway.
3. Machine-learning models: train on the design window only (or walk-forward with training strictly earlier than the test day inside one set). Never train on rows you then report as test, never use outcome columns (`net_*`, `r_*`, `status_*`) as features.
4. **No look-ahead:** only information known at the signal minute. Daily candles only up to the previous day. Today's Nifty move after the signal minute is hindsight.
5. Keep the live constraints: max 6 trades a day, the scanner's costs, lots from the Rs 15,000 futures-risk sizing (a test of a different option lot count is allowed but must be reported separately, with premium outlay and worst day).
6. **Bar for "better":** beats BOTH Opus v3 (T1) and Fable-OP (T3) on OPTION net on BOTH `unseen` and `real` 2nd half, with option worst day and max drawdown no worse than 1.25x the better baseline. Also report against Switch-1 and show futures net for reference.

## Safety

Work only in your own folder `$SP/hunt/<your id>/`. Do not edit harness.py, sets.pkl, BRIEF.md or anything outside your folder. Do not read `.env` files, `compose_*.yml`, `argv_*.txt` or `params.json`. Do not use Hostinger, Railway, GitHub, Gmail, Vercel or Supabase tools, and do not contact any broker or trading API: this is offline research on cached data, plus web reading.
