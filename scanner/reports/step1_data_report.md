# Step 1: data layer and QA report

Generated 2026-09-26 19:50 UTC from git `0f2c42f`, config `b2080aab7cb6` (defaults). Latest session in the data: **2026-09-25**. Reproduce with `python -m nsescan universe && python -m nsescan history && python -m nsescan data-report` from `scanner/`.

## 1. Tickers loaded / failed by segment

Full load `['2016-09-26', '2026-09-26']` via batched `yf.download` (100 tickers per call, threads, `auto_adjust=True`, up to 4 retries with backoff 2.0s doubling). Wall time 115.3 s for the whole universe.

| segment | constituents (real) | loaded | failed | failed symbols |
| --- | --- | --- | --- | --- |
| N500 | 500 | 500 | 0 | none |
| MICRO250 | 250 | 250 | 0 | none |

NSE's lists also carried 5 placeholder rows (DUMMYHEG, DUMMYINGL1, DUMMYINGL2, DUMMYINXGN, DUMMYTRVN): stand-ins for demerged entities that have not listed yet. Yahoo has no data for them; the universe loader now drops `DUMMY*` rows, so the universe is 500 + 250.

## 2. Benchmarks

| benchmark | ticker | returns data | bars | first | last | sessions missing | missing dates |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nifty500 | ^CRSLDX | yes | 2462 | 2016-09-26 | 2026-09-25 | 9 | 2019-10-27, 2020-11-14, 2021-01-01, 2022-12-26, 2024-01-01, 2024-02-19, 2025-01-01, 2025-02-01, 2026-01-01 |
| nifty50 | ^NSEI | yes | 2467 | 2016-09-26 | 2026-09-25 | 4 | 2018-01-01, 2019-01-01, 2019-10-27, 2020-11-14 |
| vix | ^INDIAVIX | yes | 2452 | 2016-09-26 | 2026-09-25 | 19 | 2019-10-27, 2020-01-01, 2020-11-14, 2021-01-01, 2021-01-22, 2021-02-15, 2021-02-17, 2021-05-05, 2021-05-11, 2021-05-20, 2021-05-25, 2021-05-31, 2021-07-05, 2022-12-26, 2024-01-01, 2024-02-19, 2025-01-01, 2025-02-01, 2026-01-01 |

All three return data. 21 of the 21 dates missing from a benchmark are sessions on which stocks traded normally (real bars, < 5% stubs), i.e. gaps in Yahoo's index series, not holidays. The regime carries the last benchmark value forward over them.

## 3. Session calendar and Yahoo stub bars

2471 sessions from 2016-09-26 to 2026-09-25, derived from the data (a date is a session when >= 50% of listed symbols have a bar).

Yahoo writes *stub bars* (volume 0, open = high = low = close = previous close) in two situations, both found in this data:

* **NSE holidays**: 2026-01-15, 2026-05-01, 2026-05-28, 2026-06-26, 2026-09-14. Nearly every symbol has a stub and Nifty 50 has no bar. These dates are dropped; left in, each would count as a zero-volume day and, under the strict MICRO250 rule, exclude every microcap for a year.
* **Real sessions with missing stock data**: 2024-01-15 (Nifty 50 +0.93%, 24% of stock bars stubbed), 2025-03-18 (Nifty 50 +1.45%, 99% of stock bars stubbed). The index moved, so the market was open; the stock bars are placeholders and the next bar carries both days' move. The session is kept and its stub bars are dropped, so they count as missing bars, not zero-volume days.

Bars dropped: gap_session_stub 851, off_calendar_holiday_stub 3549. Detection threshold `data.stub_date_min_share` = 0.1; on the remaining sessions the stub share has median 0.16%, 99th percentile 1.08%, max 3.3% (2021-11-04).

133 weekdays since 2017 have no bars at all (~13 a year, in line with NSE's weekday holidays). NSE's full special session on Saturday 2024-01-20 is also absent from Yahoo, so the 2024-01-23 bar carries both sessions.

## 4. History depth

| segment | symbols | full 10y | < 250 bars | min | median | mean |
| --- | --- | --- | --- | --- | --- | --- |
| N500 | 500 | 327 | 14 | 189 | 2470 | 2019 |
| MICRO250 | 250 | 133 | 15 | 191 | 2469 | 1774 |

Many current constituents listed during the window, so the early years hold far fewer names (see the eligible-per-day counts in the step-2 report).

## 5. Data QA as of 2026-09-25

Point-in-time rules (the backtest applies the same mask on every past date):

* `qa.min_bars` = `{"N500": 250, "MICRO250": 250}`
* `qa.max_missing_pct` = `{"N500": 0.02, "MICRO250": 0.02}`
* `qa.max_zero_volume_days` = `{"N500": 3, "MICRO250": 0}`
* `qa.big_move_threshold` = `0.25`
* `qa.max_big_moves` = `{"N500": 0, "MICRO250": 0}`
* `qa.lookback_sessions` = `252`

| segment | universe | with data | pass QA | excluded | excl: <250 bars | excl: missing >2% | excl: zero-volume | excl: >25% move | flagged >25% move | stale |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N500 | 500 | 500 | 481 | 19 | 14 | 0 | 0 | 5 | 5 | 0 |
| MICRO250 | 250 | 250 | 229 | 21 | 15 | 0 | 3 | 3 | 3 | 0 |

* Excluded N500 (19): CANHLIFE (insufficient_history), EMMVEE (insufficient_history), GROWW (insufficient_history), HEGAM (big_move), ICICIAMC (insufficient_history), JAINREC (insufficient_history), LENSKART (insufficient_history), LGEINDIA (insufficient_history), MEESHO (insufficient_history), PINELABS (insufficient_history), PIRAMALFIN (insufficient_history), POLICYBZR (big_move), PWL (insufficient_history), TATACAP (insufficient_history), TENNIND (insufficient_history), TMCV (insufficient_history), TMPV (big_move), TRENT (big_move), VEDL (big_move)
* Excluded MICRO250 (21): AEQUS (insufficient_history), ATLANTAELE (insufficient_history), CAPILLARY (insufficient_history), CCAVENUE (zero_volume), CORONA (insufficient_history), CRAMC (insufficient_history), EMBDL (zero_volume), INDIAGLYCO (big_move), MAHSCOOTER (zero_volume), ORKLAINDIA (insufficient_history), PARKHOSPS (insufficient_history), RUBICON (insufficient_history), SAATVIKGL (insufficient_history), SKFINDIA (big_move), SKFINDUS (insufficient_history), STYL (insufficient_history), SUDEEPPHRM (insufficient_history), TRIVENI (big_move), UTLSOLAR (insufficient_history), WAKEFIT (insufficient_history), WEWORK (insufficient_history)

## 6. Single-day moves over 25% (full history)

| segment | total | up | down |
| --- | --- | --- | --- |
| MICRO250 | 26 | 9 | 17 |
| N500 | 78 | 40 | 38 |

Many of these are not trading moves. Several coincide with demergers that Yahoo did not adjust: Tata Motors (TMPV 2025-10-14), ABFRL (2025-05-22), SKF India (2025-10-15), Quess (2025-04-15) and Strides (STAR 2024-12-06). 6 fall on 1 January (CGCL, GPIL, MOTILALOFS, PARAS, REDTAPE, TRENT). Muhurat sessions produce spikes that reverse two sessions later (INDIAMART and THYROCARE on 2019-10-27 and 2020-11-14). Genuine moves exist too (PSU-bank recapitalisation 2017-10-25, March 2020, Adani 2023), mostly on several times normal volume. A corrupted history distorts SMA150/200, 52-week levels and RS for a year, so `qa.max_big_moves` excludes a name for 252 sessions after such a move in **both** segments (set N500 to `null` to flag only). Trades that span such a day are counted separately in step 2.

<details><summary>All moves</summary>

| segment | symbol | date | move | vol / 50d median |
| --- | --- | --- | --- | --- |
| MICRO250 | EMBDL | 2017-04-17 | +40.0% | 32.15 |
| MICRO250 | AHLUCONT | 2017-09-06 | +168.9% |  |
| MICRO250 | HCC | 2018-05-03 | -25.4% | 14.10 |
| MICRO250 | PCJEWELLER | 2018-05-04 | +43.8% | 32.77 |
| MICRO250 | PCJEWELLER | 2018-05-07 | +37.6% | 34.16 |
| MICRO250 | PCJEWELLER | 2018-07-16 | -25.6% | 4.80 |
| MICRO250 | CCAVENUE | 2018-09-28 | -70.8% | 35.72 |
| MICRO250 | CCAVENUE | 2018-10-22 | -26.2% | 8.43 |
| MICRO250 | PCJEWELLER | 2018-11-02 | +27.1% | 8.61 |
| MICRO250 | THYROCARE | 2019-10-27 | +207.2% | 0.19 |
| MICRO250 | THYROCARE | 2019-10-29 | -67.5% | 1.21 |
| MICRO250 | ALOKINDS | 2020-02-19 | +410.6% | 1.34 |
| MICRO250 | AHLUCONT | 2020-11-14 | -29.4% |  |
| MICRO250 | THYROCARE | 2020-11-14 | +203.7% | 0.05 |
| MICRO250 | AHLUCONT | 2020-11-17 | +41.7% |  |
| MICRO250 | THYROCARE | 2020-11-17 | -67.6% | 0.53 |
| MICRO250 | DIACABS | 2023-09-18 | -88.1% |  |
| MICRO250 | STAR | 2024-12-06 | -54.0% | 0.44 |
| MICRO250 | PARAS | 2025-01-01 | -50.1% | 0.78 |
| MICRO250 | REDTAPE | 2025-01-01 | -74.8% | 1.25 |
| MICRO250 | QUESS | 2025-04-15 | -50.7% | 0.30 |
| MICRO250 | STLTECH | 2025-04-24 | -25.2% | 0.18 |
| MICRO250 | JSLL | 2025-06-03 | -78.3% | 11.10 |
| MICRO250 | SKFINDIA | 2025-10-15 | -54.8% | 1.45 |
| MICRO250 | TRIVENI | 2026-07-22 | -41.6% | 0.49 |
| MICRO250 | INDIAGLYCO | 2026-09-02 | -78.8% | 0.67 |
| N500 | IDEA | 2017-01-30 | +25.3% | 26.37 |
| N500 | FSL | 2017-02-27 | +25.5% |  |
| N500 | J&KBANK | 2017-02-27 | -53.8% |  |
| N500 | CDSL | 2017-07-03 | -49.9% |  |
| N500 | BANKBARODA | 2017-10-25 | +31.4% | 13.03 |
| N500 | BANKINDIA | 2017-10-25 | +34.1% | 11.01 |
| N500 | CANBK | 2017-10-25 | +38.7% | 22.04 |
| N500 | PNB | 2017-10-25 | +46.2% | 30.51 |
| N500 | SBIN | 2017-10-25 | +27.7% | 21.42 |
| N500 | UNIONBANK | 2017-10-25 | +34.2% | 11.49 |
| N500 | YESBANK | 2018-09-21 | -29.0% | 19.13 |
| N500 | ADANIPOWER | 2018-10-10 | +25.3% | 1.42 |
| N500 | ZEEL | 2019-01-25 | -26.6% | 19.34 |
| N500 | RPOWER | 2019-02-04 | -34.8% | 9.66 |
| N500 | RPOWER | 2019-02-05 | -30.2% | 23.42 |
| N500 | YESBANK | 2019-02-14 | +28.1% | 5.80 |
| N500 | SUZLON | 2019-02-22 | +29.2% | 11.03 |
| N500 | SUZLON | 2019-03-05 | +25.2% | 12.29 |
| N500 | YESBANK | 2019-04-30 | -29.2% | 6.68 |
| N500 | ADANIENT | 2019-05-20 | +27.4% | 9.35 |
| N500 | IDEA | 2019-07-29 | -27.0% | 13.31 |
| N500 | SAMMAANCAP | 2019-09-30 | -34.4% | 4.58 |
| N500 | YESBANK | 2019-10-03 | +32.8% | 3.21 |
| N500 | ABREL | 2019-10-11 | -55.4% | 3.96 |
| N500 | INDIAMART | 2019-10-27 | +104.1% | 0.13 |
| N500 | INDIAMART | 2019-10-29 | -50.6% | 0.64 |
| N500 | IDEA | 2019-11-19 | +36.0% | 8.23 |
| N500 | PATANJALI | 2020-01-27 | -94.9% |  |
| N500 | IDEA | 2020-02-19 | +40.0% | 6.30 |
| N500 | YESBANK | 2020-03-05 | +25.6% | 5.58 |
| N500 | YESBANK | 2020-03-06 | -56.1% | 1.36 |
| N500 | YESBANK | 2020-03-09 | +31.6% | 5.17 |
| N500 | YESBANK | 2020-03-11 | +35.5% | 2.94 |
| N500 | ADANIPOWER | 2020-03-12 | -26.5% | 3.55 |
| N500 | IDEA | 2020-03-13 | +33.3% | 1.44 |
| N500 | YESBANK | 2020-03-16 | +45.2% | 1.18 |
| N500 | YESBANK | 2020-03-17 | +58.1% | 1.57 |
| N500 | IDEA | 2020-03-18 | -35.1% | 3.95 |
| N500 | SAMMAANCAP | 2020-03-19 | -33.7% | 2.42 |
| N500 | AXISBANK | 2020-03-23 | -27.9% | 4.43 |
| N500 | BAJAJFINSV | 2020-03-23 | -25.9% | 3.10 |
| N500 | BANDHANBNK | 2020-03-23 | -25.0% | 3.32 |
| N500 | CHOLAFIN | 2020-03-23 | -29.6% | 1.80 |
| N500 | M&MFIN | 2020-03-23 | -28.6% | 1.82 |
| N500 | MFSL | 2020-03-23 | -29.2% | 0.53 |
| N500 | ICICIPRULI | 2020-03-25 | +25.9% | 2.51 |
| N500 | BANDHANBNK | 2020-03-26 | +39.3% | 5.53 |
| N500 | INDUSINDBK | 2020-03-26 | +44.7% | 5.26 |
| N500 | JINDALSTEL | 2020-04-07 | +28.9% | 3.02 |
| N500 | SAMMAANCAP | 2020-06-19 | +31.1% | 4.52 |
| N500 | GLENMARK | 2020-06-22 | +27.0% | 18.56 |
| N500 | IDEA | 2020-09-03 | +26.8% | 1.48 |
| N500 | ANANTRAJ | 2020-10-06 | +33.4% | 1.08 |
| N500 | INDIAMART | 2020-11-14 | +99.4% | 0.02 |
| N500 | INDIAMART | 2020-11-17 | -51.2% | 0.48 |
| N500 | ZEEL | 2021-09-14 | +40.0% | 35.24 |
| N500 | IDEA | 2021-09-16 | +25.7% | 0.00 |
| N500 | ZEEL | 2021-09-22 | +31.7% | 28.43 |
| N500 | MOTHERSON | 2022-01-14 | +28.6% | 4.60 |
| N500 | ADANIENT | 2023-02-01 | -28.2% | 8.34 |
| N500 | ADANIENT | 2023-02-02 | -26.7% | 21.26 |
| N500 | CGCL | 2024-01-01 | -74.8% | 1.30 |
| N500 | GPIL | 2024-01-01 | -79.5% | 8.20 |
| N500 | MOTILALOFS | 2024-01-01 | -74.6% | 2.49 |
| N500 | IRFC | 2024-01-16 | +25.1% | 10.17 |
| N500 | OFSS | 2024-01-18 | +28.7% | 49.35 |
| N500 | ZEEL | 2024-01-23 | -33.6% | 11.80 |
| N500 | FORCEMOT | 2024-02-14 | +31.9% |  |
| N500 | HINDZINC | 2024-05-21 | +25.6% | 6.46 |
| N500 | RECLTD | 2024-06-04 | -25.2% | 8.26 |
| N500 | INDUSINDBK | 2025-03-11 | -27.2% | 25.61 |
| N500 | ABFRL | 2025-05-22 | -66.6% | 17.84 |
| N500 | IEX | 2025-07-24 | -29.6% | 21.66 |
| N500 | TMPV | 2025-10-14 | -40.2% | 4.85 |
| N500 | TRENT | 2026-01-01 | -33.0% | 0.97 |
| N500 | VEDL | 2026-04-30 | -64.9% | 5.10 |
| N500 | HEGAM | 2026-09-07 | -62.6% | 2.93 |
| N500 | POLICYBZR | 2026-09-24 | -36.0% | 25.93 |

</details>

## 7. Traded value vs the liquidity floors

Median of close x volume over the last 50 bars, INR crore, on 2026-09-25. Prices are Yahoo dividend-adjusted (`auto_adjust=True`), so older traded values are slightly understated (by the cumulative dividend yield since then).

| segment | floor (cr) | n | p5 | p10 | p25 | median | p75 | p90 | >= floor | [<1] | [1-2] | [2-3] | [3-5] | [5-10] | [10-20] | [20-50] | [50-100] | [>100] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N500 | 10.0 | 500 | 9.0 | 12.4 | 21.8 | 62.3 | 142.9 | 287.3 | 468 | 0 | 0 | 0 | 10 | 22 | 78 | 118 | 92 | 180 |
| MICRO250 | 3.0 | 250 | 3.3 | 4.0 | 7.9 | 14.2 | 24.6 | 49.2 | 243 | 0 | 1 | 6 | 27 | 49 | 81 | 61 | 17 | 8 |

MICRO250 through time (all name-days with a defined 50-day median, current constituents):

| year | name-days | median | p10 | share >= 3 cr | share >= 2 cr | share >= 5 cr |
| --- | --- | --- | --- | --- | --- | --- |
| 2016 | 2261 | 1.5 | 0.1 | 26% | 40% | 18% |
| 2017 | 33337 | 1.8 | 0.2 | 37% | 47% | 25% |
| 2018 | 34631 | 1.8 | 0.2 | 39% | 48% | 28% |
| 2019 | 35786 | 0.8 | 0.1 | 22% | 29% | 16% |
| 2020 | 38907 | 1.6 | 0.1 | 37% | 45% | 26% |
| 2021 | 41052 | 6.2 | 0.8 | 69% | 77% | 57% |
| 2022 | 44658 | 5.0 | 0.9 | 69% | 78% | 50% |
| 2023 | 47403 | 7.0 | 1.5 | 78% | 86% | 63% |
| 2024 | 51724 | 14.9 | 4.7 | 96% | 98% | 89% |
| 2025 | 56469 | 12.0 | 4.9 | 97% | 99% | 90% |
| 2026 | 44994 | 11.9 | 4.5 | 97% | 99% | 87% |

Today 243 of 250 MICRO250 names clear the INR 3 cr floor, so it removes only the thinnest ~3% now. Below the floor: SANOFICONR 1.59, SUBROS 2.33, HGINFRA 2.53, TSFINV 2.59, SAATVIKGL 2.76, NFL 2.98, AHLUCONT 2.99. In 2017-2020 only 22-39% of name-days cleared it. It is a nominal rupee floor applied to today's constituents, most of which were much smaller then, so it binds far harder in the early backtest years. The ₹3 cr level itself looks reasonable for today's list; whether to scale it with market turnover for the backtest is your call.

Pass data QA **and** the liquidity gate today: N500 438, MICRO250 216.

## 8. Known gaps (not faked)

* No delivery %: Yahoo has none.
* No price-band or trade-for-trade (T2T) history. The constituent CSV's `Series` column (EQ/BE) is stored for today only; the circuit check infers limits from price action.
* NSE earnings dates via Yahoo are unreliable; the earnings flag will be best effort, flag only.
* Survivorship bias: the universe is today's constituents, so the backtest never sees names that dropped out or delisted. Worse for MICRO250 (higher index churn); its results are reported separately and should be read as optimistic.
* Yahoo stub bars and unadjusted corporate actions exist (sections 3 and 6); they are detected, not repaired.
