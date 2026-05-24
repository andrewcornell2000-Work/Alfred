import numpy as np
import pandas as pd
from fetcher import fetch_ohlcv


def analyze(ticker: str) -> dict:
    df = fetch_ohlcv(ticker, period="1y", interval="1d")
    close   = df["Close"]
    returns = close.pct_change().dropna()

    # Realized volatility (annualized)
    vol_20 = float(returns.rolling(20).std().iloc[-1] * np.sqrt(252) * 100)
    vol_60 = float(returns.rolling(60).std().iloc[-1] * np.sqrt(252) * 100)

    # Vol expansion: short-term vs medium-term
    vol_ratio = float(
        returns.rolling(5).std().iloc[-1] /
        (returns.rolling(20).std().iloc[-1] + 1e-10)
    )

    # Max drawdown over the last 60 sessions
    recent = close.iloc[-60:]
    drawdown = (recent - recent.cummax()) / (recent.cummax() + 1e-10)
    max_dd   = float(drawdown.min() * 100)

    # Annualized return (last year)
    n_days   = len(returns)
    ann_ret  = float(returns.mean() * 252 * 100)

    # Sharpe (risk-free ≈ 5 %)
    rf_daily = 0.05 / 252
    excess   = returns - rf_daily
    sharpe   = float(excess.mean() / (excess.std() + 1e-10) * np.sqrt(252))

    # Distributional shape
    skewness = float(returns.skew())
    kurtosis = float(returns.kurtosis())   # excess kurtosis

    # Stress days: daily moves > 2σ in absolute value
    sigma      = returns.std()
    stress_ct  = int((returns.abs() > 2 * sigma).sum())

    # Composite risk score: 0 = extreme risk, 1 = calm
    vol_norm    = min(vol_20 / 60.0, 1.0)               # 60 % vol → 1.0
    kurt_risk   = min(max(kurtosis, 0) / 10.0, 1.0)     # pandas returns excess kurtosis
    vol_spike   = min(max(vol_ratio - 1.0, 0) / 2.0, 1.0)

    risk_score  = 1.0 - (vol_norm * 0.50 + kurt_risk * 0.25 + vol_spike * 0.25)
    risk_score  = float(np.clip(risk_score, 0.0, 1.0))

    if risk_score < 0.35:
        risk_level = "HIGH"
    elif risk_score < 0.65:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "vol_20d_ann":      round(vol_20, 1),
        "vol_60d_ann":      round(vol_60, 1),
        "vol_ratio":        round(vol_ratio, 2),
        "vol_expanding":    bool(vol_ratio > 1.2),
        "max_drawdown_60d": round(max_dd, 1),
        "annual_return":    round(ann_ret, 1),
        "sharpe":           round(sharpe, 2),
        "skewness":         round(skewness, 2),
        "kurtosis":         round(kurtosis, 2),
        "stress_days":      stress_ct,
        "risk_score":       round(risk_score, 4),
        "risk_level":       risk_level,
    }
