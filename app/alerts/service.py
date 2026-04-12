from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.utils.logging import get_logger


class AlertDispatcher(ABC):
    """Interface for breakout alert destinations."""

    @abstractmethod
    def send_scan_alert(self, results_df: pd.DataFrame) -> None:
        """Dispatch scanner results to an alert destination."""


class ConsoleAlertDispatcher(AlertDispatcher):
    """Simple logger-based alert dispatcher."""

    def __init__(self) -> None:
        self.logger = get_logger(__name__)

    def send_scan_alert(self, results_df: pd.DataFrame) -> None:
        if results_df.empty:
            self.logger.info("No breakout candidates to alert.")
            return

        for _, row in results_df.head(10).iterrows():
            self.logger.info(
                "Alert | %s | score=%s | rating=%s | summary=%s",
                row.get("symbol"),
                row.get("total_score"),
                row.get("rating"),
                row.get("trader_summary"),
            )
