from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from nsescan.config import DEFAULTS, config_from_rows, default_config, seed_sql
from nsescan.fetch import canonicalize, download_ohlcv, split_download
from nsescan.panel import build_panel
from nsescan.universe import combine, load_universe, parse_constituents

CSV_HEADER = "Company Name,Industry,Symbol,Series,ISIN Code\n"


def _csv(n: int, prefix: str, extra: str = "") -> str:
    rows = "".join(f"Co {prefix}{i} Ltd.,Ind{i % 4},{prefix}{i},EQ,INE{i:09d}\n" for i in range(n))
    return CSV_HEADER + rows + extra


# ---------------------------------------------------------------- universe
def test_parse_constituents_validates_columns_and_size():
    frame = parse_constituents(_csv(500, "N"), "N500")
    assert len(frame) == 500
    with pytest.raises(ValueError):
        parse_constituents(_csv(100, "N"), "N500")
    with pytest.raises(ValueError):
        parse_constituents("Symbol,Other\nA,B\n", "N500")


def test_combine_dedupes_by_segment_priority():
    n500 = parse_constituents(_csv(500, "N"), "N500")
    micro = parse_constituents(_csv(249, "M") + "Dup Ltd.,Ind0,N3,EQ,INE000000003\n", "MICRO250")
    universe, dups = combine({"N500": n500, "MICRO250": micro}, added_at="2026-09-26")
    assert dups == ["N3"]
    assert universe.set_index("symbol").at["N3", "segment"] == "N500"
    assert universe["symbol"].is_unique and len(universe) == 749
    assert (universe["yahoo_ticker"] == universe["symbol"] + ".NS").all()


def test_load_universe_drops_placeholders_and_falls_back_to_snapshot(tmp_path):
    (tmp_path / "N500").mkdir()
    (tmp_path / "MICRO250").mkdir()
    (tmp_path / "N500" / "2026-09-01.csv").write_text(_csv(500, "N", "Dummy,Ind0,DUMMYHEG,EQ,X\n"))
    (tmp_path / "MICRO250" / "2026-09-01.csv").write_text(_csv(250, "M"))
    loaded = load_universe(tmp_path, refresh=False)
    assert loaded.placeholders["N500"] == ["DUMMYHEG"]
    assert loaded.from_snapshot == {"N500": True, "MICRO250": True}
    assert loaded.frame.groupby("segment").size().to_dict() == {"MICRO250": 250, "N500": 500}


# ---------------------------------------------------------------- fetch
def _yahoo_frame(tickers, dates):
    cols = pd.MultiIndex.from_product([tickers, ["Open", "High", "Low", "Close", "Volume"]])
    data = np.tile([100.123456, 101.0, 99.0, 100.5, 12345.0], (len(dates), len(tickers)))
    return pd.DataFrame(data, index=pd.DatetimeIndex(dates), columns=cols)


def test_canonicalize_rounds_and_drops_incomplete_rows():
    raw = pd.DataFrame({"Open": [1.123456789, np.nan], "High": [2.0, 2.0], "Low": [0.5, 0.5], "Close": [1.5, 1.5],
                        "Volume": [10.4, 5.0]}, index=pd.to_datetime(["2026-01-01", "2026-01-02"]))
    out = canonicalize(raw)
    assert len(out) == 1 and out["open"].iloc[0] == 1.1235 and out["volume"].iloc[0] == 10


def test_split_download_handles_both_multiindex_layouts():
    dates = pd.bdate_range("2026-01-01", periods=3)
    by_ticker = _yahoo_frame(["A.NS", "B.NS"], dates)
    assert set(split_download(by_ticker, ["A.NS", "B.NS"])) == {"A.NS", "B.NS"}
    by_field = by_ticker.swaplevel(axis=1)
    assert set(split_download(by_field, ["A.NS", "B.NS"])) == {"A.NS", "B.NS"}


def test_download_retries_failed_tickers_with_backoff():
    dates = pd.bdate_range("2026-01-01", periods=3)
    calls, sleeps = [], []

    def fake(tickers, **kwargs):
        calls.append(list(tickers))
        if len(calls) == 1:  # first call: C comes back empty
            return _yahoo_frame([t for t in tickers if t != "C.NS"], dates), {"C.NS": "timeout"}
        if len(calls) == 2:
            raise ConnectionError("rate limited")
        return _yahoo_frame(tickers, dates), {}

    result = download_ohlcv(["A.NS", "B.NS", "C.NS"], chunk_size=3, max_retries=4, backoff_base=2.0,
                            downloader=fake, sleep=sleeps.append)
    assert set(result.frames) == {"A.NS", "B.NS", "C.NS"} and not result.failed
    assert sleeps == [2.0, 4.0] and calls[1:] == [["C.NS"], ["C.NS"]]


def test_download_reports_permanent_failures():
    result = download_ohlcv(["X.NS"], max_retries=2, downloader=lambda t, **k: (None, {"X.NS": "delisted"}),
                            sleep=lambda s: None)
    assert result.failed == {"X.NS": "delisted"} and result.attempts == 3


# ---------------------------------------------------------------- config
def test_config_overrides_and_hash():
    base = default_config()
    cfg, warnings = config_from_rows([{"key": "rs.min_rank", "value": 85.0}, {"key": "bogus.key", "value": 1}])
    assert cfg["rs.min_rank"] == 85.0 and cfg.hash != base.hash
    assert any("unknown" in w for w in warnings) and any("missing" in w for w in warnings)
    assert cfg.seg("liquidity.min_median_tv_cr", "MICRO250") == 3.0
    with pytest.raises(KeyError):
        base.with_overrides({"nope": 1})


def test_seed_sql_covers_every_default():
    sql = seed_sql()
    for key in DEFAULTS:
        assert f"('{key}'," in sql
    assert "on conflict (key) do update set default_value" in sql


# ---------------------------------------------------------------- calendar / stubs
def test_holiday_and_gap_session_stubs(synthetic):
    prices, universe = synthetic
    dates = sorted(prices["date"].unique())
    holiday, gap = dates[100], dates[200]
    reference = pd.DatetimeIndex([d for d in dates if d != holiday])  # Nifty 50 has no bar on the holiday
    prices = prices.sort_values(["symbol", "date"]).copy()
    prev = prices.groupby("symbol")["close"].shift(1)
    for day in (holiday, gap):
        rows = prices["date"].eq(day)
        prices.loc[rows, ["open", "high", "low", "close"]] = np.repeat(prev[rows].to_numpy()[:, None], 4, axis=1)
        prices.loc[rows, "volume"] = 0
    panel = build_panel(prices, universe, 0.5, 0.10, reference)
    assert holiday not in panel.dates and gap in panel.dates
    assert not panel.has_bar.loc[gap].any()  # stub bars removed -> missing, not zero-volume
    assert set(panel.dropped["reason"]) == {"off_calendar_holiday_stub", "gap_session_stub"}


def test_material_changes_ignores_float_jitter():
    from nsescan.pipeline import material_changes

    stored = pd.DataFrame({"symbol": "A", "date": pd.to_datetime(["2026-09-24", "2026-09-25"]),
                           "open": [193.2779, 199.0], "high": [200.9492, 201.0], "low": [189.3, 195.0],
                           "close": [198.9666, 200.0], "volume": pd.array([100, 200], dtype="Int64")})
    fresh = stored.copy()
    fresh.loc[0, "open"] = 193.2778                      # 4th-decimal jitter: ignored
    fresh.loc[1, "close"] = 200.5                        # real revision: kept
    fresh = pd.concat([fresh, pd.DataFrame({"symbol": ["A"], "date": pd.to_datetime(["2026-09-28"]), "open": [1.0],
                                            "high": [1.0], "low": [1.0], "close": [1.0],
                                            "volume": pd.array([5], dtype="Int64")})], ignore_index=True)
    out = material_changes(fresh, stored, 1e-5)
    assert out["date"].dt.strftime("%m-%d").tolist() == ["09-25", "09-28"]
