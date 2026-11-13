# Forward test: rules fixed before the first session

Written 14 Nov 2026 02:24 IST. First session counted: 16 Nov 2026.

## What runs

After each market close, the scanner's own replay (a frozen patched copy; fingerprint of its score file: 9a53572f4d54a7d8) is run on that day's real futures candles, and each picked trade's option is priced on its real option candles. No setting changes during the test.

- Five models: Opus, Fable, Fable-OP, Opus v2, Opus v3. Each takes the first 6 signals a day at or above its own cut-off (Opus 75, Fable 80, Fable-OP 75, v2 75, v3 75), setups A and B.
- Same-day exit. Opus, Opus v2 and Opus v3 are judged at T1; Fable and Fable-OP at T3.
- Futures: lots sized to Rs 15,000 risk, charges and 0.02 % slippage a side. Options: the monthly option nearest the signal price, same lots, bought at the entry minute and sold when the futures leg exits, charges and 0.25 % slippage a side.

## What counts as proof of profit

Checked after 20, 40 and 60 sessions. Days are resampled 20,000 times.

- A model is **shown profitable** when, with at least 40 sessions, its options net is above zero in at least 90 % of resamples.
- Opus v3 is **shown better than Opus** when, with at least 40 sessions, its options net is ahead of Opus's in at least 90 % of resamples. The same test is reported against Fable-OP.
- Futures figures are reported beside the option figures throughout.
- Before 40 sessions the report says "too early" whatever the numbers look like.

Everything is reported, including if a model fails.
