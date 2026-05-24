"""
Vectorised backtest: Long-only momentum strategy.

Signal: 1 (long) when RSI > 50 AND MACD > Signal AND price > MA20 AND price > MA50.
Execution: signal at close-of-day N enters at close-of-day N+1 (no lookahead).
Benchmark: buy-and-hold over the same window.
"""

import numpy as np
import pandas as pd
from fetcher import fetch_ohlcv


def _signals(df: pd.DataFrame) -> pd.Series:
    close = df["Close"]

    # RSI (14)
    delta = close.diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rsi   = 100 - 100 / (1 + gain / (loss + 1e-10))

    # MACD (12, 26, 9)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_sig  = macd_line.ewm(span=9, adjust=False).mean()

    # Moving averages
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()

    bull_count = (
        (rsi > 50).astype(int) +
        (macd_line > macd_sig).astype(int) +
        (close > ma20).astype(int) +
        (close > ma50).astype(int)
    )
    # Long when at least 3 of 4 conditions are met
    return (bull_count >= 3).astype(float)


def run(ticker: str) -> dict:
    df = fetch_ohlcv(ticker, period="2y", interval="1d")
    if len(df) < 60:
        return {"error": "Not enough data for backtest (need ≥ 60 days)."}

    close   = df["Close"]
    returns = close.pct_change()

    raw_sig = _signals(df)
    # Shift by 1 so we act on tomorrow's open-close with today's signal
    signal  = raw_sig.shift(1).fillna(0)

    strat_ret = signal * returns
    bh_ret    = returns

    # Drop leading NaN rows (warmup period)
    valid = signal.notna() & returns.notna() & (signal.index >= signal.first_valid_index())
    strat_ret = strat_ret[valid]
    bh_ret    = bh_ret[valid]
    signal    = signal[valid]

    n_days = len(strat_ret)
    n_years = max(n_days / 252, 1e-6)

    # Cumulative equity curves
    strat_cum = (1 + strat_ret).cumprod()
    bh_cum    = (1 + bh_ret).cumprod()

    # ── Strategy metrics ──────────────────────────────────────────────────────
    total_ret  = float(strat_cum.iloc[-1] - 1)
    ann_ret    = float((1 + total_ret) ** (1 / n_years) - 1)

    rf_daily   = 0.05 / 252
    excess     = strat_ret - rf_daily
    sharpe     = float(excess.mean() / (excess.std() + 1e-10) * np.sqrt(252))

    roll_max   = strat_cum.cummax()
    dd         = (strat_cum - roll_max) / (roll_max + 1e-10)
    max_dd     = float(dd.min())

    in_market  = signal == 1
    n_in       = int(in_market.sum())
    win_days   = int((strat_ret[in_market] > 0).sum())
    win_rate   = float(win_days / n_in) if n_in else 0.0

    # Profit factor
    wins   = strat_ret[in_market & (strat_ret > 0)].sum()
    losses = strat_ret[in_market & (strat_ret < 0)].abs().sum()
    pf     = float(wins / losses) if losses > 1e-10 else float("inf")

    # ── Buy-and-hold metrics ──────────────────────────────────────────────────
    bh_total = float(bh_cum.iloc[-1] - 1)
    bh_ann   = float((1 + bh_total) ** (1 / n_years) - 1)
    bh_roll  = bh_cum.cummax()
    bh_dd    = float(((bh_cum - bh_roll) / (bh_roll + 1e-10)).min())

    bh_excess = bh_ret - rf_daily
    bh_sharpe = float(bh_excess.mean() / (bh_excess.std() + 1e-10) * np.sqrt(252))

    return {
        "ticker":      ticker,
        "period_days": n_days,
        "strategy": {
            "total_return_pct":   round(total_ret * 100, 1),
            "annual_return_pct":  round(ann_ret   * 100, 1),
            "sharpe":             round(sharpe, 2),
            "max_drawdown_pct":   round(max_dd * 100, 1),
            "win_rate_pct":       round(win_rate * 100, 1),
            "profit_factor":      round(pf, 2),
            "days_in_market":     n_in,
            "time_in_market_pct": round(n_in / n_days * 100, 1),
        },
        "buy_hold": {
            "total_return_pct":  round(bh_total * 100, 1),
            "annual_return_pct": round(bh_ann   * 100, 1),
            "max_drawdown_pct":  round(bh_dd    * 100, 1),
            "sharpe":            round(bh_sharpe, 2),
        },
        "equity_curve":  [round(v, 4) for v in strat_cum.tolist()],
        "bh_curve":      [round(v, 4) for v in bh_cum.tolist()],
        "dates":         [d.strftime("%Y-%m-%d") for d in strat_cum.index],
    }
