from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pandas as pd

from app.config import AppSettings
from app.models import DateLike
from app.providers.base import MarketDataProvider
from app.providers.exceptions import MarketDataRetryableError
from app.providers.schemas import normalize_ohlcv_frame
from app.utils.logging import get_logger
from app.utils.retry import retry_call


@dataclass(slots=True)
class MarketDataService:
    """Wrapper around a market data provider with retries and normalization."""

    provider: MarketDataProvider
    settings: AppSettings
    logger: logging.Logger = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.logger = get_logger(__name__)

    def get_historical_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_date: DateLike,
        end_date: DateLike,
    ) -> pd.DataFrame:
        frame = retry_call(
            lambda: self.provider.get_historical_ohlcv(symbol, interval, start_date, end_date),
            operation_name=f"{self.provider.provider_name}.get_historical_ohlcv({symbol})",
            max_attempts=self.settings.max_retry_attempts,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
            retry_exceptions=(MarketDataRetryableError,),
        )
        normalized = normalize_ohlcv_frame(frame, symbol)
        self.logger.debug("Fetched %s OHLCV rows for %s.", len(normalized), symbol)
        return normalized

    def get_quotes(self, symbols: list[str]) -> pd.DataFrame:
        return retry_call(
            lambda: self.provider.get_quotes(symbols),
            operation_name=f"{self.provider.provider_name}.get_quotes",
            max_attempts=self.settings.max_retry_attempts,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
            retry_exceptions=(MarketDataRetryableError,),
        )

    def get_instruments(self) -> pd.DataFrame:
        return retry_call(
            self.provider.get_instruments,
            operation_name=f"{self.provider.provider_name}.get_instruments",
            max_attempts=self.settings.max_retry_attempts,
            base_delay_seconds=self.settings.retry_base_delay_seconds,
            retry_exceptions=(MarketDataRetryableError,),
        )
