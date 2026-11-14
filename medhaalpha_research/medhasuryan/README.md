# MedhaSuryan files

Start with `../medhasuryan.md`: the algorithm, the results, and how to install it on the VPS from your laptop.

| File | What it is |
|---|---|
| `../medhasuryan_integration.patch` | The app change (scanner + engine, tests included). Apply with `git apply -p1 --ignore-whitespace` from the app folder that holds `engine/` and `scanner/` |
| `apply_report_regimes.py`, `report_regimes.json` | Adds each stored day's Nifty trend to the scanner's two stored backtest reports; checks the files by SHA-256 before and after |
| `equiv.py` | Checks the patched scanner against the research's Switch-1 (272 of 272 trades, futures +8,11,393, trend labels 126 of 126) |
| `add_regimes.py` | How `report_regimes.json` was made (the scanner's own `nifty_regime` on Nifty 50 daily closes) |
| `deploy_write.py` | A checked file-update script (check / write / rollback) from the first install attempt; not needed for the laptop install |
| `held4.py`, `held4.log`, `bt4.json` | Held-across-days backtest of the four models (T1/T2/T3 hits and days), and the data for the Railway page |
| `site/` | Source of the Railway backtest page (`server.ts` = `page.html` + `server_tail.ts`) |
| `cutoff/` | MedhaSuryan score cutoff grid, 55 to 90 |
