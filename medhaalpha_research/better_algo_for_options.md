# Is there a better algorithm than Opus v3 or Fable-OP for options?

14 Nov 2026. Offline research on cached data only. Nothing here touched the live scanner.

## Short answer

**No.** I searched the internet for intraday methods and found 36 candidates. Six were tested on option profit, and none beat both current models in both test periods. Two independent checks confirmed every result.

What the work does show:

1. **For options, Fable-OP exiting at T3, or Switch-1, is still the best choice.** Switch-1 uses Fable-OP at T3 except on downtrend days, when it uses Opus v3 at T1.
2. **If you trade options with Opus v3, do not exit at T1.** Holding to T3, or to the 15:29 square-off, made more money in every period tested. This improves Opus v3, but it does not make it better than Fable-OP or Switch-1.
3. **The trailing-stop lead from my last update did not hold up.** Opus v3 with a trailing stop to the close comes out level with Switch-1, not ahead of it.

## How option profit is worked out

For every signal, the scanner buys the at-the-money call (long signal) or put (short signal) of the stock's monthly contract. It rolls to the next month when 4 or fewer sessions are left to expiry. It buys the same number of lots as the futures sizing gives. It sells at the open of the minute after the futures trade exits, and there is no stop on the premium itself.

- **No option price history.** Option prices for the past are modelled with Black-76. The volatility comes from each stock's ATR, and the time decay was fitted on 1,960 real option exits the scanner recorded between 21 Oct and 13 Nov 2026.
- **Checked against real trades.** The model's result per trade had a correlation of 0.97 with the real option result. Every exit policy's total came within 1-7% of the real total.
- **Costs.** STT, exchange, stamp, SEBI and GST charges, Rs 20 brokerage an order, and 0.25% slippage each way.
- **Accuracy.** Treat every option figure as good to about ±10%.

## Rules for a fair test

- **Choosing settings:** each method could declare up to 4 settings in advance. The setting was chosen on 12 May-31 Aug 2026 only.
- **Periods that count:** 3 Nov 2025-11 May 2026 (a period no model was built on) and 1 Sep-11 Nov 2026.
- **Bar to pass:** beat both Opus v3 (T1) and Fable-OP (T3) on option profit in both periods. The worst day and the largest drawdown could be no more than 1.25 times the better model's.
- **Live rules kept:** first 6 signals a day scoring 75 or more, Rs 15,000 risk sizing, and the scanner's costs.
- **Checks:** each result was re-run, and recomputed by a second, independent script. Each was also checked for look-ahead and data leaks.

## The six internet methods tested

Option profit in rupees, after all costs.

| Method and source | What it does | 3 Nov 2025-11 May 2026 | 1 Sep-11 Nov 2026 | Result |
|---|---|---|---|---|
| **Current: Opus v3, exit T1** | | +84,362 | +1,84,693 | |
| **Current: Fable-OP, exit T3** | | +2,02,948 | +1,97,688 | |
| **Current: Switch-1** | | +2,67,606 | +2,43,042 | |
| VWAP trailing exit (Zarattini, Aziz & Barbon) | Fable-OP signals. Once 0.5R in profit, exit when price closes back through VWAP. No target. | +3,09,165 | +1,33,080 | Fails: much worse from Sep to Nov |
| Skip after a trend day (Crabel; Zarattini) | Fable-OP at T3, skipping a signal if the stock had a big move the same way the day before | +2,15,436 | +1,94,376 | Fails: Rs 3,312 short from Sep to Nov |
| Noise-area filter (Zarattini, Aziz & Barbon) | Fable-OP signals only when today's move is at least 1.5 times the stock's usual move by that time of day | +2,09,911 | +1,68,015 | Fails from Sep to Nov |
| Equal option-risk lot sizing | Size each trade so the option's loss at the stop is the same, with the same total premium | +1,92,723 | +1,95,081 | No effect: same lot count on 91-96% of trades |
| Nifty volatility state (Gao, Han, Li & Zhou) | Fable-OP signals. Hold to T3 when Nifty is moving more than usual for the time of day, else exit at T1. | +1,44,174 | +1,58,272 | Fails both periods |
| Machine-learning filter, "meta-labelling" (López de Prado) | A model learns from both scores which signals make money on the option | +43,126 | +36,647 | Fails badly: the model could not tell winners from losers |

The other 30 candidates were not tested:

- some overlapped with the six above;
- some need data we don't have, such as open interest, real option-price history or sector indices;
- some repeat ideas already tried earlier.

`hunt/search_and_tests.json` lists every candidate with its sources and the reason it was left out.

### What we learned from them

- **The VWAP trail.** It cut the largest drawdown sharply (Nov-May: -22,488 against Fable-OP's -48,875), but it gave up profit from Sep to Nov. It closes trades after about an hour instead of four or five, so it misses the big trend days.
- **The skip-after-trend-day rule.** It pointed the right way in every period, but it removes only 14 to 19 trades per period. That is too few to prove anything, so it is worth watching but not adopting.
- **Equal option-risk sizing.** It changes almost nothing. An at-the-money option loses roughly the same share of the futures loss on every trade, so whole-lot rounding gives back the same lot count.
- **The machine-learning filter.** It found no pattern beyond the two existing scores.

## Which exit suits options

I ran this check myself. It is option profit for each model's own picks, using each exit rule:

| Model and exit | 12 May-31 Aug (choice) | 1 Sep-11 Nov | 3 Nov 2025-11 May 2026 | 12 May-19 Oct (cash prices) |
|---|---|---|---|---|
| Opus v3, T1 (now) | +2,39,288 | +1,84,693 | +84,362 | +1,99,051 |
| Opus v3, T3 | **+3,51,296** | +2,87,840 | +1,19,319 | +2,85,564 |
| Opus v3, square off at close | +3,06,984 | +2,73,791 | +2,79,708 | +3,41,831 |
| Opus v3, trailing stop to close | +3,15,593 | +2,40,509 | +2,49,060 | +3,45,302 |
| Fable-OP, T3 (now) | +3,47,343 | +1,97,688 | +2,02,948 | +1,83,848 |
| Fable-OP, square off at close | +3,63,801 | +99,275 | +2,97,208 | +2,09,295 |
| Switch-1 | +3,39,868 | +2,43,042 | +2,67,606 | +1,84,194 |

How likely each exit is to beat the alternative for real, from re-sampling the trading days:

| Comparison | 1 Sep-11 Nov | 3 Nov 2025-11 May 2026 |
|---|---|---|
| Opus v3 T3 beats Opus v3 T1 | +1,03,147 (93% likely) | +34,957 (67%) |
| Opus v3 square-off beats Opus v3 T1 | +89,097 (91%) | +1,95,346 (95%) |
| Opus v3 trailing stop beats Opus v3 T1 | +55,816 (85%) | +1,64,698 (96%) |
| Opus v3 trailing stop beats Fable-OP T3 | +42,821 (67%) | +46,112 (65%) |
| Opus v3 trailing stop beats Switch-1 | -2,533 (48%) | -18,547 (41%) |

What this means:

- **Holding Opus v3 longer pays with options.** T3, the setting chosen on 12 May-31 Aug, beat T1 in both test periods. It is a bought option, so the trend days that run far past T1 pay for many small losses.
- **But T3 brings bigger drawdowns for Opus v3.** On Nov 2025-May 2026 its largest drawdown was -92,316, against -63,667 at T1. The square-off and trailing-stop versions were milder: -61,775 and -56,841.
- **None of the Opus v3 exits beats Fable-OP T3 or Switch-1 with real confidence.** The best case is a 65-82% chance, which is not enough.
- **Strikes 1-2% in the money** made more profit only because they cost more. Premium paid and the worst day rose in the same proportion.

## Recommendation for options

1. **Keep Fable-OP at T3, or Switch-1, for options.** No method found online beat them on both test periods.
2. **If Opus v3 runs on options, change its exit from T1 to the trailing stop to the close (CLOSE_TR).** It is a cheap change and makes more than T1 in every period. Its worst day matches T1's and its drawdown stays below the T3 version's.
3. **Settle the rest with live prices.** The scanner already records the option result of every exit rule. The daily forward test can compare Fable-OP T3, Switch-1 and Opus v3 with the trailing stop on real option fills. It starts when you say "schedule it". The gaps between these three are small, so expect it to take a few months before one clearly leads.

## Limits

- Option prices are modelled, not real: no volatility skew and no real day-by-day implied volatility. Good to about ±10%.
- Nov 2025-May 2026 and the 12 May-19 Oct check use cash share prices in place of futures.
- On 12 May-11 Nov the profit per exit is from real futures, but the exit times come from replaying the trades on cash one-minute prices. Those times match the real result in sign 86% of the time.
- The lead from my last update (Opus v3 with a trailing stop) was found after looking at every period. The table above shows it is level with Switch-1, so it is not a new winner.

## Files

| Path | Contents |
|---|---|
| `hunt/BRIEF.md` | The brief every research and test agent worked from, with the rules above |
| `hunt/harness.py` | Test bench: loads every signal with its result for each exit rule, applies the live rule, prices the option |
| `hunt/options/` | Option model: real option legs (`legs.py`), volatility and decay fit (`calib*.py`), inputs for every signal (`optlayer.py`) |
| `hunt/<method>/run.py`, `run.log`, `results.json` | Each tested method, with its independent check in `verify/` |
| `hunt/_mine/` | Exit, strike and expiry grid (`optgrid`), risk table (`optrisk.log`), check of the trailing-stop lead (`lead_check.log`) |
| `hunt/search_and_tests.json` | All 36 candidates with sources, the shortlist and every test result |
| `hunt/sets.pkl`, `sets_opt.pkl`, `opt_inputs.pkl` | Cached signal tables, so the test bench runs without rebuilding |

To run the test bench from this folder, set `MEDHA_SP` to the `medhaalpha_research` path. The minute-price functions also need the raw data restored (see `README.md`). Logs and some scripts still show the scratch folder they were run from. The scripts that import `scanner` need the scanner engine, which is not in this repository.

The downloaded research papers are not included. Their links are in `search_and_tests.json`.
