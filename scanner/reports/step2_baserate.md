# Step 2: base-rate study (benchmark a)

Generated 2026-09-26 19:49 UTC, git `debb9f1`, config `b2080aab7cb6`, data to 2026-09-25, signal dates 2017-09-27 to 2026-09-25. Reproduce: `python -m nsescan baserate`.

**Question:** if you buy a random liquid name on a random day and manage it with the section-4 exits, costs and slippage, what happens? Anything the strategy claims later has to beat this, out of sample.

## Definition

* Entries: every (symbol, day T) that passes data QA and the segment's liquidity gate on T, which is the exact expectation of uniformly random entry dates. No other gate.
* Entry at the T+1 open; stop = min(low of T, lowest low of the 5 sessions before T), with day T standing in for the breakout day. Skipped when the stop is more than 8% below the close (and again vs the fill).
* Exits as in section 4: stop (at the stop, or the open on a gap); breakeven from the session after +10%; sell 50% at +15% and trail the rest on a close below EMA10; stall exit if below +3% after 7 sessions; time exit at the close of session 20. **Failed-breakout exit not applied: a random entry has no pivot.** Same-bar stop/target ties go to the stop.
* Costs (ASSUMPTIONS): 0.25% round trip; slippage per side N500 0.10%, MICRO250 0.25%.
* Label: triple barrier, upper +15%, lower = stop, vertical 20 sessions. "Touched +15%" ignores the stop.
* CIs: 95% percentile bootstrap resampling calendar months (trades in the same month move together).

## Bottom line

After costs, a random liquid entry managed with these exits has **negative expectancy**. N500: -0.163R (-0.20%) per trade, 95% CI [-0.254, -0.068] R, negative in R (CI below zero); the % CI includes zero. MICRO250: -0.296R (-0.61%), CI [-0.395, -0.194] R, negative in R and in %, both CIs below zero. Before costs: N500 +0.25%, MICRO250 +0.14% per trade. +15% is reached before the stop on 9.7% (N500) and 12.8% (MICRO250) of entries; ignoring the stop, the high touches +15% within 20 sessions on 15.5% and 22.5%. These are the numbers the strategy has to beat out of sample, after costs.

## Headline, by segment

| segment | trades | win rate | avg win R | avg loss R | expectancy R | 95% CI (R) | profit factor | avg sessions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N500 | 507887 | 28.0% | 2.172 | -1.070 | -0.163 | [-0.254, -0.068] | 0.900 | 7.000 |
| MICRO250 | 184937 | 22.5% | 2.493 | -1.107 | -0.296 | [-0.395, -0.194] | 0.747 | 6.305 |

| segment | expectancy % | 95% CI (%) | gross % (pre-cost) | median stop | +15% before stop | 95% CI | stop first | touched +15% in 20 sessions |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N500 | -0.20% | [-0.45%, +0.07%] | 0.25% | 3.1% | 9.7% | [+8.61%, +10.92%] | 69.9% | 15.5% |
| MICRO250 | -0.61% | [-0.91%, -0.30%] | 0.14% | 3.3% | 12.8% | [+11.36%, +14.40%] | 74.6% | 22.5% |

Entries per month average 4660 (N500) and 1697 (MICRO250): every eligible name-day, not a signal count. Profit factor is on % returns, equal weight per trade.

Exit mix:

| exit | N500 | MICRO250 |
| --- | --- | --- |
| STOP | 52.9% | 58.3% |
| STALL | 26.8% | 21.7% |
| TIME | 11.3% | 7.9% |
| TRAIL_EMA | 3.8% | 5.8% |
| STOP_GAP | 2.7% | 2.6% |
| BREAKEVEN_STOP | 2.2% | 3.4% |
| BREAKEVEN_STOP_GAP | 0.2% | 0.3% |

Entries considered and skipped:

| count | N500 | MICRO250 |
| --- | --- | --- |
| entries_considered | 625838 | 249435 |
| closed | 507887 | 184937 |
| open_censored | 2040 | 1033 |
| stop_too_wide | 85036 | 47589 |
| open_at_or_below_stop | 15955 | 6325 |
| stop_too_wide_at_entry | 13843 | 8842 |
| stop_not_below_close | 657 | 516 |
| no_entry_bar_yet | 420 | 193 |

## MFE / MAE (closed trades, % from fill and in R)

| segment | metric | p10 | p25 | p50 | p75 | p90 |
| --- | --- | --- | --- | --- | --- | --- |
| N500 | mfe_pct | -0.1% | +0.1% | +2.0% | +5.3% | +12.8% |
| N500 | mae_pct | -4.9% | -3.4% | -2.0% | -1.1% | -0.6% |
| N500 | mfe_r | -0.09 | +0.02 | +0.55 | +1.71 | +4.06 |
| N500 | mae_r | -1.00 | -1.00 | -1.00 | -0.55 | -0.25 |
| MICRO250 | mfe_pct | -0.2% | -0.2% | +1.8% | +5.9% | +14.9% |
| MICRO250 | mae_pct | -5.4% | -3.8% | -2.4% | -1.3% | -0.7% |
| MICRO250 | mfe_r | -0.19 | -0.06 | +0.49 | +1.73 | +4.25 |
| MICRO250 | mae_r | -1.00 | -1.00 | -1.00 | -0.66 | -0.31 |

## By stop distance (stop below the fill)

| segment | stop_bucket | trades | win rate | avg win R | avg loss R | expectancy R | expectancy % | PF | +15% first | touched +15% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MICRO250 | 0-1% | 15709 | 5.6% | 12.418 | -1.795 | -1.002 | -0.67% | 0.406 | 2.8% | 18.7% |
| MICRO250 | 1-2% | 35082 | 12.5% | 5.218 | -1.329 | -0.508 | -0.73% | 0.575 | 6.3% | 20.2% |
| MICRO250 | 2-3% | 33351 | 19.9% | 3.213 | -1.134 | -0.270 | -0.66% | 0.706 | 10.6% | 22.0% |
| MICRO250 | 3-4% | 28404 | 25.1% | 2.229 | -0.997 | -0.188 | -0.65% | 0.750 | 13.3% | 22.5% |
| MICRO250 | 4-5% | 23934 | 28.9% | 1.736 | -0.900 | -0.138 | -0.62% | 0.784 | 16.1% | 23.6% |
| MICRO250 | 5-6% | 20023 | 31.6% | 1.501 | -0.809 | -0.079 | -0.43% | 0.857 | 19.1% | 25.2% |
| MICRO250 | 6-8% | 28434 | 33.1% | 1.209 | -0.700 | -0.069 | -0.46% | 0.856 | 21.1% | 25.3% |
| N500 | 0-1% | 58037 | 8.0% | 10.277 | -1.714 | -0.760 | -0.40% | 0.556 | 2.2% | 12.6% |
| N500 | 1-2% | 97293 | 18.2% | 4.153 | -1.227 | -0.248 | -0.35% | 0.764 | 5.3% | 13.7% |
| N500 | 2-3% | 92205 | 27.4% | 2.443 | -1.059 | -0.100 | -0.25% | 0.871 | 8.2% | 14.5% |
| N500 | 3-4% | 78902 | 32.8% | 1.746 | -0.931 | -0.052 | -0.18% | 0.918 | 10.6% | 15.3% |
| N500 | 4-5% | 64077 | 35.9% | 1.405 | -0.820 | -0.022 | -0.09% | 0.961 | 12.7% | 16.5% |
| N500 | 5-6% | 50813 | 38.2% | 1.176 | -0.733 | -0.004 | -0.02% | 0.992 | 14.6% | 17.6% |
| N500 | 6-8% | 66560 | 39.4% | 0.977 | -0.628 | 0.004 | 0.03% | 1.011 | 17.0% | 19.4% |

R-expectancy is driven by how close the stop is. With the stop within 1-2% of the fill, the round-trip cost and slippage alone are a large fraction of 1R and ordinary noise hits the stop, so R collapses even though the %-expectancy barely changes across buckets. The section-4 stop has a maximum (8%) but no minimum, and tight bases produce tight stops, so the same effect will hit the strategy. **Open question for you:** add a minimum stop distance (e.g. 1x ATR(14) or a fixed %)? Not changed without your decision.

## By year

| segment | year | trades | win rate | avg win R | avg loss R | expectancy R | expectancy % | PF | +15% first | touched +15% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MICRO250 | 2017 | 2565 | 34.2% | 2.491 | -1.020 | 0.179 | 0.84% | 1.424 | 20.2% | 34.2% |
| MICRO250 | 2018 | 8999 | 17.4% | 2.190 | -1.104 | -0.530 | -1.47% | 0.448 | 8.2% | 15.1% |
| MICRO250 | 2019 | 5299 | 20.6% | 2.674 | -1.133 | -0.351 | -0.72% | 0.704 | 12.1% | 20.5% |
| MICRO250 | 2020 | 7910 | 27.0% | 2.904 | -1.046 | 0.021 | 0.16% | 1.065 | 19.5% | 32.9% |
| MICRO250 | 2021 | 17645 | 27.4% | 2.756 | -1.037 | 0.001 | 0.15% | 1.067 | 18.8% | 29.0% |
| MICRO250 | 2022 | 19883 | 23.3% | 2.280 | -1.087 | -0.303 | -0.74% | 0.691 | 11.9% | 19.6% |
| MICRO250 | 2023 | 26254 | 30.0% | 2.500 | -1.053 | 0.014 | 0.34% | 1.172 | 15.7% | 24.4% |
| MICRO250 | 2024 | 32138 | 20.9% | 2.429 | -1.109 | -0.370 | -0.80% | 0.684 | 12.3% | 23.5% |
| MICRO250 | 2025 | 36806 | 17.9% | 2.276 | -1.156 | -0.543 | -1.36% | 0.473 | 8.3% | 15.9% |
| MICRO250 | 2026 | 27438 | 19.6% | 2.660 | -1.158 | -0.410 | -0.75% | 0.703 | 12.3% | 25.4% |
| N500 | 2017 | 9591 | 32.9% | 2.139 | -1.012 | 0.024 | 0.22% | 1.133 | 9.1% | 15.1% |
| N500 | 2018 | 34965 | 23.6% | 1.873 | -1.061 | -0.368 | -0.92% | 0.566 | 5.6% | 9.3% |
| N500 | 2019 | 33230 | 27.0% | 1.988 | -1.078 | -0.251 | -0.40% | 0.785 | 7.0% | 11.6% |
| N500 | 2020 | 30814 | 32.2% | 2.526 | -1.033 | 0.115 | 0.62% | 1.315 | 16.1% | 24.8% |
| N500 | 2021 | 50071 | 31.5% | 2.328 | -1.014 | 0.038 | 0.30% | 1.158 | 13.2% | 19.7% |
| N500 | 2022 | 55284 | 28.0% | 1.996 | -1.058 | -0.202 | -0.32% | 0.842 | 9.1% | 13.1% |
| N500 | 2023 | 69147 | 36.7% | 2.264 | -1.032 | 0.177 | 0.71% | 1.455 | 11.9% | 17.1% |
| N500 | 2024 | 76993 | 26.2% | 2.221 | -1.061 | -0.202 | -0.27% | 0.868 | 10.9% | 18.1% |
| N500 | 2025 | 86050 | 24.7% | 2.080 | -1.114 | -0.325 | -0.72% | 0.646 | 6.7% | 11.4% |
| N500 | 2026 | 61742 | 22.3% | 2.145 | -1.134 | -0.404 | -0.63% | 0.698 | 8.2% | 15.8% |

## By regime (state on signal day T)

| segment | regime | trades | win rate | avg win R | avg loss R | expectancy R | expectancy % | PF | +15% first | touched +15% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MICRO250 | NEUTRAL | 38706 | 20.0% | 2.441 | -1.128 | -0.416 | -0.87% | 0.650 | 11.3% | 21.9% |
| MICRO250 | RISK_OFF | 45890 | 22.4% | 2.619 | -1.135 | -0.296 | -0.49% | 0.800 | 13.0% | 25.1% |
| MICRO250 | RISK_ON | 100250 | 23.6% | 2.449 | -1.086 | -0.252 | -0.57% | 0.758 | 13.2% | 21.6% |
| MICRO250 | UNDEFINED | 91 | 67.0% | 4.531 | -1.202 | 2.641 | 7.89% | 11.110 | 48.4% | 64.8% |
| N500 | NEUTRAL | 100832 | 26.2% | 2.157 | -1.089 | -0.239 | -0.35% | 0.826 | 9.1% | 15.6% |
| N500 | RISK_OFF | 128090 | 27.3% | 2.406 | -1.114 | -0.155 | -0.10% | 0.952 | 10.4% | 17.8% |
| N500 | RISK_ON | 278650 | 28.9% | 2.073 | -1.043 | -0.142 | -0.19% | 0.902 | 9.6% | 14.3% |
| N500 | UNDEFINED | 315 | 52.4% | 3.569 | -1.197 | 1.300 | 3.51% | 5.791 | 18.4% | 32.7% |

UNDEFINED = the first year of data, before the VIX percentile has 252 sessions of history.

## Eligible names per day (QA + liquidity), yearly average

| year | N500 | MICRO250 |
| --- | --- | --- |
| 2017 | 172 | 55 |
| 2018 | 171 | 49 |
| 2019 | 159 | 28 |
| 2020 | 171 | 50 |
| 2021 | 250 | 98 |
| 2022 | 276 | 107 |
| 2023 | 331 | 135 |
| 2024 | 398 | 181 |
| 2025 | 416 | 192 |
| 2026 | 431 | 211 |

## Sensitivity: trades spanning a >25% single-day move

| segment | trades spanning a >25% day | remaining | expectancy R | expectancy % | win rate | +15% first |
| --- | --- | --- | --- | --- | --- | --- |
| N500 | 145 | 507742 | -0.164 | -0.20% | 28.0% | 9.7% |
| MICRO250 | 46 | 184891 | -0.292 | -0.60% | 22.5% | 12.8% |

The headline keeps these trades (the conservative choice). Some are real crashes, others are unadjusted demergers where the "loss" was paid out as shares of the new company.

## Caveats

* Survivorship: today's constituents only. Names that fell out of the indices or delisted are missing, so these base rates are **optimistic**, MICRO250 most of all.
* The liquidity floors are nominal rupees, so far fewer names qualify in 2017-2020; the early years carry less weight and a different mix.
* Costs and slippage are assumptions, not measurements.
* This is benchmark (a) only. Benchmark (b) (naive momentum), (c) (Nifty 500 buy-and-hold, portfolio level) and portfolio CAGR / drawdown come with the step-4 backtest.
