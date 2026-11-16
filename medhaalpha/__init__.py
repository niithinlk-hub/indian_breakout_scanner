"""MEDHAALPHA — EMA 20/50 adaptive trend research backtester for NSE stocks.

The package is intentionally separate from the Streamlit scanner in ``app/``.
It downloads point-in-time NSE data (bhavcopies + Upstox candles), builds
leak-free multi-timeframe features, simulates the intraday (TrendPulse) and
positional (TrendSwing) engines with Indian transaction costs, applies the
portfolio risk manager for a ₹3,00,000 account and produces a research report.
"""

__version__ = "1.0.0"
