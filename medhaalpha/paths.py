from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.environ.get("MEDHAALPHA_DATA_DIR", REPO_ROOT / "data" / "medhaalpha"))
RAW_DIR = DATA_DIR / "raw"
BHAV_DIR = DATA_DIR / "bhav"
CANDLE_DIR = DATA_DIR / "candles"
RESULTS_DIR = DATA_DIR / "results"

for _p in (DATA_DIR, RAW_DIR, BHAV_DIR, CANDLE_DIR, RESULTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)
