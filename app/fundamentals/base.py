from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class FundamentalsProvider(ABC):
    """Abstract provider contract for fundamental data."""

    @abstractmethod
    def get_fundamentals(self, symbols: list[str]) -> pd.DataFrame:
        """Return normalized fundamental data for the requested symbols."""
