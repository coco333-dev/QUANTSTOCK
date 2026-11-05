# QUANTSMART VN — Full Quant Platform

**Version:** 1.1.0  
**Deployment target:** one Render Python Web Service, one public website origin, one FastAPI application serving both UI and API.

## Product modules

1. **Overview** — latest close, daily change, RSI, EMA structure, daily price chart and recent OHLCV.
2. **Market Analysis** — VNStock daily bars, EMA/RSI/ATR/Bollinger Bands, data table, CSV import and persistent local cache.
3. **Strategy Lab** — EMA crossover, trend + RSI confirmation and RSI reversal templates with configurable parameters, signal preview, entry/exit ledger and price chart markers.
4. **Backtest Lab** — long-only cash-account simulation, integer shares, fees, slippage, stop/target handling using daily OHLC, trade ledger, equity curve, drawdown, CAGR, Sharpe, win rate and profit factor. Optional benchmark return.
5. **Rolling OOS** — chronological out-of-sample folds with warm-up history and fixed strategy parameters. This is an OOS evaluation, not per-fold parameter re-optimization.
6. **Portfolio Lab** — long-only mean-variance optimization, efficient-frontier samples, return correlation matrix and approximate risk contribution.
7. **Risk Management** — annualized volatility, historical VaR/CVaR at 90/95/99%, downside deviation, skewness/kurtosis, positive-day ratio, benchmark beta and correlation.
8. **Research Archive** — SQLite persistence for backtest, rolling OOS and portfolio run metadata/results.

## Architecture

```text
Browser (HTML/CSS/JS + Plotly)
          │ same origin
          ▼
FastAPI application (Render Web Service)
  ├── routers/       HTTP endpoints
  ├── providers/     VNStock + CSV adapters
  ├── engines/       indicators, backtest, risk, portfolio
  ├── services/      SQLite cache and research archive
  └── static/        complete frontend
          │
          ▼
Render persistent disk (/var/data)
```

## Deploy on Render

For Vietnamese step-by-step instructions, see [`docs/DEPLOY_RENDER_VI.md`](docs/DEPLOY_RENDER_VI.md).

1. Create a GitHub repository and upload the **contents** of this project folder to the repository root (so `render.yaml` is at the root).
2. In Render, select **New → Blueprint**, connect the repository and apply the Blueprint.
3. The Blueprint creates one Python Web Service in Singapore and a 1 GB persistent disk mounted at `/var/data`.
4. Set `APP_PASSWORD` to a strong site-wide password. If the VNStock endpoint/account tier requires authentication, set `VNSTOCK_API_KEY` too. Never commit secrets into GitHub.
5. Wait for deploy, then open the Render `onrender.com` URL. `/api/health` is the health-check endpoint and `/docs` exposes the API schema (both require the site password except health).

The Blueprint uses a paid `0.5c-512mb` compute plan because Render persistent disks are available only on paid services. Check the current plan and disk pricing in your Render account before applying it. The service is intentionally configured as a single instance because a Render persistent disk cannot be shared by multiple instances.

### Manual Web Service alternative

- Runtime: Python
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check: `/api/health`
- Attach a persistent disk mounted at `/var/data`
- Environment variables:
  - `DATABASE_PATH=/var/data/quantsmart.db`
  - `APP_PASSWORD=<strong password>`
  - `VNSTOCK_API_KEY=<key if required>`

## Run locally

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## VNStock and data conventions

- Installs VNStock v5 from the official package index configured in `requirements.txt`.
- Equities use `Market().equity(symbol).ohlcv(...)`.
- Known Vietnamese indices (VNINDEX, VN30, HNXINDEX, HNX30, UPCOMINDEX) use `Market().index(symbol).ohlcv(...)` and are **not** converted to VND.
- Domestic stock prices reported in thousand VND are converted to VND when the median close indicates that unit. CSV input is expected to already be in VND.
- CSV upload stores the selected ticker/date range in the SQLite cache. It can then be selected in the analysis modules for that covered period.
- Cached recent ranges refresh after 24 hours; older market ranges are cached for 30 days. Explicit refresh bypasses the cache. The application limits daily-history requests to eight years to align with the currently documented VNStock community-tier history window; actual row limits can also depend on account tier and provider policy.
- VNStock account tier, API key, request quota and data history may affect availability. Verify provider responses before using the data in a research conclusion.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Render health check and package status |
| GET | `/api/market-data` | OHLCV and technical indicators |
| POST | `/api/upload-csv` | Validate and cache a CSV data range |
| POST | `/api/strategy-preview` | Completed-bar strategy signals and signal ledger |
| POST | `/api/backtest` | Historical strategy simulation |
| POST | `/api/walk-forward` | Fixed-parameter rolling OOS evaluation |
| POST | `/api/portfolio-optimize` | Long-only mean-variance optimizer |
| GET | `/api/risk` | Risk statistics and optional benchmark analysis |
| GET | `/api/saved-runs` | Recent research runs |
| GET | `/api/saved-runs/{run_id}` | Full saved result |
| GET | `/docs` | Interactive API documentation |

## Quality checks

The project includes automated tests for API routes, indicator calculations, provider normalization, backtesting, persistence, portfolio optimization and risk statistics. The current development build passes 15 tests. Live VNStock connectivity must still be verified after deployment with the user's actual network/account and API entitlement.

```bash
python -m compileall -q app tests
python -m pytest -q
```

## Research limitations

This is a research and education platform, not a brokerage, order execution system or investment-advice service.

- Backtesting is daily-bar, long-only, one symbol at a time, with integer shares and no leverage. It does not fully model Vietnamese board lots, tick sizes, price ceilings/floors, taxes, exchange fees, corporate actions, liquidity or market impact.
- Stop-loss/take-profit logic uses OHLC ranges. If both barriers are touched within one daily candle, the engine assumes the stop is hit first. Intraday order path and queue priority are unknowable from daily bars.
- Signal generation occurs at close and entries/exits execute at the next session open. The last open position is liquidated at the final close for reporting.
- Rolling OOS keeps the selected parameters fixed across folds. It does not perform nested optimization or hyperparameter tuning. Use a separate training-only optimization process before claiming a fully tuned walk-forward study.
- Portfolio optimization uses historical sample mean/covariance, which are noisy and unstable. It is long-only and fully invested; it does not include transaction costs, turnover limits, robust optimization or rebalancing simulation.
- SQLite with a persistent disk is intended for one service instance and a small private research workspace. It is not multi-user isolation or enterprise-grade concurrent storage. Add managed PostgreSQL and user-level authentication before sharing with multiple users.
- The optional Basic Auth password is a single site-wide gate, not individual user accounts or role-based access control. Keep the app private and do not store sensitive client information.
- No live streaming, automated trading, alert engine, corporate-action adjustment, delisted-ticker survivorship controls or formal model governance is included.
