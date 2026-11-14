# MedhaSuryan (Switch-1) in the live app

MedhaSuryan is the research's Switch-1, added to the VPS app (scanner + engine) as a score model you can select. The app now offers four scores: **Opus, Opus v3, Fable-OP and MedhaSuryan**. Fable and Opus v2 were dropped (owner, 15 Nov 2026).

## How MedhaSuryan works

- **Score:** the Fable-OP score, except on days Nifty 50 opens in a downtrend, when it takes the Opus v3 score. A downtrend day is one where Nifty's last daily close is below its 20-day average, and that average is below the 50-day average. The threshold is 75.
- **Exit:** T3, and T1 on downtrend days. On a downtrend day the scanner hands the engine only T1. With the engine's exit plan set to "Hold for T3", that trade sells everything at T1, and the Telegram message says so. On other days it holds for T3.
- **Nifty trend:**
  - It is worked out once before the open from Nifty 50 daily candles (`features.nifty_regime`).
  - A failed read is retried, and is read again every 5 minutes until the scan window opens.
  - A last close older than the previous session counts as a failed read.
  - The trend is kept for the day, stored in every signal's snapshot, and shown on the Scanner page.
  - If the trend cannot be read at all, MedhaSuryan uses the Fable-OP score and T3 for that day.

## Using it

1. Settings → Scanner → "Score the scanner trades on" → MedhaSuryan.
2. Settings → Scanner → "Exit plan for scanner trades" → Hold for T3.
3. When you switch back to another score, set the exit plan back to "Sell all at T1".

## Checks

- **Tests:**
  - Scanner: 66 pass.
  - Engine: 536 pass. The 2 forecast-worker tests also fail on the unchanged code here; they need files outside the engine folder.
- **Matches the research:** over 12 May to 11 Nov 2026, the patched scanner takes the same 272 trades as Switch-1. Futures profit is +8,11,393 with its exits, and the trend labels match on all 126 days (`equiv.py`).
- **No change for the kept models:** for Opus, Opus v3 and Fable-OP, the live picks, thresholds and hand-overs to the engine match the code that was running before. That covers 27 scenarios and 146 hand-overs.
- **Independent reviews:** two, before the install.

## Files

| File | What it is |
|---|---|
| `../medhasuryan_integration.patch` | The change to the app's `scanner/` and `engine/` folders, tests included. Apply with `patch -p1` from the app's root folder. **Apply it to your own copy of the code too**: the deploy scripts copy your local folders to the VPS and would otherwise remove MedhaSuryan |
| `add_regimes.py` | Adds each stored day's Nifty trend to the scanner's two stored backtest files |
| `equiv.py` | The check against the research's Switch-1 |
| `deploy_write.py` | The server-side file update. It writes only if every file is the tested version, backs up the originals to `/opt/vitezza/backups/medhasuryan-2026-11-14/`, and has check / write / rollback modes |
| `helper.py`, `crypt.py` | The installer job. It fetches the encrypted package from this branch, checks its fingerprint, decrypts it with a key that was never stored in this repository, and runs `deploy_write.py` |
