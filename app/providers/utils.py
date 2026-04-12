from __future__ import annotations

import gzip
import io
import json
import re
from datetime import date, datetime
from typing import Any

import pandas as pd
import requests

from app.models import DateLike
from app.providers.exceptions import (
    MarketDataConfigurationError,
    MarketDataError,
    MarketDataRetryableError,
)

_DERIVATIVE_TYPES = {"CE", "PE", "FUT", "FUTSTK", "FUTIDX", "OPTSTK", "OPTIDX"}
_DEFAULT_INDEX_ALIASES = {
    "^NSEI": ["NIFTY 50", "NIFTY50", "NIFTY"],
    "^NSEBANK": ["NIFTY BANK", "BANKNIFTY", "NIFTYBANK"],
}


def build_session() -> requests.Session:
    """Create a reusable HTTP session."""

    session = requests.Session()
    session.headers.update({"User-Agent": "indian-breakout-scanner/1.0"})
    return session


def normalize_date(value: DateLike) -> date:
    """Normalize date-like values to a date."""

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def canonicalize_symbol(value: str | None) -> str:
    """Convert symbols and names into a comparable lookup key."""

    return re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())


def parse_symbol_input(symbol: str, default_exchange: str) -> tuple[str, str]:
    """Split an input symbol into exchange and symbol components."""

    cleaned = symbol.strip()
    if ":" in cleaned:
        exchange, raw_symbol = cleaned.split(":", 1)
        return exchange.strip().upper(), raw_symbol.strip()
    return default_exchange.upper(), cleaned


def expand_symbol_aliases(symbol: str) -> set[str]:
    """Expand common index aliases to improve provider lookups."""

    aliases = {symbol}
    aliases.update(_DEFAULT_INDEX_ALIASES.get(symbol.upper(), []))
    return {alias for alias in aliases if alias}


def filter_preferred_instruments(instruments: pd.DataFrame) -> pd.DataFrame:
    """Prefer cash/index instruments over derivatives when resolving symbols."""

    if instruments.empty:
        return instruments

    filtered = instruments.copy()
    if "expiry" in filtered.columns:
        filtered = filtered.loc[filtered["expiry"].isna()]
    if "instrument_type" in filtered.columns:
        filtered = filtered.loc[~filtered["instrument_type"].fillna("").str.upper().isin(_DERIVATIVE_TYPES)]
    return filtered if not filtered.empty else instruments


def maybe_decompress(content: bytes) -> bytes:
    """Decompress gzip payloads when necessary."""

    if content[:2] == b"\x1f\x8b":
        return gzip.decompress(content)
    return content


def decode_json_bytes(content: bytes) -> Any:
    """Decode JSON payloads that may be gzip-compressed."""

    return json.loads(maybe_decompress(content).decode("utf-8"))


def decode_csv_bytes(content: bytes) -> pd.DataFrame:
    """Decode CSV payloads that may be gzip-compressed."""

    return pd.read_csv(io.StringIO(maybe_decompress(content).decode("utf-8")), low_memory=False)


def raise_for_status(response: requests.Response) -> None:
    """Translate HTTP failures into domain-specific exceptions."""

    if response.ok:
        return

    body_preview = response.text[:500]
    if response.status_code in {429, 500, 502, 503, 504}:
        raise MarketDataRetryableError(
            f"Transient provider error {response.status_code}: {body_preview}",
        )
    if response.status_code in {401, 403}:
        raise MarketDataConfigurationError(
            f"Authentication failed with status {response.status_code}: {body_preview}",
        )
    raise MarketDataError(f"Provider request failed with status {response.status_code}: {body_preview}")


def wrap_request_exception(exc: requests.RequestException) -> MarketDataRetryableError:
    """Translate network exceptions into retryable domain errors."""

    return MarketDataRetryableError(f"Network error while calling provider API: {exc}")
