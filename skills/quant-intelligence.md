# Quant Intelligence System

Alfred's Quant Intelligence plugin is a live trading analysis engine exposed through a Flask API. Alfred routes `QUANT` category requests directly to the API; it does not dispatch Quant questions to Claude Code or Codex.

## Location

- Plugin path: `plugins/quant`
- Flask entrypoint: `plugins/quant/app.py`
- Default port: `5000`
- Local base URL: `http://127.0.0.1:5000`
- Cloud/local override: `QUANT_BASE_URL`

## Setup Notes

Quant has its own dependencies:

```powershell
.venv\Scripts\activate
pip install -r plugins\quant\requirements.txt
```

Run locally:

```powershell
python plugins\quant\app.py
```

## What It Tracks

The stock universe is configured in `plugins/quant/config.py`.

Current default:

```text
NVDA, TSLA, QQQ
```

Update `STOCKS` in `config.py` to add or remove tickers.

## Signals

The trade engine uses an 8-factor edge model:

| Signal | Weight | Source |
|---|---:|---|
| Markov regime | 0.18 | 3-state Bull/Sideways/Bear transition model |
| Momentum / technical | 0.18 | RSI, MACD, moving averages, momentum, Bollinger Bands |
| Mean reversion | 0.14 | RSI extremes and Bollinger Band position |
| News sentiment | 0.14 | VADER plus financial lexicon over recent headlines |
| Institutional flow | 0.10 | Insider, institutional, short-interest, analyst, and options-derived signals |
| Volatility | 0.10 | Realized volatility and expansion checks |
| Market breadth / macro | 0.08 | VIX, yields, dollar, gold, SPY backdrop |
| Risk | 0.08 | ATR stops, position sizing, account/risk limits |

Trade status requires at least 3 independent confirmations for `ACTIVE` status.

## API Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/analyze/<ticker>` | Full technical, sentiment, options, risk, Markov, and regime snapshot |
| `/api/backtest/<ticker>` | Historical strategy performance |
| `/api/institutional/<ticker>` | Smart-money composite score |
| `/api/opportunities` | Scan configured tickers for trade opportunities |
| `/api/macro` | Broader market environment |
| `/api/paper` | Paper trading P/L and open positions |
| `/api/alerts` | Recent trade alerts |
| `/api/learning` | Signal reliability, calibration, mistake distribution, recommendations |
| `/api/refresh` | Clear data cache |

## Output Concepts

- **Final trade score:** 0-100 composite edge score
- **Direction:** `LONG`, `SHORT`, or `NO TRADE`
- **Status:** `NO TRADE`, `WATCHLIST`, `ACTIVE`, `HIGH CONVICTION`, `WEAKENING`, `EXIT`, or `INVALIDATED`
- **Institutional flow score:** 0-100 smart-money composite
- **Smart money bias:** bearish, neutral, or bullish label from institutional signals
- **Risk controls:** ATR stop, target, risk/reward, expected value, Kelly, safe Kelly, shares, capital required, leverage, max loss

## Example Alfred Queries

- `analyze NVDA`
- `what are the best opportunities right now`
- `show me smart money on TSLA`
- `how is the paper portfolio doing`
- `backtest QQQ`
- `what is the macro environment`
- `show learning stats`

## Routing Rule

If a user asks about stocks, tickers, trade opportunities, market analysis, institutional flow, options flow, alerts, paper trading, backtesting, or learning performance, classify as `QUANT` and use the Quant API path.
