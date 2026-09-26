"""Local parquet store with the same tables as Supabase.

Used for development, for backtests (the full 10-year panel is read from here), and
as the working copy until the Supabase project exists. `nsescan sync` pushes it to
Supabase and `nsescan pull` refreshes it from Supabase.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger(__name__)

PRICE_COLUMNS = ["symbol", "date", "open", "high", "low", "close", "volume"]


class LocalStore:
    kind = "local"

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- helpers ---------------------------------------------------------
    def _path(self, table: str) -> Path:
        return self.root / f"{table}.parquet"

    def _read(self, table: str) -> pd.DataFrame | None:
        path = self._path(table)
        return pd.read_parquet(path) if path.exists() else None

    def _write(self, table: str, frame: pd.DataFrame) -> None:
        tmp = self._path(table).with_suffix(".tmp")
        frame.to_parquet(tmp, index=False)
        tmp.replace(self._path(table))

    # ---- universe ----------------------------------------------------------
    def upsert_universe(self, universe: pd.DataFrame) -> None:
        """Insert/refresh current constituents; symbols no longer listed become inactive."""

        existing = self._read("universe")
        current = universe.copy()
        if existing is not None and not existing.empty:
            kept_added = existing.set_index("symbol")["added_at"]
            current["added_at"] = current["symbol"].map(kept_added).fillna(current["added_at"])
            dropped = existing.loc[~existing["symbol"].isin(current["symbol"])].copy()
            dropped["active"] = False
            current = pd.concat([current, dropped], ignore_index=True)
        self._write("universe", current.sort_values(["segment", "symbol"]).reset_index(drop=True))

    def read_universe(self, active_only: bool = True) -> pd.DataFrame:
        frame = self._read("universe")
        if frame is None:
            raise FileNotFoundError("universe not loaded; run `python -m nsescan universe`")
        return frame.loc[frame["active"]].reset_index(drop=True) if active_only else frame

    # ---- prices --------------------------------------------------------------
    def upsert_prices(self, rows: pd.DataFrame, replace_symbols: list[str] | None = None) -> int:
        """Upsert (symbol, date) rows. Symbols in `replace_symbols` have their history replaced."""

        rows = rows[PRICE_COLUMNS].copy()
        rows["date"] = pd.to_datetime(rows["date"]).dt.normalize()
        existing = self._read("prices_daily")
        if existing is not None and not existing.empty:
            if replace_symbols:
                existing = existing.loc[~existing["symbol"].isin(replace_symbols)]
            combined = pd.concat([existing, rows], ignore_index=True)
        else:
            combined = rows
        combined = combined.drop_duplicates(subset=["symbol", "date"], keep="last")
        combined["volume"] = combined["volume"].astype("Int64")
        self._write("prices_daily", combined.sort_values(["symbol", "date"]).reset_index(drop=True))
        return len(rows)

    def read_prices(self, symbols: list[str] | None = None, start: str | None = None) -> pd.DataFrame:
        frame = self._read("prices_daily")
        if frame is None:
            return pd.DataFrame(columns=PRICE_COLUMNS)
        if symbols is not None:
            frame = frame.loc[frame["symbol"].isin(symbols)]
        if start is not None:
            frame = frame.loc[frame["date"] >= pd.Timestamp(start)]
        return frame.reset_index(drop=True)

    def last_price_dates(self) -> pd.Series:
        frame = self._read("prices_daily")
        if frame is None or frame.empty:
            return pd.Series(dtype="datetime64[ns]")
        return frame.groupby("symbol")["date"].max()

    # ---- benchmarks --------------------------------------------------------------
    def upsert_benchmarks(self, rows: pd.DataFrame) -> None:
        rows = rows[["ticker", "date", "close"]].copy()
        rows["date"] = pd.to_datetime(rows["date"]).dt.normalize()
        existing = self._read("benchmarks_daily")
        combined = rows if existing is None else pd.concat([existing, rows], ignore_index=True)
        combined = combined.drop_duplicates(subset=["ticker", "date"], keep="last")
        self._write("benchmarks_daily", combined.sort_values(["ticker", "date"]).reset_index(drop=True))

    def read_benchmarks(self) -> pd.DataFrame:
        frame = self._read("benchmarks_daily")
        return frame if frame is not None else pd.DataFrame(columns=["ticker", "date", "close"])

    # ---- QA / regime ---------------------------------------------------------------
    def replace_data_quality(self, issues: pd.DataFrame) -> None:
        self._write("data_quality", issues.reset_index(drop=True))

    def read_data_quality(self) -> pd.DataFrame:
        frame = self._read("data_quality")
        return frame if frame is not None else pd.DataFrame()

    def upsert_regime(self, regime: pd.DataFrame) -> None:
        existing = self._read("regime_daily")
        combined = regime if existing is None else pd.concat([existing, regime], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last").sort_values("date")
        self._write("regime_daily", combined.reset_index(drop=True))

    def read_regime(self) -> pd.DataFrame:
        frame = self._read("regime_daily")
        return frame if frame is not None else pd.DataFrame()

    # ---- run logs ----------------------------------------------------------------------
    def log_scan_run(self, record: dict[str, Any]) -> None:
        record = {"logged_at": datetime.now(timezone.utc).isoformat(), **record}
        with (self.root / "scan_runs.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, default=str) + "\n")

    def save_backtest_run(self, kind: str, params: dict[str, Any], metrics: dict[str, Any], report_md: str,
                          config_hash: str, data_asof: str | None, git_sha: str | None) -> str:
        folder = self.root / "backtest_runs"
        folder.mkdir(exist_ok=True)
        run_id = f"{kind}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        payload = {
            "id": run_id, "run_at": datetime.now(timezone.utc).isoformat(), "kind": kind, "params": params,
            "metrics": metrics, "report_md": report_md, "config_hash": config_hash, "data_asof": data_asof,
            "git_sha": git_sha,
        }
        (folder / f"{run_id}.json").write_text(json.dumps(payload, default=str, indent=1), encoding="utf-8")
        return run_id
