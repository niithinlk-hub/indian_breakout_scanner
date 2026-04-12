from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.fundamentals.base import FundamentalsProvider

_DEFAULT_COLUMNS = [
    "symbol",
    "sector",
    "market_cap_bucket",
    "market_cap_inr_cr",
    "pe_ratio",
    "pb_ratio",
    "ev_ebitda",
    "dividend_yield_pct",
    "revenue_growth_pct",
    "eps_growth_pct",
    "roe_pct",
    "roce_pct",
    "debt_to_equity",
    "net_margin_pct",
    "operating_margin_pct",
    "current_ratio",
    "interest_coverage",
    "promoter_holding_pct",
]


class CsvFundamentalsProvider(FundamentalsProvider):
    """Load fundamental snapshots from a local CSV file."""

    def __init__(self, csv_path: Path) -> None:
        self.csv_path = Path(csv_path)

    def get_fundamentals(self, symbols: list[str]) -> pd.DataFrame:
        if not self.csv_path.exists():
            return pd.DataFrame(columns=_DEFAULT_COLUMNS)

        frame = pd.read_csv(self.csv_path)
        frame.columns = [str(column).strip().lower() for column in frame.columns]
        for column in _DEFAULT_COLUMNS:
            if column not in frame.columns:
                frame[column] = pd.NA

        frame["symbol"] = frame["symbol"].fillna("").astype(str).str.upper()
        for column in [
            "market_cap_inr_cr",
            "pe_ratio",
            "pb_ratio",
            "ev_ebitda",
            "dividend_yield_pct",
            "revenue_growth_pct",
            "eps_growth_pct",
            "roe_pct",
            "roce_pct",
            "debt_to_equity",
            "net_margin_pct",
            "operating_margin_pct",
            "current_ratio",
            "interest_coverage",
            "promoter_holding_pct",
        ]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

        requested = {symbol.strip().upper() for symbol in symbols}
        filtered = frame.loc[frame["symbol"].isin(requested)].copy() if requested else frame.copy()
        return filtered[_DEFAULT_COLUMNS].drop_duplicates(subset=["symbol"]).reset_index(drop=True)
