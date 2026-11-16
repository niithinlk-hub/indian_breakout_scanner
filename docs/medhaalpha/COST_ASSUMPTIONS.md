# MEDHAALPHA — cost and market-structure assumptions

Window: 18 Nov 2024 – 13 Nov 2026. Account: Upstox Basic plan (retail). Each rate below was
researched and then re-checked by an independent verifier against primary sources (NSE circulars,
Finance Acts, NSE stamp-duty page, broker charge pages) in November 2026.

## Cash equity (per executed order / per side)

| Item | Intraday (MIS) | Delivery (CNC) | Source / note |
|---|---|---|---|
| Brokerage | min(₹20, 0.05% of order) until 14 Mar 2025; min(₹20, 0.1%) from 15 Mar 2025 | ₹20 per order | Upstox repricing 15 Mar 2025 (start date medium confidence) |
| STT | 0.025% of sell value | 0.1% of buy and sell value | Unchanged by Finance (No.2) Act 2024 and Finance Act 2026 |
| NSE transaction charge (incl. IPFT) | 0.00307% each side | 0.00307% each side | NSE/FA/73061: split changed 1 Mar 2026, total unchanged |
| SEBI turnover fee | ₹10 per crore each side | same | GST applies |
| Stamp duty | 0.003% of buy value | 0.015% of buy value | Indian Stamp Act (from 1 Jul 2020) |
| GST | 18% on brokerage + exchange + SEBI fee (+ DP) | same | not on STT/stamp |
| DP charge | — | ₹18.50 + GST until ~14 Mar 2025, ₹20 + GST after, per scrip per sell day | Upstox charges page |

Upstox API orders were billed a promotional flat ₹10 from 1 Aug 2025 (validity extended to 31 Dec
2026). The backtest keeps the standard ₹20 (conservative).

## Stock options (premium based, per side)

| Item | Rate |
|---|---|
| Brokerage | ₹20 per executed order (per leg) |
| STT on sell | 0.1% of premium (1 Oct 2024 – 31 Mar 2026); **0.15% from 1 Apr 2026** (Finance Act 2026, NSE/FATAX/73524) |
| STT on exercise | 0.125% → 0.15% of intrinsic value from 1 Apr 2026 (not incurred: positions close before expiry) |
| NSE transaction charge (incl. IPFT) | 0.03553% of premium each side |
| Stamp duty | 0.003% of premium (buy) |
| SEBI fee, GST | as above |

## Slippage and spreads (modelled)

* Equities: 5 bps per side on top of the simulated fill, +3 bps extra when a stop is hit; a stress
  case doubles both.
* Options: half-spread of 1% of premium per side (2.5% if the contract traded under 200 lots the
  prior session), never less than one ₹0.05 tick, on every leg.

## Session and broker rules used

* New intraday entries 09:30–14:45 (blueprint). Flat time: close of the bar ending 15:10 until
  31 Jul 2026, 15:00 from 3 Aug 2026. Reason: Upstox auto-squares-off MIS positions at 15:15 (until
  Jun 2026), and after NSE launched the closing-auction session for F&O stocks on 3 Aug 2026
  (continuous trading ends 15:15) at 15:05, later 15:10.
* MIS leverage up to 5× (20% margin floor under SEBI peak-margin rules); intraday shorting allowed,
  no overnight equity shorts.
* Stock F&O expiry: last Thursday until Aug 2025, last Tuesday from Sep 2025 (SEBI circular of
  26 May 2025). Stock derivatives are physically settled; Upstox blocks fresh positions in the
  expiring contract from the Monday of expiry week. The options module only uses expiries ≥ 7
  (intraday) / ≥ 14 (positional) calendar days away.
* Lot sizes come from each day's F&O bhavcopy (point in time). Contract values sit in the
  ₹5–10 lakh band (the ₹15 lakh minimum of Nov 2024 applies to index derivatives only).
* From 1 Apr 2026 retail API order placement requires a broker-registered static IP and other
  SEBI retail-algo framework controls (relevant to paper/live phases, not to the backtest).
