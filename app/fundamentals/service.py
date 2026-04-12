from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.fundamentals.base import FundamentalsProvider


@dataclass(slots=True)
class FundamentalsService:
    """Thin wrapper around a fundamentals provider."""

    provider: FundamentalsProvider

    def get_fundamentals(self, symbols: list[str]) -> pd.DataFrame:
        return self.provider.get_fundamentals(symbols)

    def build_lookup(self, symbols: list[str]) -> dict[str, dict[str, Any]]:
        frame = self.get_fundamentals(symbols)
        if frame.empty:
            return {}
        return {
            str(row["symbol"]).upper(): row.to_dict()
            for _, row in frame.iterrows()
            if str(row.get("symbol", "")).strip()
        }
