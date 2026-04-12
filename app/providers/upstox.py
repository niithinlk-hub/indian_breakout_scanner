from __future__ import annotations

from typing import Any
from urllib.parse import quote

import pandas as pd
import requests

from app.config import AppSettings
from app.models import DateLike
from app.providers.base import MarketDataProvider
from app.providers.exceptions import MarketDataConfigurationError, MarketDataError
from app.providers.schemas import ensure_quote_symbols, normalize_ohlcv_frame
from app.providers.utils import (
    build_session,
    canonicalize_symbol,
    decode_json_bytes,
    expand_symbol_aliases,
    filter_preferred_instruments,
    normalize_date,
    parse_symbol_input,
    raise_for_status,
    wrap_request_exception,
)
from app.utils.logging import get_logger


class UpstoxProvider(MarketDataProvider):
    """HTTP-backed Upstox market data provider."""

    provider_name = "upstox"
    base_url = "https://api.upstox.com/v2"
    instruments_url = "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"

    def __init__(self, settings: AppSettings, session: requests.Session | None = None) -> None:
        self.settings = settings
        self.logger = get_logger(__name__)
        self.session = session or build_session()
        self._instrument_cache: pd.DataFrame | None = None

    def get_historical_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_date: DateLike,
        end_date: DateLike,
    ) -> pd.DataFrame:
        instrument = self._resolve_instrument(symbol)
        start = normalize_date(start_date)
        end = normalize_date(end_date)
        interval_name = self._map_interval(interval)
        encoded_key = quote(str(instrument["instrument_key"]), safe="")
        payload = self._request_json(
            "GET",
            f"/historical-candle/{encoded_key}/{interval_name}/{end.isoformat()}/{start.isoformat()}",
        )
        candles = payload.get("data", {}).get("candles", [])
        frame = pd.DataFrame(candles)
        if frame.empty:
            return normalize_ohlcv_frame(pd.DataFrame(), symbol)

        column_count = frame.shape[1]
        column_names = ["datetime", "open", "high", "low", "close", "volume"]
        if column_count > 6:
            column_names.extend([f"extra_{index}" for index in range(column_count - 6)])
        frame.columns = column_names[:column_count]
        frame["symbol"] = symbol.upper()
        return normalize_ohlcv_frame(frame, symbol.upper())

    def get_quotes(self, symbols: list[str]) -> pd.DataFrame:
        if not symbols:
            return pd.DataFrame()

        quote_rows: list[dict[str, Any]] = []
        requested_symbols = ensure_quote_symbols(symbols)
        instruments = [self._resolve_instrument(symbol) for symbol in requested_symbols]
        instrument_keys = ",".join(str(instrument["instrument_key"]) for instrument in instruments)
        payload = self._request_json("GET", "/market-quote/quotes", params={"instrument_key": instrument_keys})
        quotes = payload.get("data", {})

        for requested_symbol, instrument in zip(requested_symbols, instruments, strict=False):
            instrument_key = str(instrument["instrument_key"])
            quote_data = quotes.get(instrument_key, {})
            ohlc = quote_data.get("ohlc", {})
            quote_rows.append(
                {
                    "symbol": requested_symbol,
                    "provider_symbol": instrument_key,
                    "last_price": quote_data.get("last_price"),
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "close": ohlc.get("close"),
                    "volume": quote_data.get("volume"),
                    "timestamp": pd.to_datetime(quote_data.get("timestamp"), errors="coerce"),
                },
            )
        return pd.DataFrame(quote_rows)

    def get_instruments(self) -> pd.DataFrame:
        if self._instrument_cache is not None:
            return self._instrument_cache.copy()

        response = self._request_absolute(self.instruments_url, auth_required=False)
        payload = decode_json_bytes(response.content)
        instruments = pd.DataFrame(payload)
        if instruments.empty:
            self._instrument_cache = instruments
            return instruments.copy()

        instruments.columns = [str(column).strip().lower() for column in instruments.columns]
        if "exchange" not in instruments.columns:
            instruments["exchange"] = ""
        if "segment" not in instruments.columns:
            instruments["segment"] = ""
        if "instrument_type" not in instruments.columns:
            instruments["instrument_type"] = ""
        if "trading_symbol" not in instruments.columns:
            instruments["trading_symbol"] = ""
        if "name" not in instruments.columns:
            instruments["name"] = ""
        if "short_name" not in instruments.columns:
            instruments["short_name"] = ""
        instruments["exchange"] = instruments["exchange"].fillna("").astype(str).str.upper()
        instruments["segment"] = instruments["segment"].fillna("").astype(str)
        instruments["instrument_type"] = instruments["instrument_type"].fillna("").astype(str)
        instruments["trading_symbol"] = instruments["trading_symbol"].fillna("").astype(str)
        instruments["name"] = instruments["name"].fillna("").astype(str)
        instruments["short_name"] = instruments["short_name"].fillna("").astype(str)
        instruments["lookup_trading_symbol"] = instruments["trading_symbol"].map(canonicalize_symbol)
        instruments["lookup_name"] = instruments["name"].map(canonicalize_symbol)
        instruments["lookup_short_name"] = instruments["short_name"].map(canonicalize_symbol)
        self._instrument_cache = instruments
        return instruments.copy()

    def _resolve_instrument(self, symbol: str) -> pd.Series:
        exchange, raw_symbol = parse_symbol_input(symbol, self.settings.default_exchange)
        aliases = {canonicalize_symbol(value) for value in expand_symbol_aliases(raw_symbol)}
        instruments = filter_preferred_instruments(self.get_instruments())

        exchange_matches = instruments.loc[instruments["exchange"].eq(exchange)]
        candidates = self._match_instruments(exchange_matches, aliases)
        if candidates.empty:
            candidates = self._match_instruments(instruments, aliases)
        if candidates.empty:
            raise MarketDataError(f"No Upstox instrument found for symbol '{symbol}'.")
        candidates = candidates.sort_values(by=["exchange", "trading_symbol"]).reset_index(drop=True)
        return candidates.iloc[0]

    @staticmethod
    def _match_instruments(instruments: pd.DataFrame, aliases: set[str]) -> pd.DataFrame:
        if instruments.empty:
            return instruments
        mask = (
            instruments["lookup_trading_symbol"].isin(aliases)
            | instruments["lookup_name"].isin(aliases)
            | instruments["lookup_short_name"].isin(aliases)
        )
        return instruments.loc[mask]

    @staticmethod
    def _map_interval(interval: str) -> str:
        interval_key = interval.strip().lower()
        if interval_key in {"day", "1day", "daily"}:
            return "day"
        raise MarketDataError(f"Unsupported Upstox interval '{interval}'.")

    def _headers(self, auth_required: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if not auth_required:
            return headers

        if not self.settings.upstox_access_token:
            raise MarketDataConfigurationError(
                "Upstox access token missing. Set UPSTOX_ACCESS_TOKEN in .env.",
            )
        headers["Authorization"] = f"Bearer {self.settings.upstox_access_token}"
        return headers

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._request_absolute(
            f"{self.base_url}{path}",
            params=params,
            auth_required=True,
        )
        payload = response.json()
        if payload.get("status") == "error":
            raise MarketDataError(str(payload))
        return payload

    def _request_absolute(
        self,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        auth_required: bool,
    ) -> requests.Response:
        try:
            response = self.session.request(
                method="GET",
                url=url,
                headers=self._headers(auth_required=auth_required),
                params=params,
                timeout=self.settings.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise wrap_request_exception(exc) from exc

        raise_for_status(response)
        return response
