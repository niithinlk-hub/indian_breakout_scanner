# Opus v3: test on unseen dates. Rules fixed before the run

Written 14 Nov 2026 01:59 IST, before any result for dates earlier than 12 May 2026 was computed.

## Why a stand-in is needed

Real futures candles before mid-May 2026 cannot be read by anyone: Upstox keeps expired contracts for six months only (its own documentation: "up to six months of historical expiries"). That is why the scanner's own backtest starts on 12 May. So the test uses the scanner's replay run on each stock's cash share instead of its future (the "stand-in").

## What is tested

- Dates: every session from 3 Nov 2025 to 11 May 2026. Nothing in any model was fitted on these dates: Opus was tuned on 21 Oct - 9 Nov 2026, Fable-OP on 12 May - 31 Aug 2026, and Opus v2 and v3 were chosen on 12 May - 11 Nov 2026.
- Models, frozen: Opus (cut 75), Fable-OP (75), Opus v2 (long needs Fable-OP 75, short needs Opus 75), Opus v3 (v2, and a long needs relative volume of 1 or more). Code fingerprint of the patched score file: 9a53572f4d54a7d8. Replay script: 7d89cd5bd2d86e10. Evaluation script: cfb48a00b5310f5d.
- Rule: setups A and B, first 6 qualifying signals a day, same-day exit at T1, lots sized to Rs 15,000 risk, usual charges and slippage. No cut-off or setting is changed for the stand-in.
- Stocks: one fixed list of 199 (every stock with a signal in the scanner's file by 30 June 2026), used for every day.

## How good the stand-in is (measured on the known months, 12 May - 19 Oct 2026, 111 sessions)

| | Real futures | Cash stand-in |
|---|---|---|
| Opus: trades, reached T1, net | 316, 35.8 %, +2,11,138 | 315, 32.4 %, +1,05,459 |
| Opus v3: trades, reached T1, net | 284, 50.0 %, +5,04,339 | 299, 40.5 %, +1,52,729 |
| v3 minus Opus, reached T1 | +14.2 points | +8.1 points |
| v3 minus Opus, net | +2,93,201 | +47,270 |
| Months in which v3 reached T1 more often than Opus | 6 of 6 | 6 of 6 |
| Months in which the net difference has the same sign as the real one | - | 4 of 6 |

So the stand-in keeps the direction of the reach-T1 result at a little over half its size, and is too noisy to judge profit. It is a conservative test: it tends to understate v3.

## Pass rule

Main test: on the unseen dates, v3 reaches T1 more often than Opus. Days are resampled 20,000 times; the test passes if v3 is ahead in at least 95 % of resamples.

Also reported, whatever they show:
1. Net at T1, v3 against Opus (share of resamples in which v3 is ahead).
2. Trade count: v3 at least 85 % of Opus's.
3. Side structure: Opus's shorts against its longs; Fable-OP's longs against Opus's longs.
4. The volume condition: among longs scoring 75 or more on Fable-OP, those with relative volume under 1 against the rest.
5. v3 against v2, stop-out rates, and month-by-month figures.

If the main test fails, the report will say so.
