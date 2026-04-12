from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.config import AppSettings
from app.providers.upstox import UpstoxProvider
from app.providers.zerodha import ZerodhaKiteProvider


def _settings() -> AppSettings:
    return AppSettings(
        project_root=Path.cwd(),
        database_path=Path.cwd() / "data" / "scanner.sqlite",
        provider_name="zerodha",
        log_level="INFO",
        benchmark_symbol="^NSEI",
        scan_lookback_days=365,
        scan_workers=2,
        max_retry_attempts=3,
        retry_base_delay_seconds=1.0,
        request_timeout_seconds=30.0,
        default_exchange="NSE",
        zerodha_api_key="test-key",
        zerodha_api_secret=None,
        zerodha_access_token="test-token",
        upstox_api_key="test-key",
        upstox_api_secret=None,
        upstox_access_token="test-token",
    )


def test_zerodha_historical_parsing_normalizes_schema() -> None:
    provider = ZerodhaKiteProvider(_settings())
    provider._resolve_instrument = lambda symbol: pd.Series(  # type: ignore[method-assign]
        {"instrument_token": 123, "exchange": "NSE", "trading_symbol": "RELIANCE"},
    )
    provider._request_json = lambda *args, **kwargs: {  # type: ignore[method-assign]
        "data": {
            "candles": [
                ["2024-01-01T09:15:00+0530", 100.0, 105.0, 99.0, 104.0, 1_000_000],
                ["2024-01-02T09:15:00+0530", 104.0, 108.0, 103.0, 107.0, 1_200_000],
            ],
        },
    }

    history = provider.get_historical_ohlcv("RELIANCE", "day", "2024-01-01", "2024-01-31")
    assert list(history.columns) == ["datetime", "open", "high", "low", "close", "volume", "symbol"]
    assert history.iloc[-1]["symbol"] == "RELIANCE"


def test_zerodha_resolve_instrument_prefers_cash_market_rows() -> None:
    provider = ZerodhaKiteProvider(_settings())
    provider._instrument_cache = pd.DataFrame(
        [
            {
                "exchange": "NSE",
                "trading_symbol": "RELIANCE",
                "name": "RELIANCE INDUSTRIES",
                "instrument_type": "EQ",
                "expiry": pd.NaT,
                "instrument_token": 111,
                "lookup_trading_symbol": "RELIANCE",
                "lookup_name": "RELIANCEINDUSTRIES",
            },
            {
                "exchange": "NSE",
                "trading_symbol": "RELIANCE",
                "name": "RELIANCE FUT",
                "instrument_type": "FUT",
                "expiry": pd.Timestamp("2026-05-28"),
                "instrument_token": 222,
                "lookup_trading_symbol": "RELIANCE",
                "lookup_name": "RELIANCEFUT",
            },
        ],
    )

    instrument = provider._resolve_instrument("RELIANCE")
    assert int(instrument["instrument_token"]) == 111


def test_upstox_resolve_instrument_supports_benchmark_alias() -> None:
    provider = UpstoxProvider(_settings())
    provider._instrument_cache = pd.DataFrame(
        [
            {
                "exchange": "NSE",
                "trading_symbol": "RELIANCE",
                "short_name": "Reliance",
                "name": "Reliance Industries",
                "instrument_type": "EQ",
                "instrument_key": "NSE_EQ|INE002A01018",
                "lookup_trading_symbol": "RELIANCE",
                "lookup_name": "RELIANCEINDUSTRIES",
                "lookup_short_name": "RELIANCE",
            },
            {
                "exchange": "NSE",
                "trading_symbol": "Nifty 50",
                "short_name": "Nifty 50",
                "name": "Nifty 50",
                "instrument_type": "INDEX",
                "instrument_key": "NSE_INDEX|Nifty 50",
                "lookup_trading_symbol": "NIFTY50",
                "lookup_name": "NIFTY50",
                "lookup_short_name": "NIFTY50",
            },
        ],
    )

    instrument = provider._resolve_instrument("^NSEI")
    assert str(instrument["instrument_key"]) == "NSE_INDEX|Nifty 50"
