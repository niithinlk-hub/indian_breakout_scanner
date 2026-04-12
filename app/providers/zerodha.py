from __future__ import annotations

from typing import Any

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
    decode_csv_bytes,
    expand_symbol_aliases,
    filter_preferred_instruments,
    normalize_date,
    parse_symbol_input,
    raise_for_status,
    wrap_request_exception,
)
from app.utils.logging import get_logger


class ZerodhaKiteProvider(MarketDataProvider):
    """HTTP-backed Zerodha Kite Connect provider."""

    provider_name = "zerodha"
    base_url = "https://api.kite.trade"

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
        payload = self._request_json(
            "GET",
            f"/instruments/historical/{int(instrument['instrument_token'])}/{interval}",
            params={
                "from": f"{start.isoformat()} 00:00:00",
                "to": f"{end.isoformat()} 23:59:59",
                "oi": 0,
            },
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
        quote_rows: list[dict[str, Any]] = []
        for symbol in ensure_quote_symbols(symbols):
            instrument = self._resolve_instrument(symbol)
            provider_symbol = f"{instrument['exchange']}:{instrument['trading_symbol']}"
            payload = self._request_json("GET", "/quote", params=[("i", provider_symbol)])
            quote = payload.get("data", {}).get(provider_symbol, {})
            if not quote:
                continue
            ohlc = quote.get("ohlc", {})
            quote_rows.append(
                {
                    "symbol": symbol,
                    "provider_symbol": provider_symbol,
                    "last_price": quote.get("last_price"),
                    "open": ohlc.get("open"),
                    "high": ohlc.get("high"),
                    "low": ohlc.get("low"),
                    "close": ohlc.get("close"),
                    "volume": quote.get("volume"),
                    "timestamp": pd.to_datetime(quote.get("timestamp"), errors="coerce"),
                },
            )
        return pd.DataFrame(quote_rows)

    def get_instruments(self) -> pd.DataFrame:
        if self._instrument_cache is not None:
            return self._instrument_cache.copy()

        response = self._request("GET", "/instruments")
        instruments = decode_csv_bytes(response.content)
        instruments.columns = [str(column).strip().lower() for column in instruments.columns]
        instruments = instruments.rename(columns={"tradingsymbol": "trading_symbol"})
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
        instruments["exchange"] = instruments["exchange"].fillna("").astype(str).str.upper()
        instruments["segment"] = instruments["segment"].fillna("").astype(str)
        instruments["instrument_type"] = instruments["instrument_type"].fillna("").astype(str)
        instruments["trading_symbol"] = instruments["trading_symbol"].fillna("").astype(str)
        instruments["name"] = instruments["name"].fillna("").astype(str)
        instruments["provider_symbol"] = instruments["exchange"] + ":" + instruments["trading_symbol"]
        instruments["lookup_trading_symbol"] = instruments["trading_symbol"].map(canonicalize_symbol)
        instruments["lookup_name"] = instruments["name"].map(canonicalize_symbol)
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
            raise MarketDataError(f"No Zerodha instrument found for symbol '{symbol}'.")

        candidates = candidates.sort_values(by=["exchange", "trading_symbol"]).reset_index(drop=True)
        return candidates.iloc[0]

    @staticmethod
    def _match_instruments(instruments: pd.DataFrame, aliases: set[str]) -> pd.DataFrame:
        if instruments.empty:
            return instruments
        mask = instruments["lookup_trading_symbol"].isin(aliases) | instruments["lookup_name"].isin(aliases)
        return instruments.loc[mask]

    def _headers(self) -> dict[str, str]:
        if not self.settings.zerodha_api_key or not self.settings.zerodha_access_token:
            raise MarketDataConfigurationError(
                "Zerodha credentials missing. Set ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN in .env.",
            )
        return {
            "Authorization": f"token {self.settings.zerodha_api_key}:{self.settings.zerodha_access_token}",
            "X-Kite-Version": "3",
        }

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    ) -> requests.Response:
        try:
            response = self.session.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=self._headers(),
                params=params,
                timeout=self.settings.request_timeout_seconds,
            )
        except requests.RequestException as exc:
            raise wrap_request_exception(exc) from exc

        raise_for_status(response)
        return response

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    ) -> dict[str, Any]:
        response = self._request(method, path, params=params)
        payload = response.json()
        if payload.get("status") == "error":
            raise MarketDataError(str(payload))
        return payload
