from __future__ import annotations

from app.config import AppSettings
from app.providers.base import MarketDataProvider
from app.providers.upstox import UpstoxProvider
from app.providers.zerodha import ZerodhaKiteProvider


def build_market_data_provider(settings: AppSettings) -> MarketDataProvider:
    """Create the configured market data provider."""

    if settings.provider_name == "zerodha":
        return ZerodhaKiteProvider(settings)
    if settings.provider_name == "upstox":
        return UpstoxProvider(settings)
    raise ValueError(
        f"Unsupported MARKET_DATA_PROVIDER '{settings.provider_name}'. "
        "Use 'zerodha' or 'upstox'.",
    )
