"""Exceptions used by market data providers."""


class MarketDataError(Exception):
    """Base exception for data provider failures."""


class MarketDataRetryableError(MarketDataError):
    """Transient provider failure that can be retried."""


class MarketDataConfigurationError(MarketDataError):
    """Provider is not configured correctly."""


class ProviderNotImplementedError(MarketDataConfigurationError):
    """Placeholder provider method has not been implemented yet."""
