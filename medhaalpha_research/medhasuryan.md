# MedhaSuryan

MedhaSuryan is a score model for the MedhaAlpha NSE F&O scanner (the Vitezza app on the VPS: `scanner` + `engine` services in `/opt/vitezza`). The research called it **Switch-1**.

In short, it trades Fable-OP's picks and holds them for T3. On days Nifty opens in a downtrend, it trades Opus v3's picks instead and books at T1.

Status on 15 Nov 2026:
- **Built and tested; not installed on the VPS.** The live model is still Opus v3.
- **Backtest page:** https://medhaalpha-backtest4-production.up.railway.app (Railway project `medhaalpha`, service `medhaalpha-backtest4`). It uses the medhaalpha app password.

---

## 1. The algorithm

### 1.1 Signals (unchanged scanner setups)

The scanner reads one-minute futures and cash candles for about 200 F&O stocks. New signals fire from 09:17 to 14:15 IST, one per stock, setup and day, on the first minute that every condition holds.

| Setup | Side | Conditions at the signal minute |
|---|---|---|
| A, trend breakout | Long (buy CE) | Above its 20-day average. Daily RSI(14) 50 to 65. Up 0.6% or more on the day. Above the previous day's high and above VWAP. In the top 30% of today's range. Breaking 2 or more prior bars. |
| B, breakdown | Short (buy PE) | Nifty down 0.25% or more on the day. Below its 20-day average. RSI below 50. Down 0.9% or more. Below the previous day's low and below VWAP. In the bottom 10% of today's range. Breaking 5 or more prior bars. |

### 1.2 The day's Nifty trend, known before the open

The scanner reads Nifty 50 daily closes up to the previous session before the open (scanner: `features.nifty_regime`, read at the 08:40 pre-open load). Both averages include the last close.

| Label | Rule |
|---|---|
| **Downtrend** | Last close < its 20-day average, and the 20-day average < the 50-day average |
| Uptrend | Last close > its 20-day average, and the 20-day average > the 50-day average |
| Sideways | Anything else |

If the read fails or there are fewer than 50 closes:
- the scanner tries again (3 tries at the pre-open load, then one try every 5 minutes until 09:14);
- a trend read earlier the same day is reused;
- if the trend is still unknown, the day counts as **not** a downtrend.

A last close older than the previous session counts as a failed read. Once the scan starts at 09:17, the day's trend never changes.

### 1.3 The MedhaSuryan score (0 to 100)

| Day | Score used |
|---|---|
| Not a downtrend day (Uptrend, Sideways or unknown) | **Fable-OP** |
| Downtrend day | **Opus v3** |

**Fable-OP** is a weighted average of five parts, each worth 0 to 1:

| Part | Points | Full | Nothing |
|---|---|---|---|
| Today's move in daily ATRs (day change ÷ ATR %) | 30 | 1.0 ATR | 0.25 ATR or less |
| Closed off the day's extreme (position in today's range, direction-adjusted) | 20 | 0.90 or lower | 1.0, pinned at the extreme |
| The day's extreme made just now (minutes since it, log scale) | 20 | 0 min | 15 min or more |
| Early in the session (minutes since the open, log scale) | 15 | first 5 min | after 180 min |
| Nifty flat or against the trade (Nifty's day change, direction-adjusted) | 15 | −0.2% (against) | +0.6% (with) |

**Opus v3:**
- **Long signals** take the Fable-OP score. A long whose volume so far is below normal for the time of day (rel_vol under 1) scores 0.
- **Short signals** take the Opus score:

| Opus part | Points | Full | Nothing |
|---|---|---|---|
| Move from today's open | 35 | 3% | 0% |
| Beyond VWAP | 25 | 1.5% | 0% |
| Small opening gap | 15 | no gap | 2% gap with the trade |
| RSI room (70 − RSI for longs, RSI − 30 for shorts) | 10 | 20 points of room | none |
| Stop at a real level, not the ATR fallback | 15 | real level | fallback |

### 1.4 Which signals are taken

- **Cutoff:** a MedhaSuryan score of **75** or more.
- **Daily cap:** each day, in time order, take the first **6** signals that pass. Signals in the same minute go highest score first.
- **Risk budget:** a signal is skipped (over_budget) if one futures lot would lose more than ₹15,000 at its stop. It does not use a slot.

**Choosing the cutoff:** the cutoff was chosen on 12 May to 31 Aug 2026 only and then checked on two periods it wasn't chosen on. 75 was best overall. 72.5 is a close alternative that takes a few more trades. Below 70 the drawdowns double. Above 80 there are too few trades. See `medhasuryan/cutoff/`.

### 1.5 Stop and targets (unchanged)

- **Stop:** a structural stop at the nearest support (longs) or resistance (shorts), 0.2% beyond the level. It must sit 0.3 to 0.9 daily ATR from the price; if no level fits, it goes at 0.5 ATR.
- **Targets:** R is the stop distance. **T1 = 1.0R, T2 = 1.9R, T3 = 2.6R.**

### 1.6 Exit

| Day | Exit |
|---|---|
| Not a downtrend day | Hold for **T3**, fixed stop |
| Downtrend day | Sell everything at **T1** |

How the app does it: on a downtrend day the scanner hands the engine **T1 only** (`score.handoff_targets`). With the engine's exit plan set to **Hold for T3**, a trade sells everything at the last target it holds. That means T1 on downtrend days and T3 on the rest. Telegram then says "sell all at T1: the scanner sent targets up to T1 only".

### 1.7 What is bought

| | Rule |
|---|---|
| Instrument | The **at-the-money CE** for a long or **PE** for a short, monthly expiry. Rolls to next month when 4 or fewer sessions remain. |
| Size | Lots = "Amount per scanner trade" ÷ (premium × lot size), at least 1 lot. The paper ledger sizes futures at ₹15,000 risk. |
| Order | Limit at the ask, with a safety SL at Angel. Skipped if the bid-ask gap is wider than the Settings limit (5%). |
| Holding | Carried overnight. Sold from 15:15 in the session before expiry. |
| Locks | Real orders need Settings > Scanner > "Trade the scanner's signals" **and** the server locks LIVE_TRADING_ALLOWED and SCANNER_LIVE_ALLOWED. Otherwise the engine only sends a Telegram dry run. |

---

## 2. Results

### 2.1 Same-day backtest (every trade closed at 15:29)

Options are modelled with Black-76, fitted on 1,960 real option exits, and are good to about ±10%.

| Period | Model | Trades | Options (Rs) | Futures (Rs) | Largest fall, options |
|---|---|---|---|---|---|
| 12 May-11 Nov 2026 (real futures) | **MedhaSuryan** | 272 | **+5,82,910** | **+8,11,393** | −28,584 |
| | Fable-OP (T3) | 233 | +5,45,031 | +7,02,290 | −37,024 |
| | Opus v3 (T1) | 335 | +4,23,981 | +5,89,038 | −36,768 |
| | Opus (T1), the earlier live model | 369 | +2,45,027 | +2,50,359 | −28,983 |
| 3 Nov 2025-11 May 2026 (cash prices) | **MedhaSuryan** | 298 | **+2,67,606** | **+1,78,272** | −48,875 |
| | Fable-OP (T3) | 232 | +2,02,948 | +78,849 | −48,875 |
| | Opus v3 (T1) | 366 | +84,362 | −1,28,597 | −63,667 |
| | Opus (T1) | 388 | +22,835 | −1,79,918 | −65,258 |

### 2.2 Held across days until target or stop

Futures-equivalent on cash one-minute prices, sold the session before expiry.

| Period | Model | T1 hit | T2 hit | T3 hit | Held result (Rs) |
|---|---|---|---|---|---|
| 12 May-11 Nov 2026 | **MedhaSuryan** | **69%** | **53%** | **42%** | **+13,39,773** |
| | Opus v3 | 68% | 50% | 40% | +11,11,209 |
| | Fable-OP | 66% | 49% | 40% | +9,98,378 |
| | Opus | 60% | 42% | 33% | +5,87,249 |
| 3 Nov 2025-11 May 2026 | **MedhaSuryan** | **57%** | **40%** | 31% | **+3,84,126** |
| | Fable-OP | 56% | 39% | **33%** | +2,94,227 |
| | Opus v3 | 53% | 37% | 29% | +5,808 |
| | Opus | 51% | 32% | 24% | −2,01,589 |

**How long targets take:** T1 usually comes on the entry day. T2 and T3 typically take 1 more trading day, and the slowest T3 took 11.

### 2.3 How sure

- **Built on the same data:** the switch rule was chosen after seeing 12 May to 11 Nov, so the Nov 2025 to May 2026 period is the fairer test.
- **Re-sampling the trading days:** MedhaSuryan beats Fable-OP alone 70% of the time (May–Nov) and 82% (Nov–May). It beats Opus v3 at T1 95% and 99%.
- **App code checked against the research:** over 12 May to 11 Nov, the app's code picks the same 272 trades as the research's Switch-1, with futures +8,11,393 and the same trend label on all 126 days (`medhasuryan/equiv.py`).
- **The other three models are unaffected:** with the patch, Opus, Opus v3 and Fable-OP pick the same trades and hand over the same orders as before. That covers 27 scenarios and 146 hand-overs.
- **Independent reviews:** two independent code reviews found it safe to install. Their fixes are in the patch.

---

## 3. What the patch changes in the app

The app keeps four scores: **Opus, Opus v3, Fable-OP and MedhaSuryan**. Fable and Opus v2 are removed (owner, 15 Nov 2026). A saved choice of a removed score falls back to Opus v3.

| Service | Changes |
|---|---|
| scanner | `score.py`: four models, `medhasuryan_score`, `handoff_targets`. `features.py`: `nifty_regime` and the trend in every snapshot. `engine.py`: pre-open Nifty read, retries, keeps the day's trend, T1-only hand-over. `backtest.py`: stored days. `config.py`: `medhasuryan_min_score` 75, `regime_days`, `regime_retry_s`. Tests. |
| engine | Settings choices and "MedhaSuryan score needed". `/internal/settings`. Scanner page: score column, Nifty trend line, Rules cards. `scanner_trade.py`: plan wording when fewer targets are sent. Tests. |
| stored reports | Each stored day gains `nifty_regime`, so stored backtest pages show MedhaSuryan's real picks. Applied by `apply_report_regimes.py`. |

Tests: scanner 66 pass. Engine 536 pass. The 2 forecast-worker tests need the `forecast-worker` folder next to `engine`, and fail without it on the unchanged code too.

---

## 4. Install on the VPS from your laptop

Do this after 15:30 IST or at the weekend. The engine restarts in a few seconds; SL orders at Angel stay in place.

**0. Start from the VPS version of 14 Nov 2026.** The patch was built on the VPS code with Opus v3 as the default. If your laptop copy differs, take the VPS copy first, e.g. `scp -r root@<vps>:/opt/vitezza/engine root@<vps>:/opt/vitezza/scanner .`, using the host and key from `deploy/push-engine.ps1`. Keep a zip of `engine/` and `scanner/` as your rollback.

**1. Get the files** from GitHub `niithinlk-hub/indian_breakout_scanner`, branch `claude/cool-cannon-2qua2u`:
- `medhaalpha_research/medhasuryan_integration.patch`
- `medhaalpha_research/medhasuryan/apply_report_regimes.py`
- `medhaalpha_research/medhasuryan/report_regimes.json`

**2. Apply the patch** in the app folder (the one holding `engine/` and `scanner/`). In Git Bash:
```
git apply --check -p1 --ignore-whitespace medhasuryan_integration.patch   # must print nothing
git apply -p1 --ignore-whitespace medhasuryan_integration.patch
```
`scanner/scanner/equity/features.py` has Windows line endings, hence `--ignore-whitespace`. `patch -p1 < medhasuryan_integration.patch` also works.

**3. Add the trend to the stored reports:**
```
python apply_report_regimes.py <app folder>
```
It prints `updated` twice. It changes nothing if the reports are not the 14 Nov versions.

**4. Run the tests:**
```
cd scanner && python -m pytest -q      # 66 passed
cd ../engine && python -m pytest -q    # 536 passed
```

**5. Copy both services and rebuild them together.** Deploy the scanner and the engine at the same time. With a new engine and the old scanner, picking MedhaSuryan would run Opus v3 with "Hold for T3". From the app folder, in Git Bash:
```
tar -czf medhasuryan.tgz --exclude=.venv --exclude=__pycache__ --exclude=.pytest_cache --exclude=.omc engine scanner
scp -i ~/.ssh/vitezza_vps medhasuryan.tgz root@<vps>:/tmp/
ssh -i ~/.ssh/vitezza_vps root@<vps> 'set -e; cd /opt/vitezza; b=backups/pre-medhasuryan-$(date +%Y%m%d); mkdir -p $b; cp -a engine scanner $b/; tar -xzf /tmp/medhasuryan.tgz; rm -f /tmp/medhasuryan.tgz; docker compose up -d --build scanner engine; sleep 10; docker compose logs --tail 30 scanner engine'
```

**6. Check it worked:**
- **Settings > Scanner** offers Opus, Opus v3, Fable-OP and MedhaSuryan, with "MedhaSuryan score needed" set to 75.
- **Scanner > Rules** shows the Opus v3 and MedhaSuryan cards.
- **Scanner > Signals**, after 08:40 IST on the next trading day, shows "Nifty before the open: …".

**7. Switch MedhaSuryan on:**
1. Settings > Scanner > "Score the scanner trades on" → **MedhaSuryan**.
2. "MedhaSuryan score needed" → **75**.
3. "Exit plan for scanner trades" → **Hold for T3**.

**8. Switch back or roll back:**
- **Leave MedhaSuryan:** pick the other score, and set the exit plan back to **Sell all at T1**. There is one exit plan for all scores.
- **Remove the code:** restore `/opt/vitezza/backups/pre-medhasuryan-<date>/engine` and `scanner`, then run `docker compose up -d --build scanner engine`.

**Keep your laptop copy patched.** `deploy/push-engine.ps1` copies your laptop's `engine` folder to the VPS. An unpatched copy would remove MedhaSuryan from the engine.

---

## 5. Known limits

- **One exit plan for all scores.** MedhaSuryan needs "Hold for T3"; the other three scores were tested at T1.
- **Trend read failure before the scan:** if the Nifty trend cannot be read before 09:14, MedhaSuryan uses Fable-OP and all three targets that day. A restart later that day that does read the trend switches the rest of the day to Opus v3 with T1 only.
- **`EQ_SCORE_MODEL` set to a removed score** (only if someone sets it in `.env`; it isn't set now) falls back to Opus, not Opus v3.
- **Backtest figures are estimates:**
  - option figures are modelled;
  - the Nov 2025 to May 2026 period and all held results use cash prices in place of futures;
  - the held backtest gives the same target or stop outcome as real futures about 9 times in 10.
- **Real orders differ from the backtest:** they size by rupee amount, not by ₹15,000 risk, and carry trades overnight.

---

## 6. Files

All under `medhaalpha_research/` on branch `claude/cool-cannon-2qua2u`.

| Path | What |
|---|---|
| `medhasuryan.md` | This document |
| `medhasuryan_integration.patch` | The app change, tests included |
| `medhasuryan/apply_report_regimes.py`, `report_regimes.json` | Adds the trend to the two stored reports |
| `medhasuryan/equiv.py` | The check that the app's code matches the research's Switch-1 |
| `medhasuryan/held4.py`, `bt4.json`, `site/` | Held backtest of the four models and the Railway page's source |
| `medhasuryan/cutoff/` | Cutoff grid, 55 to 90 |
| `six_month_comparison.md`, `t1_t2_t3_timing_21Oct-13Nov.md`, `better_algo_for_options.md` | The research reports behind it |
| `hunt/` | Test bench, option model and the methods tried |

---

## 7. Notes for Claude (recall)

- **Names:** MedhaSuryan is the research's Switch-1. The model key in code is `medhasuryan`; its label is MedhaSuryan.
- **Rule:** the Fable-OP score, or Opus v3 on Nifty downtrend days (prev close < MA20 < MA50, averages include the prev close). Cutoff 75. First 6 a day. Exit T3, or T1 on downtrend days.
- **The VPS runs real money.**
  - Never change the live score model or the server locks without the owner's explicit go-ahead.
  - Never print or reuse values from `/opt/vitezza/.env`.
  - Deploy only after 15:30 IST or at weekends, scanner and engine together.
- **The engine and scanner source stay out of public repositories.** Only patches and research data are on the public branch.
- **Railway:** the existing `medhaalpha` app was uploaded from a computer, so its source isn't on GitHub. Read only Railway variable names, never their values.
