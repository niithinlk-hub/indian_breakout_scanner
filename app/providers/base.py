from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.models import DateLike


class MarketDataProvider(ABC):
    """Abstract provider contract for Indian market data sources."""

    provider_name: str

    @abstractmethod
    def get_historical_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_date: DateLike,
        end_date: DateLike,
    ) -> pd.DataFrame:
        """Return OHLCV history in the normalized schema."""

    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> pd.DataFrame:
        """Return latest quotes for the requested symbols."""

    @abstractmethod
    def get_instruments(self) -> pd.DataFrame:
        """Return supported tradable instruments metadata."""
