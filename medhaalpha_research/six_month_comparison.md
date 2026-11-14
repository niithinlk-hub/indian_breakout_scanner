# Six-month comparison: all models, options and futures

14 Nov 2026. Offline research on cached data. Nothing on the live scanner was touched.

## What was compared

- **Period:** 12 May to 11 Nov 2026, 126 sessions. This is the scanner's own six-month backtest at real futures prices. The six months before it, 3 Nov 2025 to 11 May 2026, are added as a check; they use cash share prices in place of futures.
- **Models:**
  - Opus, the live model, exiting at T1
  - Opus v2 and Opus v3, exiting at T1
  - Fable and Fable-OP, exiting at T3
  - Switch-1: Fable-OP at T3, except on downtrend days, when Opus v3 at T1 is used
  - Opus v3 with a trailing stop held to the close, the exit suggested in `better_algo_for_options.md`
- **Live rule:** every model takes the first 6 signals a day that score 75 or more (Fable 80). Each trade risks Rs 15,000 in futures terms.
- **Options:** each trade buys the at-the-money call (long) or put (short) of the scanner's monthly contract, the same number of lots, and sells one minute after the futures trade exits. Option prices for May to October cannot be read any more, so they are modelled. The model was fitted on 1,960 real option exits from 21 Oct to 13 Nov 2026, and is good to about ±10%. Costs and 0.25% slippage a side are included.

## Six months, 12 May to 11 Nov 2026

| Model (exit) | Trades | Option profit (Rs) | Futures profit (Rs) | Worst day, options (Rs) | Largest fall, options (Rs) | Months in profit | Premium a trade (Rs) | Option profit as % of premium |
|---|---|---|---|---|---|---|---|---|
| Opus (T1), live | 369 | +2,45,027 | +2,50,359 | -21,222 | -28,983 | 7 of 7 | 21,533 | 3.1% |
| Opus v2 (T1) | 353 | +3,99,885 | +5,28,284 | -22,812 | -37,123 | 7 of 7 | 21,877 | 5.2% |
| Opus v3 (T1) | 335 | +4,23,981 | +5,89,038 | -18,863 | -36,768 | 7 of 7 | 21,901 | 5.8% |
| Fable (T3) | 475 | +5,70,293 | +4,73,539 | -35,551 | -72,788 | 7 of 7 | 23,459 | 5.1% |
| Fable-OP (T3) | 233 | +5,45,031 | +7,02,290 | -26,335 | -37,024 | 7 of 7 | 22,390 | 10.4% |
| **Switch-1** | 272 | **+5,82,910** | **+8,11,393** | -23,143 | **-28,584** | 7 of 7 | 22,156 | 9.7% |
| Opus v3, trailing stop to close | 335 | +5,56,102 | +7,66,300 | -18,867 | -53,487 | 7 of 7 | 21,901 | 7.6% |

### Option profit by month (Rs)

| Month (sessions) | Opus | Opus v2 | Opus v3 | Fable | Fable-OP | Switch-1 | v3 trailing |
|---|---|---|---|---|---|---|---|
| May (13, from 12 May) | +20,223 | **+50,724** | +45,167 | +11,182 | +31,038 | +31,038 | +20,874 |
| Jun (21) | +60,993 | +68,853 | **+77,820** | +28,178 | +30,956 | +23,481 | +70,402 |
| Jul (23) | +17,835 | +88,635 | +88,848 | +88,852 | **+1,78,826** | **+1,78,826** | +1,46,697 |
| Aug (21) | +31,163 | +26,753 | +27,453 | +77,121 | **+1,06,522** | **+1,06,522** | +77,620 |
| Sep (21) | +36,062 | +1,14,030 | +1,08,300 | +1,31,269 | +78,844 | +99,118 | **+1,74,999** |
| Oct (20) | +29,843 | +13,344 | +21,877 | **+72,926** | +31,702 | +56,782 | +8,373 |
| Nov (7, to 11 Nov) | +48,908 | +37,545 | +54,516 | **+1,60,764** | +87,142 | +87,142 | +57,136 |
| **Total** | +2,45,027 | +3,99,885 | +4,23,981 | +5,70,293 | +5,45,031 | **+5,82,910** | +5,56,102 |

### Futures profit by month (Rs)

| Month | Opus | Opus v2 | Opus v3 | Fable | Fable-OP | Switch-1 | v3 trailing |
|---|---|---|---|---|---|---|---|
| May | +14,731 | **+79,446** | +68,915 | -25,297 | +56,567 | +56,567 | +18,084 |
| Jun | +91,531 | +93,020 | **+1,07,734** | -47,995 | +19,065 | +6,323 | +70,150 |
| Jul | +727 | +1,11,580 | +1,16,793 | +38,839 | **+2,42,901** | **+2,42,901** | +2,13,509 |
| Aug | +35,089 | +8,708 | +15,555 | +40,120 | **+1,15,175** | **+1,15,175** | +1,00,464 |
| Sep | +37,963 | +2,00,858 | +1,93,158 | +1,62,967 | +96,500 | +1,87,449 | **+2,88,204** |
| Oct | +4,489 | -18,926 | +266 | +60,007 | +44,718 | **+75,613** | -17,489 |
| Nov | +65,829 | +53,598 | +86,618 | **+2,44,898** | +1,27,365 | +1,27,365 | +93,378 |
| **Total** | +2,50,359 | +5,28,284 | +5,89,038 | +4,73,539 | +7,02,290 | **+8,11,393** | +7,66,300 |

## The six months before: 3 Nov 2025 to 11 May 2026 (check)

No model was built on these dates. Prices are cash shares in place of futures.

| Model (exit) | Trades | Option profit (Rs) | Futures profit (Rs) | Worst day, options (Rs) | Largest fall, options (Rs) | Months in profit, options |
|---|---|---|---|---|---|---|
| Opus (T1), live | 388 | +22,835 | -1,79,918 | -25,651 | -65,258 | 3 of 7 |
| Opus v2 (T1) | 375 | +51,160 | -2,03,092 | -25,651 | -81,697 | 3 of 7 |
| Opus v3 (T1) | 366 | +84,362 | -1,28,597 | -25,651 | -63,667 | 4 of 7 |
| Fable (T3) | 503 | +7,603 | -5,26,521 | -29,675 | -1,53,041 | 4 of 7 |
| Fable-OP (T3) | 232 | +2,02,948 | +78,849 | -16,461 | -48,875 | 5 of 7 |
| **Switch-1** | 298 | **+2,67,606** | **+1,78,272** | -25,651 | -48,875 | 6 of 7 |
| Opus v3, trailing stop to close | 366 | +2,49,060 | +54,081 | -25,651 | -56,841 | 5 of 7 |

Twelve months together, option profit: Switch-1 +8,50,516; Opus v3 trailing +8,05,162; Fable-OP +7,47,979; Fable +5,77,896; Opus v3 +5,08,343; Opus v2 +4,51,045; Opus +2,67,862.

## What the comparison shows

1. **Switch-1 made the most, in options and futures, with the smallest fall from a peak.** It also came first over the six months before.
2. **In the last six months every model made money in options in every month.** The six months before were much harder: Opus, Opus v2 and Fable barely broke even in options, and all three Opus models and Fable lost money in futures.
3. **Fable looks good on the last six months but is not reliable.** It made +5.70 lakh in options, but its fall from a peak (-72,788) is twice the others', and it made only +7,603 in the six months before.
4. **The live model, Opus at T1, made the least.** It made +2.45 lakh in options against +5.83 lakh for Switch-1, and only +22,835 in the six months before.
5. **Options suit the models that hold for bigger targets.** Fable-OP and Switch-1 return about 10% of the premium paid against 3-6% for the T1 models. A bought option loses less than the future when stopped but keeps most of a big win.
6. **No single model leads every month.** Opus v2 or v3 led in May and June, Fable-OP in July and August, Opus v3 trailing in September, and Fable in October and November.

## Exit choice per model, six-month option profit (Rs)

Each model's own picks, priced with every exit rule. The current exit is marked with *.

| Model | T1 | T2 | T3 | Square off at close | T3 trailing | Close, trailing |
|---|---|---|---|---|---|---|
| Opus | +2,45,027* | +3,33,894 | +3,66,654 | +3,36,708 | +3,67,336 | +3,42,972 |
| Opus v2 | +3,99,885* | +5,50,726 | +6,11,230 | +5,83,667 | +5,96,407 | +5,81,671 |
| Opus v3 | +4,23,981* | +5,87,206 | +6,39,136 | +5,80,775 | +5,97,083 | +5,56,102 |
| Fable | +1,15,514 | +3,77,264 | +5,70,293* | +8,03,949 | +4,78,974 | +6,42,214 |
| Fable-OP | +2,83,610 | +4,53,431 | +5,45,031* | +4,63,075 | +5,09,773 | +4,93,673 |

Same table, 3 Nov 2025 to 11 May 2026:

| Model | T1 | T2 | T3 | Square off at close | T3 trailing | Close, trailing |
|---|---|---|---|---|---|---|
| Opus | +22,835* | -4,470 | -13,047 | +1,09,054 | +17,949 | +1,14,443 |
| Opus v2 | +51,160* | +55,412 | +77,819 | +2,40,210 | +90,364 | +2,14,437 |
| Opus v3 | +84,362* | +1,05,097 | +1,19,319 | +2,79,708 | +1,26,989 | +2,49,060 |
| Fable | -36,380 | -55,670 | +7,603* | +1,33,525 | +46,139 | +72,146 |
| Fable-OP | +1,17,100 | +1,68,841 | +2,02,948* | +2,97,208 | +2,09,691 | +2,93,548 |

For options, every Opus model made more in both periods by holding to the close, with or without a trailing stop, than by exiting at T1. Picking the best exit after seeing these tables overstates what it would have made, so treat the best cell in each row as an upper bound.

## Capital

Average premium is Rs 21,500 to 23,500 a trade. The most premium open at one moment over the six months was Rs 1,37,543 (Opus) to Rs 2,33,986 (Fable); Switch-1 needed Rs 1,57,276. Rs 3 lakh of premium covers every model.

## Limits

- Option prices are modelled, not real fills: no volatility skew, no real day-by-day implied volatility.
- On 12 May to 11 Nov the profit of each exit is from real futures. The minute each trade exits, which sets the option's time decay, comes from replaying it on cash one-minute prices.
- The six months before use cash share prices for both the futures and the option model.
- Several models were built on these same months, so their figures here flatter them:
  - Fable-OP was built on 12 May to 31 Aug.
  - Opus's weights were tuned on 21 Oct to 9 Nov.
  - Opus v3, Switch-1 and the trailing-stop exit were chosen after seeing the whole six months.

  The six months before are the fairer test.
- These figures replace the six-month option estimates in `options_five_scenarios.md`, which converted futures results with fixed ratios. The new figures price every trade and come out 10-30% lower.

## Files

`hunt/six_month/six_month.py` builds every number here; `six_month.json` and `six_month.log` hold the output.
