from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _get_streamlit_secret(key: str) -> str | None:
    """Read a value from Streamlit secrets when available."""

    try:
        import streamlit as st
    except Exception:
        return None

    try:
        value: Any = st.secrets.get(key)
    except Exception:
        return None

    if value is None:
        return None
    return str(value)


def _get_setting(key: str, default: str | None = None) -> str | None:
    """Resolve a setting from environment variables first, then Streamlit secrets."""

    env_value = os.getenv(key)
    if env_value not in {None, ""}:
        return env_value

    secret_value = _get_streamlit_secret(key)
    if secret_value not in {None, ""}:
        return secret_value

    return default


@dataclass(slots=True)
class AppSettings:
    """Application configuration loaded from environment variables."""

    project_root: Path
    database_path: Path
    provider_name: str
    log_level: str
    benchmark_symbol: str
    scan_lookback_days: int
    scan_workers: int
    max_retry_attempts: int
    retry_base_delay_seconds: float
    request_timeout_seconds: float
    default_exchange: str
    zerodha_api_key: str | None
    zerodha_api_secret: str | None
    zerodha_access_token: str | None
    upstox_api_key: str | None
    upstox_api_secret: str | None
    upstox_access_token: str | None


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""

    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    return AppSettings(
        project_root=project_root,
        database_path=Path(_get_setting("DATABASE_PATH", str(data_dir / "scanner.sqlite")) or data_dir / "scanner.sqlite"),
        provider_name=(_get_setting("MARKET_DATA_PROVIDER", "zerodha") or "zerodha").strip().lower(),
        log_level=(_get_setting("LOG_LEVEL", "INFO") or "INFO").upper(),
        benchmark_symbol=_get_setting("BENCHMARK_SYMBOL", "^NSEI") or "^NSEI",
        scan_lookback_days=int(_get_setting("SCAN_LOOKBACK_DAYS", "365") or "365"),
        scan_workers=int(_get_setting("SCAN_WORKERS", "4") or "4"),
        max_retry_attempts=int(_get_setting("MAX_RETRY_ATTEMPTS", "3") or "3"),
        retry_base_delay_seconds=float(_get_setting("RETRY_BASE_DELAY_SECONDS", "1.0") or "1.0"),
        request_timeout_seconds=float(_get_setting("REQUEST_TIMEOUT_SECONDS", "30") or "30"),
        default_exchange=(_get_setting("DEFAULT_EXCHANGE", "NSE") or "NSE").upper(),
        zerodha_api_key=_get_setting("ZERODHA_API_KEY"),
        zerodha_api_secret=_get_setting("ZERODHA_API_SECRET"),
        zerodha_access_token=_get_setting("ZERODHA_ACCESS_TOKEN"),
        upstox_api_key=_get_setting("UPSTOX_API_KEY"),
        upstox_api_secret=_get_setting("UPSTOX_API_SECRET"),
        upstox_access_token=_get_setting("UPSTOX_ACCESS_TOKEN"),
    )
