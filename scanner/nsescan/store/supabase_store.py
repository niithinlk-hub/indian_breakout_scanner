"""Supabase store (supabase-py, service-role key). Same interface as `LocalStore`.

Needs SUPABASE_URL and SUPABASE_SERVICE_KEY. The service key bypasses RLS and must
only ever live in GitHub Actions secrets or a local `.env`, never in the web app.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Iterable

import pandas as pd

from ..config import Config, config_from_rows

PAGE = 1000  # PostgREST default max rows per request
WRITE_CHUNK = 5000


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """DataFrame -> JSON-safe records (dates ISO, NaN/NA -> None, numpy -> python)."""

    out = []
    for row in frame.to_dict(orient="records"):
        clean: dict[str, Any] = {}
        for key, value in row.items():
            if value is None or value is pd.NA or (isinstance(value, float) and math.isnan(value)):
                clean[key] = None
            elif isinstance(value, pd.Timestamp):
                clean[key] = value.date().isoformat()
            elif hasattr(value, "item"):
                clean[key] = value.item()
            else:
                clean[key] = value
        out.append(clean)
    return out


def _chunks(items: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


class SupabaseStore:
    kind = "supabase"

    def __init__(self, client: Any) -> None:
        self.client = client

    @classmethod
    def from_env(cls) -> "SupabaseStore":
        from supabase import create_client

        return cls(create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"]))

    # ---- generic helpers -----------------------------------------------------------
    def _select_all(self, table: str, columns: str = "*", filters: list[tuple[str, str, Any]] | None = None,
                    order: list[str] | None = None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = self.client.table(table).select(columns)
            for op, column, value in filters or []:
                query = getattr(query, op)(column, value)
            for column in order or []:
                query = query.order(column)
            batch = query.range(offset, offset + PAGE - 1).execute().data
            rows.extend(batch)
            if len(batch) < PAGE:
                return rows
            offset += PAGE

    def _upsert(self, table: str, frame: pd.DataFrame, on_conflict: str) -> int:
        records = _records(frame)
        for chunk in _chunks(records, WRITE_CHUNK):
            self.client.table(table).upsert(chunk, on_conflict=on_conflict).execute()
        return len(records)

    # ---- config ---------------------------------------------------------------------------
    def read_config(self) -> Config:
        config, _warnings = config_from_rows(self._select_all("config", "key,value"))
        return config

    # ---- universe -------------------------------------------------------------------------
    def upsert_universe(self, universe: pd.DataFrame) -> None:
        existing = {row["symbol"]: row for row in self._select_all("universe", "symbol,added_at,active")}
        frame = universe.copy()
        frame["added_at"] = [existing.get(s, {}).get("added_at") or a for s, a in zip(frame["symbol"], frame["added_at"])]
        self._upsert("universe", frame, on_conflict="symbol")
        dropped = sorted(set(existing) - set(frame["symbol"]))
        for chunk in _chunks(dropped, 200):
            self.client.table("universe").update({"active": False}).in_("symbol", chunk).execute()

    def read_universe(self, active_only: bool = True) -> pd.DataFrame:
        filters = [("eq", "active", True)] if active_only else []
        return pd.DataFrame(self._select_all("universe", filters=filters, order=["symbol"]))

    # ---- prices ------------------------------------------------------------------------------
    def upsert_prices(self, rows: pd.DataFrame, replace_symbols: list[str] | None = None) -> int:
        for symbol in replace_symbols or []:
            self.client.table("prices_daily").delete().eq("symbol", symbol).execute()
        frame = rows[["symbol", "date", "open", "high", "low", "close", "volume"]]
        return self._upsert("prices_daily", frame, on_conflict="symbol,date")

    def read_prices(self, symbols: list[str] | None = None, start: str | None = None) -> pd.DataFrame:
        filters: list[tuple[str, str, Any]] = []
        if start is not None:
            filters.append(("gte", "date", start))
        rows: list[dict[str, Any]] = []
        for chunk in _chunks(symbols, 50) if symbols is not None else [None]:
            chunk_filters = filters + ([("in_", "symbol", chunk)] if chunk is not None else [])
            rows.extend(self._select_all("prices_daily", filters=chunk_filters, order=["symbol", "date"]))
        frame = pd.DataFrame(rows, columns=["symbol", "date", "open", "high", "low", "close", "volume"])
        frame["date"] = pd.to_datetime(frame["date"])
        frame["volume"] = frame["volume"].astype("Int64")
        return frame

    def last_price_dates(self) -> pd.Series:
        rows = self._select_all("price_last_dates", "symbol,last_date")
        if not rows:
            return pd.Series(dtype="datetime64[ns]")
        frame = pd.DataFrame(rows)
        return pd.Series(pd.to_datetime(frame["last_date"]).to_numpy(), index=frame["symbol"], name="date")

    # ---- benchmarks / QA / regime -------------------------------------------------------------
    def upsert_benchmarks(self, rows: pd.DataFrame) -> None:
        self._upsert("benchmarks_daily", rows[["ticker", "date", "close"]], on_conflict="ticker,date")

    def read_benchmarks(self) -> pd.DataFrame:
        frame = pd.DataFrame(self._select_all("benchmarks_daily", order=["ticker", "date"]))
        if not frame.empty:
            frame["date"] = pd.to_datetime(frame["date"])
        return frame

    def replace_data_quality(self, issues: pd.DataFrame) -> None:
        self.client.table("data_quality").delete().gte("id", 0).execute()
        frame = issues.copy()
        if "detail" in frame:
            frame["detail"] = [json.loads(d) if isinstance(d, str) else d for d in frame["detail"]]
        records = _records(frame)
        for chunk in _chunks(records, WRITE_CHUNK):
            self.client.table("data_quality").insert(chunk).execute()

    def upsert_regime(self, regime: pd.DataFrame) -> None:
        self._upsert("regime_daily", regime, on_conflict="date")

    # ---- run logs ----------------------------------------------------------------------------------
    def log_scan_run(self, record: dict[str, Any]) -> int:
        payload = json.loads(json.dumps(record, default=str))
        response = self.client.table("scan_runs").insert(payload).execute()
        return int(response.data[0]["id"])

    def save_backtest_run(self, kind: str, params: dict[str, Any], metrics: dict[str, Any], report_md: str,
                          config_hash: str, data_asof: str | None, git_sha: str | None) -> int:
        payload = json.loads(json.dumps({
            "kind": kind, "params": params, "metrics": metrics, "report_md": report_md,
            "config_hash": config_hash, "data_asof": data_asof, "git_sha": git_sha,
        }, default=str))
        response = self.client.table("backtest_runs").insert(payload).execute()
        return int(response.data[0]["id"])
