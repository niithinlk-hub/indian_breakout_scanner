# Indian Stock Breakout Scanner

Production-ready Python scaffold for scanning Indian equities for daily breakout setups. The project is organized into typed modules for data ingestion, technical signals, scoring, explanations, backtesting, alerts, persistence, and a Streamlit dashboard.

## Features

- Python 3.11-targeted codebase with clean package structure
- Broker abstraction layer for Indian market data
- Placeholder `ZerodhaKiteProvider` and `UpstoxProvider` adapters
- Signal engine for breakouts, volume, moving averages, ATR, and benchmark-relative strength
- Configurable scoring engine with ranking support
- Deterministic explanation generator designed for optional future LLM enhancement
- Daily end-of-day scanning pipeline with parallel symbol processing and SQLite persistence
- Streamlit dashboard with breakout pages, filters, explanations, mini charts, and CSV export
- Backtesting engine with configurable entries and exits
- Pytest scaffolding with synthetic OHLCV fixtures

## Folder structure

```text
indian_breakout_scanner/
├── app/
│   ├── alerts/
│   ├── backtesting/
│   ├── dashboard/
│   ├── explanations/
│   ├── providers/
│   ├── scoring/
│   ├── signals/
│   ├── storage/
│   ├── utils/
│   ├── config.py
│   ├── data_ingestion.py
│   ├── main.py
│   ├── models.py
│   └── pipeline.py
├── config/
│   └── watchlist.example.txt
├── data/
├── tests/
├── .env.example
├── README.md
└── requirements.txt
```

## Setup

1. Install Python 3.11.
2. Create and activate a virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in the provider credentials you plan to use.
5. Update `config/watchlist.example.txt` or point the CLI to your own watchlist file.

Required live-data environment variables:

- Zerodha: `MARKET_DATA_PROVIDER=zerodha`, `ZERODHA_API_KEY`, `ZERODHA_ACCESS_TOKEN`
- Upstox: `MARKET_DATA_PROVIDER=upstox`, `UPSTOX_ACCESS_TOKEN`
- Common: `DEFAULT_EXCHANGE=NSE`

## Running the scanner

```bash
python -m app.main --scan-eod
```

If the dashboard is empty, the most common cause is that no successful scan has been stored yet. Run the scanner after configuring your broker access token:

```bash
python -m app.main --scan-eod
```

The scanner stores results in SQLite only after successful broker data fetches.

## Launching the dashboard

```bash
streamlit run streamlit_app.py
```

Dashboard pages:

1. Top breakouts today
2. Near-breakouts
3. Failed breakouts
4. Signal history
5. Backtest summary

## Deploying to Streamlit Community Cloud

1. Push this folder to a GitHub repository.
2. In Streamlit Community Cloud, create a new app from that repo.
3. Set the main file path to `streamlit_app.py`.
4. In the app settings, add secrets using the same keys shown in `.streamlit/secrets.toml.example`.
5. Deploy the app and use the sidebar `Run scan now` button to fetch/store results.

Example Streamlit secrets:

```toml
MARKET_DATA_PROVIDER = "zerodha"
ZERODHA_API_KEY = "your_api_key"
ZERODHA_ACCESS_TOKEN = "your_access_token"
DEFAULT_EXCHANGE = "NSE"
```

Notes:

- Streamlit Cloud provides an HTTPS app URL, which is the kind of URL Zerodha expects for app configuration.
- The dashboard now supports running scans directly from the UI, which is better for Streamlit deployment than relying on a separate CLI step.
- Local SQLite storage works for quick deployments, but Streamlit Community Cloud storage is not a durable production database. For long-term persistence, move scan results to an external database later.

## Backtesting example

```python
from app.backtesting.engine import EntryConfig, ExitConfig, run_breakout_backtest

result = run_breakout_backtest(
    df=ohlcv_df,
    symbol="RELIANCE",
    entry_config=EntryConfig(
        breakout_lookback=20,
        min_volume_multiple=2.0,
        require_above_200_dma=True,
    ),
    exit_config=ExitConfig(
        fixed_holding_period=10,
        stop_loss_pct=0.05,
        trailing_stop_pct=0.08,
        close_below_moving_average=20,
    ),
)

print(result.summary)
print(result.trades.head())
```

Persist backtest outputs by saving `result.summary` and `result.trades` with `app.storage.SQLiteStore.save_backtest_run(...)`.

## Testing

```bash
pytest
```

## Notes

- All secrets stay in environment variables.
- Historical OHLCV is normalized into a shared schema:
  `datetime, open, high, low, close, volume, symbol`
- The explanation generator is deterministic and template-first so it remains stable in automated workflows.
- The project was scaffolded to be Python 3.11 compatible. If your local machine only has Python 3.12 available, install 3.11 before production deployment.
