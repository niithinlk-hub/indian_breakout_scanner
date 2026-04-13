# Indian Stock Breakout Scanner

Production-ready Python scaffold for scanning Indian equities for daily breakout setups. The project is organized into typed modules for data ingestion, technical signals, scoring, explanations, backtesting, alerts, persistence, and a Streamlit dashboard.

## Features

- Python 3.11-targeted codebase with clean package structure
- Broker abstraction layer for Indian market data
- Placeholder `ZerodhaKiteProvider` and `UpstoxProvider` adapters
- Signal engine for breakouts, volume, moving averages, ATR, and benchmark-relative strength
- Configurable scoring engine with ranking support
- Fundamental scoring matrix and composite technical-plus-fundamental ranking
- Deterministic explanation generator designed for optional future LLM enhancement
- Daily end-of-day scanning pipeline with parallel symbol processing and SQLite persistence
- Streamlit dashboard with breakout pages, filters, explanations, mini charts, and CSV export
- Separate BOS + FVG analyzer page for Yahoo-powered watchlist screening and 5-year single-stock chart analysis
- Separate stock alerter page for bullish breakout scoring, NIFTY LargeMidcap 250 scans, and Telegram alerts
- Stock alerter also supports a `NASDAQ Top 250` universe with live Nasdaq-screener fetch plus bundled fallback
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
│   ├── fundamentals.example.csv
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

Fundamentals are loaded from a local CSV file configured via `FUNDAMENTALS_CSV_PATH`. The sample file at `config/fundamentals.example.csv` includes:

- `symbol`
- `sector`
- `market_cap_bucket`
- `revenue_growth_pct`
- `eps_growth_pct`
- `roe_pct`
- `roce_pct`
- `debt_to_equity`
- `net_margin_pct`
- `promoter_holding_pct`

The scanner converts these into a `fundamental_score`, keeps the existing technical score as `technical_score`, and then creates a composite `total_score` using:

- `COMPOSITE_TECHNICAL_WEIGHT`
- `COMPOSITE_FUNDAMENTAL_WEIGHT`

Zerodha token helper:

```bash
python -m app.auth.zerodha_token --redirect-url "https://your-app.streamlit.app/" --show-login-url
python -m app.auth.zerodha_token --request-token "paste_request_token_here"
```

The second command saves the new `ZERODHA_ACCESS_TOKEN` into `.env`.

## Running the scanner

```bash
python -m app.main --scan-eod
```

Scan all NSE cash equities instead of the manual watchlist:

```bash
python -m app.main --scan-eod --universe-mode nse_equities --symbol-limit 500
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

The dashboard now uses a top workspace selector instead of a sidebar radio list. The main workspaces are:

1. Technical Scanner
2. Fundamental Scores
3. Signal History
4. Backtest Summary
5. BOS + FVG Analyzer
6. Stock Alerter

Inside `Technical Scanner`, you can switch between:

1. All scanned stocks
2. Top breakouts today
3. Near-breakouts
4. Failed breakouts

The sidebar scanner lets you choose between:

- `Manual watchlist`
- `All NSE equities`

For large universes, use the `Symbol limit` control to cap scan size.
You can also filter the dashboard by composite, technical, and fundamental minimum scores.

## BOS + FVG Analyzer

The dashboard includes a dedicated `BOS + FVG Analyzer` page for multi-symbol screening and detailed single-stock chart work. It is intentionally separate from the main breakout scanner so the technical BOS/FVG workflow stays independent from the end-of-day ranking workflow.

The analyzer supports:

- Default watchlists for `NIFTY 50` and `BANKNIFTY majors`
- Custom comma-separated tickers and CSV uploads
- Timeframes `5m`, `15m`, `1h`, `4h`, and `1d`
- BOS/CHoCH structure detection, swing highs/lows, breakout levels, and fair value gaps
- Plotly candlestick charts with FVG rectangles and structure annotations
- 5-year single-stock analysis on the daily timeframe

Notes:

- `1d` is the recommended interval for the full 5-year pattern study.
- Intraday Yahoo Finance intervals can return shorter history windows, so the app clamps those requests and shows a notice when that happens.

## Stock Alerter

The dashboard also includes a dedicated `Stock Alerter` page focused on high-quality bullish breakout candidates with transparent rule-based scoring and optional Telegram delivery.

Highlights:

- Default universe: `NIFTY LargeMidcap 250`, sourced from official NSE index constituent CSVs by combining `NIFTY 100` and `NIFTY Midcap 150`
- Alternate universe: `NASDAQ Top 250`, sourced from the official Nasdaq stock screener API with a bundled fallback snapshot
- Pattern modules for range breakouts, ascending triangles, bull flags, cup-and-handle approximations, major swing highs, 52-week highs, bullish BOS, bullish FVGs, and BOS+FVG continuation breakouts
- Trend, momentum, candle-quality, relative-strength, retest, BOS, and FVG confirmations
- Score categories: `A+ Breakout`, `A Breakout`, `Watchlist`, and `Reject / ignore`
- Duplicate-alert prevention backed by local JSON persistence
- Telegram alerts driven by `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

Add these when you want Telegram alerts:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
STOCK_ALERTER_ALERT_HISTORY_PATH=data/stock_alerter_alerts.json
```

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
