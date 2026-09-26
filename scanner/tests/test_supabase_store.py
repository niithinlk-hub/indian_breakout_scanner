"""SupabaseStore against a fake supabase-py client (no network): chunking, pagination,
JSON-safe payloads and config merging."""

from __future__ import annotations

import numpy as np
import pandas as pd

from nsescan.store.supabase_store import PAGE, WRITE_CHUNK, SupabaseStore


class FakeQuery:
    def __init__(self, client, table):
        self.client, self.table, self.op, self.payload, self.filters, self.bounds = client, table, None, None, [], None

    def select(self, columns="*"):
        self.op = "select"
        return self

    def upsert(self, rows, on_conflict=None):
        self.op, self.payload = "upsert", rows
        self.client.calls.append(("upsert", self.table, len(rows), on_conflict))
        return self

    def insert(self, rows):
        self.op, self.payload = "insert", rows
        self.client.calls.append(("insert", self.table, rows))
        return self

    def update(self, values):
        self.op, self.payload = "update", values
        return self

    def delete(self):
        self.op = "delete"
        return self

    def eq(self, col, value):
        self.filters.append(("eq", col, value))
        return self

    def gte(self, col, value):
        self.filters.append(("gte", col, value))
        return self

    def in_(self, col, values):
        self.filters.append(("in", col, list(values)))
        return self

    def order(self, col):
        return self

    def range(self, start, end):
        self.bounds = (start, end)
        return self

    def execute(self):
        class Response:
            pass

        response = Response()
        if self.op == "select":
            rows = self.client.tables.get(self.table, [])
            start, end = self.bounds
            response.data = rows[start : end + 1]
        elif self.op == "insert":
            response.data = [{"id": 7}]
        else:
            if self.op in ("update", "delete"):
                self.client.calls.append((self.op, self.table, self.filters))
            response.data = []
        return response


class FakeClient:
    def __init__(self, tables=None):
        self.tables = tables or {}
        self.calls = []

    def table(self, name):
        return FakeQuery(self, name)


def test_upsert_prices_chunks_and_serialises():
    n = WRITE_CHUNK + 10
    rows = pd.DataFrame({
        "symbol": "ABC", "date": pd.bdate_range("2020-01-01", periods=n), "open": 1.0, "high": 2.0, "low": 0.5,
        "close": np.r_[np.full(n - 1, 1.5), np.nan], "volume": pd.array([100] * (n - 1) + [None], dtype="Int64"),
    })
    client = FakeClient()
    SupabaseStore(client).upsert_prices(rows, replace_symbols=["ABC"])
    upserts = [c for c in client.calls if c[0] == "upsert"]
    assert [c[2] for c in upserts] == [WRITE_CHUNK, 10]
    assert all(c[3] == "symbol,date" for c in upserts)
    assert ("delete", "prices_daily", [("eq", "symbol", "ABC")]) in client.calls


def test_select_paginates():
    client = FakeClient({"universe": [{"symbol": f"S{i}", "active": True} for i in range(PAGE + 5)]})
    frame = SupabaseStore(client).read_universe()
    assert len(frame) == PAGE + 5


def test_read_config_merges_defaults():
    client = FakeClient({"config": [{"key": "rs.min_rank", "value": 90.0}]})
    cfg = SupabaseStore(client).read_config()
    assert cfg["rs.min_rank"] == 90.0 and cfg.source == "supabase"
    assert cfg["base.max_len"] == 60


def test_records_are_json_safe():
    from nsescan.store.supabase_store import _records

    frame = pd.DataFrame({"d": [pd.Timestamp("2026-01-02")], "x": [np.float64("nan")], "n": [np.int64(3)],
                          "v": pd.array([None], dtype="Int64")})
    assert _records(frame) == [{"d": "2026-01-02", "x": None, "n": 3, "v": None}]
