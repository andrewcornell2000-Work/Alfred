# Quant Intelligence System

A live trading analysis engine running as a local Flask API (port 5000).
Alfred routes QUANT-category queries directly to it — no Claude/Codex dispatch needed.

## What it tracks
Configurable stock list (default: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, SPY, QQQ, SMCI).

## Signals (8-factor edge model, weights sum to 1.0)
| Signal | Weight | Source |
|---|---|---|
| Markov regime | 0.18 | 3-state HMM (Bull/Sideways/Bear) |
| Momentum | 0.18 | RSI, MACD, price trend |
| Mean reversion | 0.14 | RSI extremes + Bollinger Band position |
| News sentiment | 0.14 | VADER + financial lexicon |
| Institutional flow | 0.10 | Insider transactions, 13F, short interest, analyst ratings |
| Volatility | 0.10 | ATR-based position sizing |
| Market breadth | 0.08 | Advance/decline, sector rotation |
| Risk | 0.08 | ATR stops, Kelly sizing |

Trade status gates: requires ≥ 3 independent signal confirmations for ACTIVE status.

## API endpoints Alfred calls
- `/api/analyze/<ticker>` — full analysis snapshot
- `/api/backtest/<ticker>` — historical strategy performance
- `/api/institutional/<ticker>` — smart-money composite score (0–100)
- `/api/opportunities` — scan all stocks, returns edge scores + status
- `/api/macro` — macro regime (Bayesian 5-agent softmax)
- `/api/paper` — paper trading P&L and open positions
- `/api/alerts` — recent trade alerts
- `/api/learning` — signal reliability, Brier score, weight recommendations
- `/api/refresh` — invalidate data cache

## Output scores
- **Edge score**: 0–100 (>60 = LONG bias, <40 = SHORT bias)
- **Institutional flow score**: 0–100 (smart-money composite)
- **Trade status**: INACTIVE / WATCH / ACTIVE / HIGH_CONVICTION
- **Smart money bias**: BEARISH / MILDLY_BEARISH / NEUTRAL / MILDLY_BULLISH / BULLISH

## Example Alfred queries
- "analyze NVDA" → full snapshot with all 8 signals
- "what are the best opportunities right now" → scan all tracked stocks
- "show me smart money on AAPL" → institutional flow detail
- "how is the paper portfolio doing" → P&L and open positions
- "backtest MSFT" → historical win rate and Sharpe
- "what's the macro look like" → regime and breadth
- "show learning stats" → which signals are working, weight recommendations
