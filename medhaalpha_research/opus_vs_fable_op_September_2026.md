# Opus vs Fable-OP: September 2026 (21 sessions, Nifty -6.05 %)

Which trades each model took, and the same-day results, come from the scanner's own six-month backtest report stored on the VPS (generated 13 Nov 2026). That report was priced on the real September futures contracts, live rule (first 6 signals a day scoring 75 or more, setups A and B), lots sized to risk Rs 15,000 a trade, charges and 0.02 % slippage a side included, anything open squared off at the close. No option results: the September option contracts have expired.

## Same-day results (squared off at the close)

| | Opus | Fable-OP |
|---|---|---|
| Trades | 64 | 25 |
| Reached T1 | 23 | 14 |
| Stopped out | 15 | 7 |
| Squared off at the close | 26 | 4 |
| Net, exit at T1 (Rs) | +37,966 | +50,867 |
| Net, hold for T2 (Rs) | +1,11,661 | +59,691 |
| Net, hold for T3 (Rs) | +1,70,790 | +96,500 |
| Net, stop only, exit at the close (Rs) | +1,78,496 | +71,464 |
| Net per trade at T1 (Rs) | +593 | +2,035 |
| Days in profit at T1 | 7 of 21 | 9 of 21 |
| Worst day at T1 (Rs) | -35,541 | -33,341 |

## Day by day, exit at T1, same day

| Date | Opus trades | Opus T1 hit / stopped | Opus net (Rs) | Fable-OP trades | Fable-OP T1 hit / stopped | Fable-OP net (Rs) |
|---|---|---|---|---|---|---|
| 09-01 | 5 | 2 / 2 | -6,479 | 0 | 0 / 0 | no trade |
| 09-02 | 5 | 1 / 4 | -35,541 | 0 | 0 / 0 | no trade |
| 09-03 | 1 | 1 / 0 | +8,482 | 6 | 4 / 1 | +20,500 |
| 09-04 | 2 | 0 / 0 | -12,054 | 1 | 0 / 1 | -6,294 |
| 09-07 | 4 | 0 / 1 | -14,042 | 0 | 0 / 0 | no trade |
| 09-08 | 2 | 1 / 0 | +7,702 | 1 | 1 / 0 | +10,989 |
| 09-09 | 2 | 0 / 0 | -5,541 | 2 | 1 / 0 | +2,647 |
| 09-10 | 0 | 0 / 0 | no trade | 1 | 1 / 0 | +10,342 |
| 09-11 | 3 | 1 / 1 | -5,499 | 6 | 1 / 4 | -33,341 |
| 09-15 | 6 | 5 / 0 | +43,009 | 0 | 0 / 0 | no trade |
| 09-16 | 0 | 0 / 0 | no trade | 0 | 0 / 0 | no trade |
| 09-17 | 1 | 0 / 0 | -6,516 | 0 | 0 / 0 | no trade |
| 09-18 | 0 | 0 / 0 | no trade | 2 | 1 / 0 | +6,820 |
| 09-21 | 3 | 1 / 0 | -3,485 | 2 | 1 / 1 | +3,333 |
| 09-22 | 5 | 0 / 1 | -4,470 | 0 | 0 / 0 | no trade |
| 09-23 | 1 | 0 / 0 | +7,671 | 0 | 0 / 0 | no trade |
| 09-24 | 6 | 1 / 3 | -13,642 | 0 | 0 / 0 | no trade |
| 09-25 | 2 | 0 / 0 | +4,246 | 0 | 0 / 0 | no trade |
| 09-28 | 6 | 5 / 0 | +45,938 | 1 | 1 / 0 | +7,073 |
| 09-29 | 4 | 1 / 2 | -3,352 | 2 | 2 / 0 | +19,252 |
| 09-30 | 6 | 4 / 1 | +31,539 | 1 | 1 / 0 | +9,546 |
| **Total** | **64** | **23 / 15** | **+37,966** | **25** | **14 / 7** | **+50,867** |

## Held across days (no square-off at the close)

Same trades. The September futures candles can no longer be read, so each trade is followed on its cash share: stop and targets rebuilt by the scanner's level code at the report's signal minute, then held until the target or the stop. Treat these as approximate. Check: followed the same way but squared off at the close, the cash route gives Opus +51,623 / +1,03,627 / +1,54,884 and Fable-OP +47,289 / +89,214 / +1,30,045 at T1 / T2 / T3, against the report's figures above.

| Exit | Opus: hit / stopped | Opus net (Rs) | Fable-OP: hit / stopped | Fable-OP net (Rs) |
|---|---|---|---|---|
| T1 | 39 / 25 | +1,26,610 | 16 / 9 | +53,737 |
| T2 | 27 / 37 | +1,50,393 | 12 / 13 | +87,212 |
| T3 | 25 / 39 | +3,07,219 | 10 / 15 | +1,02,498 |

Trading days taken to reach T3 (after the entry day):

| Trading days after entry day | Opus | Fable-OP |
|---|---|---|
| Same session | 8 | 7 |
| 1 | 7 | 2 |
| 2 | 3 | 0 |
| 3 | 1 | 0 |
| 4 | 1 | 0 |
| 5 or more | 5 | 1 |
| **Reached T3** | **25** | **10** |
| Longest | 10 | 5 |

## Opus: every September trade

| Date | Time | Symbol | Side | Score | Same day, exit T1 (Rs) | Same day, hold T3 (Rs) | Held: T1 result | Held: T3 result | Days to T3 exit | Held T3 net (Rs) |
|---|---|---|---|---|---|---|---|---|---|---|
| 09-01 | 11:55 | INFY | LONG | 85.8 | -1,102 | -1,102 | stopped | stopped | 1 | -11,489 |
| 09-01 | 13:11 | M&M | SHORT | 92.2 | +7,861 | +5,300 | hit | hit | 1 | +23,567 |
| 09-01 | 13:11 | MARUTI | SHORT | 80.3 | -11,200 | -11,200 | stopped | stopped | 0 | -10,896 |
| 09-01 | 10:16 | MPHASIS | LONG | 77.6 | +7,808 | +6,269 | hit | stopped | 1 | -8,071 |
| 09-01 | 11:55 | NAUKRI | LONG | 75.4 | -9,846 | -9,846 | stopped | stopped | 0 | -8,854 |
| 09-02 | 10:12 | BLUESTARCO | SHORT | 78.6 | +8,857 | +3,265 | hit | stopped | 1 | -10,972 |
| 09-02 | 10:07 | CONCOR | LONG | 82.5 | -7,296 | -7,296 | stopped | stopped | 0 | -9,481 |
| 09-02 | 14:11 | LICHSGFIN | LONG | 90.0 | -12,789 | -12,789 | hit | hit | 2 | +31,083 |
| 09-02 | 10:46 | MAHABANK | LONG | 95.3 | -11,100 | -11,100 | stopped | stopped | 0 | -9,927 |
| 09-02 | 10:02 | PNB | LONG | 82.8 | -13,213 | -13,213 | stopped | stopped | 4 | -13,420 |
| 09-03 | 09:18 | MAHABANK | LONG | 76.1 | +8,482 | +29,331 | hit | hit | 0 | +30,327 |
| 09-04 | 13:49 | APLAPOLLO | LONG | 94.7 | -7,238 | -7,238 | hit | stopped | 1 | -9,272 |
| 09-04 | 13:59 | JINDALSTEL | LONG | 79.4 | -4,816 | -4,816 | stopped | stopped | 1 | -11,745 |
| 09-07 | 11:17 | GODREJPROP | SHORT | 95.5 | -714 | -714 | hit | hit | 4 | +29,976 |
| 09-07 | 12:55 | NATIONALUM | SHORT | 86.5 | -2,027 | -2,027 | stopped | stopped | 1 | -8,308 |
| 09-07 | 10:35 | NYKAA | LONG | 88.7 | -13,252 | -13,252 | stopped | stopped | 0 | -13,406 |
| 09-07 | 11:46 | SBICARD | LONG | 91.2 | +1,951 | +1,951 | stopped | stopped | 4 | -10,477 |
| 09-08 | 10:43 | CGPOWER | LONG | 78.4 | -3,602 | -3,602 | hit | stopped | 3 | -10,309 |
| 09-08 | 11:28 | KALYANKJIL | LONG | 93.7 | +11,303 | +7,391 | hit | stopped | 3 | -13,382 |
| 09-09 | 11:32 | DIXON | SHORT | 83.5 | +3,139 | +3,139 | hit | hit | 1 | +24,936 |
| 09-09 | 12:23 | LTM | SHORT | 80.3 | -8,680 | -8,680 | stopped | stopped | 0 | -9,856 |
| 09-11 | 10:06 | BANDHANBNK | LONG | 83.7 | +7,832 | +1,608 | hit | stopped | 1 | -10,874 |
| 09-11 | 11:32 | ETERNAL | LONG | 88.2 | -11,837 | -11,837 | stopped | stopped | 0 | -8,683 |
| 09-11 | 10:29 | LICHSGFIN | LONG | 87.9 | -1,494 | -1,494 | hit | stopped | 1 | -8,287 |
| 09-15 | 09:56 | BAJAJFINSV | SHORT | 80.1 | +8,943 | +11,643 | hit | hit | 1 | +25,988 |
| 09-15 | 09:56 | BEL | SHORT | 77.5 | +8,987 | +25,236 | hit | hit | 0 | +25,237 |
| 09-15 | 09:56 | GMRAIRPORT | SHORT | 84.9 | +10,674 | +22,953 | hit | stopped | 3 | -10,105 |
| 09-15 | 09:56 | GODREJPROP | SHORT | 83.2 | +6,699 | +12,388 | hit | stopped | 5 | -8,871 |
| 09-15 | 09:56 | LT | SHORT | 79.6 | -191 | -191 | hit | stopped | 3 | -14,477 |
| 09-15 | 09:56 | SHRIRAMFIN | SHORT | 83.3 | +7,895 | +20,934 | hit | hit | 10 | +30,138 |
| 09-17 | 09:45 | MCX | LONG | 80.5 | -6,516 | -6,516 | stopped | stopped | 2 | -12,899 |
| 09-21 | 09:33 | BLUESTARCO | LONG | 81.7 | -4,861 | -4,861 | stopped | stopped | 0 | -13,505 |
| 09-21 | 11:03 | HDFCLIFE | LONG | 75.5 | -9,712 | -9,712 | stopped | stopped | 0 | -14,659 |
| 09-21 | 09:17 | PATANJALI | LONG | 82.2 | +11,088 | +30,316 | hit | hit | 0 | +33,648 |
| 09-22 | 10:50 | CONCOR | SHORT | 95.7 | +7,071 | +7,071 | hit | hit | 5 | +31,202 |
| 09-22 | 14:05 | FORCEMOT | SHORT | 82.6 | -5,378 | -5,378 | stopped | stopped | 1 | -12,931 |
| 09-22 | 10:58 | MOTILALOFS | LONG | 75.6 | -9,330 | -9,330 | stopped | stopped | 0 | -10,259 |
| 09-22 | 10:52 | MPHASIS | SHORT | 78.9 | -3,783 | -3,783 | hit | hit | 5 | +27,053 |
| 09-22 | 13:49 | VOLTAS | SHORT | 79.7 | +6,949 | +6,949 | hit | stopped | 1 | -14,869 |
| 09-23 | 12:18 | NYKAA | LONG | 82.9 | +7,671 | +7,671 | hit | stopped | 1 | -12,621 |
| 09-24 | 09:36 | ALKEM | LONG | 80.4 | -7,204 | -7,204 | stopped | stopped | 0 | -10,322 |
| 09-24 | 09:48 | AUBANK | SHORT | 79.3 | -220 | -220 | stopped | stopped | 0 | -13,017 |
| 09-24 | 09:17 | BAJAJFINSV | SHORT | 85.4 | +1,657 | +1,657 | stopped | stopped | 0 | -7,763 |
| 09-24 | 09:34 | SBILIFE | LONG | 99.1 | -8,112 | -8,112 | stopped | stopped | 0 | -14,297 |
| 09-24 | 09:17 | UJJIVANSFB | SHORT | 75.3 | +10,991 | -11,735 | hit | stopped | 0 | -11,735 |
| 09-24 | 09:34 | VMM | LONG | 77.8 | -10,753 | -10,753 | stopped | stopped | 0 | -10,560 |
| 09-25 | 12:17 | APLAPOLLO | LONG | 75.3 | +811 | +811 | stopped | stopped | 2 | -12,125 |
| 09-25 | 11:51 | BLUESTARCO | LONG | 89.3 | +3,435 | +3,435 | hit | stopped | 3 | -8,912 |
| 09-28 | 10:19 | ADANIGREEN | SHORT | 76.9 | +10,078 | +20,520 | hit | hit | 0 | +22,324 |
| 09-28 | 10:30 | ATHERENERG | SHORT | 82.4 | +11,354 | +8,578 | hit | hit | 3 | +30,474 |
| 09-28 | 09:25 | CHOLAFIN | SHORT | 75.0 | -4,846 | -4,846 | hit | hit | 7 | +47,795 |
| 09-28 | 11:42 | IDEA | SHORT | 90.6 | +11,871 | +12,586 | hit | hit | 2 | +41,188 |
| 09-28 | 09:40 | NMDC | SHORT | 76.5 | +10,407 | +16,619 | hit | hit | 1 | +32,951 |
| 09-28 | 09:19 | YESBANK | SHORT | 88.4 | +7,073 | +19,516 | hit | hit | 0 | +18,274 |
| 09-29 | 13:37 | FORTIS | SHORT | 79.3 | -8,103 | -8,103 | hit | hit | 1 | +18,063 |
| 09-29 | 10:07 | IDEA | SHORT | 79.1 | -12,414 | -12,414 | hit | hit | 2 | +50,504 |
| 09-29 | 11:01 | KFINTECH | SHORT | 76.2 | +12,690 | +33,050 | hit | hit | 0 | +30,215 |
| 09-29 | 12:42 | PREMIERENE | SHORT | 93.3 | +4,476 | +4,476 | stopped | stopped | 0 | -11,807 |
| 09-30 | 09:33 | APOLLOHOSP | SHORT | 78.1 | +10,572 | +27,201 | hit | hit | 0 | +25,767 |
| 09-30 | 09:33 | FORTIS | SHORT | 81.7 | +9,546 | +25,166 | hit | hit | 0 | +24,239 |
| 09-30 | 10:44 | IDEA | SHORT | 85.1 | +11,905 | +18,339 | hit | hit | 1 | +34,072 |
| 09-30 | 10:44 | JUBLFOOD | SHORT | 82.0 | -2,283 | -2,283 | hit | hit | 1 | +21,533 |
| 09-30 | 09:52 | LICHSGFIN | SHORT | 75.7 | -8,232 | -8,232 | stopped | stopped | 0 | -8,229 |
| 09-30 | 09:33 | MAXHEALTH | SHORT | 85.6 | +10,032 | +9,297 | hit | hit | 5 | +28,335 |

## Fable-OP: every September trade

| Date | Time | Symbol | Side | Score | Same day, exit T1 (Rs) | Same day, hold T3 (Rs) | Held: T1 result | Held: T3 result | Days to T3 exit | Held T3 net (Rs) |
|---|---|---|---|---|---|---|---|---|---|---|
| 09-03 | 09:17 | BANKINDIA | LONG | 84.2 | -3,169 | -3,169 | stopped | stopped | 2 | -9,090 |
| 09-03 | 09:26 | COALINDIA | LONG | 79.8 | +8,300 | -11,800 | hit | stopped | 0 | -11,810 |
| 09-03 | 09:21 | ICICIBANK | LONG | 87.0 | -9,004 | -9,004 | stopped | stopped | 0 | -7,669 |
| 09-03 | 09:18 | MAHABANK | LONG | 82.8 | +8,482 | +29,331 | hit | hit | 0 | +30,327 |
| 09-03 | 09:17 | RBLBANK | LONG | 81.3 | +5,225 | -10,004 | hit | hit | 0 | +29,660 |
| 09-03 | 09:17 | SOLARINDS | LONG | 89.2 | +10,666 | +13,914 | hit | hit | 1 | +25,363 |
| 09-04 | 09:17 | LTM | LONG | 77.2 | -6,294 | -6,294 | stopped | stopped | 0 | -10,432 |
| 09-08 | 09:17 | HAL | LONG | 88.5 | +10,989 | +30,985 | hit | hit | 0 | +17,239 |
| 09-09 | 09:18 | COALINDIA | LONG | 86.8 | +7,155 | +7,964 | hit | stopped | 3 | -14,510 |
| 09-09 | 09:18 | OIL | LONG | 77.9 | -4,507 | -4,507 | stopped | stopped | 0 | -8,281 |
| 09-10 | 09:17 | ATHERENERG | LONG | 78.5 | +10,342 | +11,504 | hit | stopped | 2 | -11,990 |
| 09-11 | 09:17 | HDFCBANK | SHORT | 75.7 | -14,503 | -14,503 | stopped | stopped | 0 | -11,572 |
| 09-11 | 09:17 | HINDALCO | SHORT | 82.9 | -7,252 | -7,252 | stopped | stopped | 0 | -11,840 |
| 09-11 | 09:17 | IEX | SHORT | 79.7 | +1,604 | +1,604 | hit | hit | 1 | +26,579 |
| 09-11 | 09:18 | LT | SHORT | 76.5 | -13,339 | -13,339 | stopped | stopped | 0 | -14,624 |
| 09-11 | 09:17 | NMDC | SHORT | 81.4 | -8,957 | -8,957 | stopped | stopped | 0 | -9,898 |
| 09-11 | 09:18 | ONGC | LONG | 81.1 | +9,105 | -13,829 | hit | stopped | 0 | -13,152 |
| 09-18 | 09:33 | JUBLFOOD | LONG | 78.6 | +8,417 | +8,480 | hit | stopped | 4 | -8,132 |
| 09-18 | 09:17 | ZYDUSLIFE | LONG | 83.8 | -1,597 | -1,597 | hit | hit | 5 | +34,019 |
| 09-21 | 09:17 | BPCL | LONG | 79.8 | -7,755 | -7,755 | stopped | stopped | 0 | -14,275 |
| 09-21 | 09:17 | PATANJALI | LONG | 77.0 | +11,088 | +30,316 | hit | hit | 0 | +33,648 |
| 09-28 | 09:19 | YESBANK | SHORT | 80.2 | +7,073 | +19,516 | hit | hit | 0 | +18,274 |
| 09-29 | 09:17 | DRREDDY | LONG | 82.3 | +7,949 | +2,703 | hit | stopped | 1 | -8,290 |
| 09-29 | 09:17 | UNITDSPR | SHORT | 90.6 | +11,303 | +27,026 | hit | hit | 0 | +28,714 |
| 09-30 | 09:33 | FORTIS | SHORT | 82.7 | +9,546 | +25,166 | hit | hit | 0 | +24,239 |

## The six months in the same report, month by month (same-day results, live rule)

| Month | Sessions | Nifty | Opus trades | Opus T1 (Rs) | Opus T3 (Rs) | Fable-OP trades | Fable-OP T1 (Rs) | Fable-OP T3 (Rs) |
|---|---|---|---|---|---|---|---|---|
| 2026-05 | 13 | -1.89 % | 43 | +14,732 | +21,119 | 20 | +79,882 | +56,567 |
| 2026-06 | 21 | +1.11 % | 67 | +91,531 | +30,642 | 45 | +36,791 | +19,065 |
| 2026-07 | 23 | +1.96 % | 58 | +727 | +33,006 | 44 | +1,26,190 | +2,42,900 |
| 2026-08 | 21 | -2.00 % | 45 | +35,090 | +48,860 | 51 | +25,412 | +1,15,177 |
| 2026-09 | 21 | -6.05 % | 64 | +37,966 | +1,70,790 | 25 | +50,867 | +96,500 |
| 2026-10 | 20 | +2.26 % | 72 | +4,488 | -67,105 | 30 | -7,181 | +44,718 |
| 2026-11 | 7 | +7.85 % | 20 | +65,828 | +1,06,098 | 18 | +49,324 | +1,27,367 |
| **12 May - 11 Nov** | **126** | | **369** | **+2,50,362** | **+3,43,410** | **233** | **+3,61,285** | **+7,02,294** |

Fable-OP's score was shaped on 12 May - 31 Aug, so those months flatter it; 1 Sep onward is its unseen period. Opus's weights were tuned on 21 Oct - 9 Nov.
