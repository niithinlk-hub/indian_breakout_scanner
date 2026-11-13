# Opus v3 on unseen dates: result

Test rules were fixed beforehand in `opus_v3_unseen_test_protocol.md`; the code fingerprints at run time match that file. Nothing on the VPS was changed.

**Dates:** 3 Nov 2025 to 11 May 2026, 127 sessions. No model was fitted on any of them. Nifty fell 7.4 % over the period (including an 11 % fall in March 2026); over the scanner's six-month backtest period it rose 6 %.

**Data:** cash-share stand-in, because real futures candles before mid-May 2026 no longer exist at the data source. On known months the stand-in showed a little over half of the real reach-T1 gap between v3 and Opus and could not judge profit.

## Verdict

- **Main test: passed.** v3 reached T1 38.3 % of the time against Opus's 28.9 %, a gap of +9.4 points (5th to 95th percentile +5.3 to +13.7), ahead in 100 % of 20,000 resamples.
- **Profit: not confirmed.** On the stand-in v3 lost Rs 1,28,597 and Opus lost Rs 1,79,918. v3 was ahead in only 60 % of resamples.
- **Stop-outs: worse than Opus** (31.7 % against 25.3 %).
- **The short side did not hold up.** Shorts picked by the Opus score lost money in this period.
- **Fable-OP did best of the four** on both accuracy and net.

## Results, same-day exit at T1 (stand-in)

| | Opus | Fable-OP | Opus v2 | Opus v3 |
|---|---|---|---|---|
| Trades | 388 | 232 | 375 | 366 |
| Reached T1 | 28.9 % | 46.6 % | 37.6 % | 38.3 % |
| Stopped out | 25.3 % | 34.5 % | 32.3 % | 31.7 % |
| Ended in profit | 50.3 % | 53.0 % | 48.5 % | 49.5 % |
| Net at T1 (Rs) | -1,79,918 | +1,543 | -2,03,092 | -1,28,597 |
| Net, hold for T3 (Rs) | -2,96,679 | +78,849 | -2,37,273 | -1,47,609 |
| Days up / down | 52 / 57 | 53 / 43 | 52 / 54 | 53 / 51 |
| Longs: trades, reached T1, net | 192, 27.1 %, -77,082 | 194, 45.9 %, -39,485 | 196, 45.9 %, -30,641 | 184, 47.3 %, +21,663 |
| Shorts: trades, reached T1, net | 196, 30.6 %, -1,02,835 | 38, 50.0 %, +41,028 | 179, 28.5 %, -1,72,452 | 182, 29.1 %, -1,50,260 |

## The items the protocol said would be reported

| Comparison | Reached T1 | Ahead in | Net (Rs) | Ahead in | Stop-outs | Trades |
|---|---|---|---|---|---|---|
| v3 against Opus | +9.4 pts | 100 % | +51,321 | 60 % | +6.4 pts | 94 % |
| v3 against v2 (the volume condition) | +0.7 pts | 89 % | +74,496 | 97 % | -0.6 pts | 98 % |
| v2 against Opus | +8.7 pts | 100 % | -23,175 | 44 % | +7.0 pts | 97 % |
| v3 against Fable-OP | -8.3 pts | 0 % | -1,30,140 | 19 % | -2.8 pts | 158 % |

- **Trade count:** v3 took 94 % as many trades as Opus (rule: at least 85 %). Met.
- **Volume condition:** among longs scoring 75 or more on Fable-OP, the 14 with relative volume under 1 reached T1 28.6 % of the time and lost Rs 2,974 a trade; the other 188 reached T1 47.9 % and made Rs 239 a trade. Same direction as in the known months.
- **Side structure:** Fable-OP's longs reached T1 far more often than Opus's longs (45.9 % against 27.1 %), as expected. Opus's shorts did not beat its longs: both lost (shorts Rs -1,02,835, longs Rs -77,082).

## Month by month: trades, reached T1, stopped, net (Rs)

| Month | Opus | Opus v3 | Fable-OP |
|---|---|---|---|
| 2025-11 | 35, 31 %, 17 %, -1,071 | 50, 46 %, 30 %, -25,979 | 49, 51 %, 31 %, -12,531 |
| 2025-12 | 49, 29 %, 24 %, -52,128 | 55, 40 %, 33 %, -36,775 | 33, 42 %, 42 %, -63,220 |
| 2026-01 | 79, 39 %, 30 %, +12,299 | 88, 38 %, 41 %, -1,24,721 | 44, 41 %, 41 %, -51,892 |
| 2026-02 | 67, 21 %, 24 %, -43,838 | 49, 29 %, 37 %, -67,389 | 24, 58 %, 38 %, +53,168 |
| 2026-03 | 67, 34 %, 22 %, +52,542 | 57, 39 %, 16 %, +1,13,018 | 31, 45 %, 26 %, +41,498 |
| 2026-04 | 69, 20 %, 22 %, -75,562 | 49, 39 %, 24 %, +39,662 | 36, 44 %, 33 %, +20,925 |
| 2026-05 | 22, 23 %, 46 %, -72,160 | 18, 39 %, 44 %, -26,413 | 15, 47 %, 27 %, +13,595 |

v3 reached T1 more often than Opus in 6 of 7 months and had the better net in 4 of 7.

## The same stand-in on both periods

This puts the unseen period next to the known one on the same measuring stick. Net per session, stand-in:

| | Known months (12 May - 19 Oct 2026) | Unseen (3 Nov 2025 - 11 May 2026) |
|---|---|---|
| Opus | +950 | -1,417 |
| Fable-OP | -293 | +12 |
| Opus v2 | +1,375 | -1,599 |
| Opus v3 | +1,376 | -1,013 |
| v3 longs: reached T1, net | 49.7 %, +78,508 | 47.3 %, +21,663 |
| v3 shorts: reached T1, net | 28.5 %, +74,221 | 29.1 %, -1,50,260 |

The long side behaved the same in both periods. The short side made money in the known months and lost in the unseen ones: it reached T1 about as often (29.1 % against 28.5 %) but was stopped out more (29.7 % against 20.8 %). Opus, v2 and v3 all did worse in the unseen period than in the known one; Fable-OP was about flat in both.

## What this does and does not show

- **Shown:** v3 is more accurate than Opus on dates nothing was fitted to, by about the margin the stand-in gave on known months. The volume condition points the same way again.
- **Not shown:** that v3 makes more money than Opus, or that it is profitable in a period like this one. The stand-in understates profit heavily (on known months it showed v3 at Rs 1.5 lakh where the real figure was Rs 5.0 lakh, and showed Fable-OP at a small loss where the real figure was a Rs 3.1 lakh profit), so these losses are not a measure of what real futures would have done. But they are no evidence of profit either.
- **New:** the scanner's six-month backtest period was kinder to every model than the six months before it. Its profit figures should not be read as typical.
- **Limits of the stand-in:** signals are found on cash prices rather than futures, so roughly four in ten trades differ from what the live scanner would pick; the stock list is today's F&O list, not the list as it stood then; lot sizes are today's.

## What would settle the profit question

Only results on real futures, which means forward trades: the data source keeps no real futures history older than six months. A daily after-close replay on live contracts (the method that matched the scanner exactly on 21 Oct - 13 Nov) would build that record for all five models.
