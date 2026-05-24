import numpy as np
import pandas as pd
from fetcher import fetch_ohlcv
from config import INDICATOR_WEIGHTS


# ── Indicator math ────────────────────────────────────────────────────────────

def _rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    delta = prices.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / (loss + 1e-10)
    return 100 - (100 / (1 + rs))


def _macd(prices: pd.Series, fast=12, slow=26, signal=9):
    ema_f = prices.ewm(span=fast, adjust=False).mean()
    ema_s = prices.ewm(span=slow, adjust=False).mean()
    line = ema_f - ema_s
    sig = line.ewm(span=signal, adjust=False).mean()
    return line, sig, line - sig


def _bollinger(prices: pd.Series, period=20, n_std=2):
    ma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    return ma + n_std * std, ma, ma - n_std * std


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period=14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _rsi_score(rsi_val: float) -> float:
    """Maps RSI to a score in [-1, +1]."""
    if rsi_val < 30:
        return 0.6    # oversold → buy pressure
    if rsi_val < 45:
        return -0.3
    if rsi_val < 55:
        return 0.0
    if rsi_val < 70:
        return 0.5
    return -0.3       # overbought → potential reversal


def _ma_score(price: float, ma20: float, ma50: float, ma200: float) -> float:
    score = 0.0
    if price > ma20:
        score += 0.33
    if price > ma50:
        score += 0.33
    if price > ma200:
        score += 0.34
    if ma20 > ma50:
        score += 0.25
    # Normalize from [0, 1.25] to [-1, +1]
    return score * 2 - 1


def _macd_score(hist: pd.Series) -> float:
    cur = float(hist.iloc[-1])
    prev = float(hist.iloc[-2]) if len(hist) > 1 else 0.0
    if cur > 0 and prev <= 0:
        return 0.8    # bullish crossover
    if cur > 0:
        return 0.4
    if cur < 0 and prev >= 0:
        return -0.8   # bearish crossover
    return -0.4


def _momentum_score(close: pd.Series) -> float:
    if len(close) < 21:
        return 0.0
    m5  = (close.iloc[-1] - close.iloc[-6])  / (close.iloc[-6]  + 1e-10)
    m20 = (close.iloc[-1] - close.iloc[-21]) / (close.iloc[-21] + 1e-10)
    raw = m5 * 8 + m20 * 5
    return float(np.clip(raw, -1, 1))


def _bb_score(price: float, upper: float, lower: float) -> float:
    band = upper - lower + 1e-10
    pos = (price - lower) / band    # 0 = at lower, 1 = at upper
    if pos < 0.15:
        return 0.4    # near lower band → support
    if pos > 0.85:
        return -0.4   # near upper band → resistance
    return pos - 0.5  # linear centre


def _volume_score(close: pd.Series, volume: pd.Series) -> float:
    if len(volume) < 21:
        return 0.0
    avg_vol = volume.rolling(20).mean().iloc[-1]
    cur_vol = volume.iloc[-1]
    ratio = cur_vol / (avg_vol + 1e-10)
    if ratio < 1.2:
        return 0.0    # normal volume → no signal
    daily_chg = (close.iloc[-1] - close.iloc[-2]) / (close.iloc[-2] + 1e-10)
    return 0.4 if daily_chg > 0 else -0.4


# ── Main analysis function ────────────────────────────────────────────────────

def analyze(ticker: str) -> dict:
    df = fetch_ohlcv(ticker, period="1y", interval="1d")

    close  = df["Close"]
    high   = df["High"]
    low    = df["Low"]
    volume = df["Volume"]

    rsi_s    = _rsi(close)
    m_line, m_sig, m_hist = _macd(close)
    bb_up, bb_mid, bb_lo  = _bollinger(close)
    atr_s    = _atr(high, low, close)

    ma20  = close.rolling(20).mean()
    ma50  = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    cur       = float(close.iloc[-1])
    cur_rsi   = float(rsi_s.iloc[-1])
    cur_atr   = float(atr_s.iloc[-1])
    cur_ma20  = float(ma20.iloc[-1])
    cur_ma50  = float(ma50.iloc[-1])
    cur_ma200 = float(ma200.iloc[-1])
    cur_bb_up = float(bb_up.iloc[-1])
    cur_bb_lo = float(bb_lo.iloc[-1])
    cur_vol_r = float(volume.iloc[-1] / (volume.rolling(20).mean().iloc[-1] + 1e-10))

    scores = {
        "rsi":      _rsi_score(cur_rsi),
        "macd":     _macd_score(m_hist),
        "ma":       _ma_score(cur, cur_ma20, cur_ma50, cur_ma200),
        "momentum": _momentum_score(close),
        "bb":       _bb_score(cur, cur_bb_up, cur_bb_lo),
        "volume":   _volume_score(close, volume),
    }

    technical_score = sum(scores[k] * INDICATOR_WEIGHTS[k] for k in scores)

    daily_chg  = (cur - float(close.iloc[-2])) / (float(close.iloc[-2]) + 1e-10) * 100
    weekly_chg = (
        (cur - float(close.iloc[-6])) / (float(close.iloc[-6]) + 1e-10) * 100
        if len(close) > 5 else 0.0
    )

    history_close = close.iloc[-90:]
    history_dates = [d.strftime("%Y-%m-%d") for d in history_close.index]

    return {
        "ticker":           ticker,
        "price":            round(cur, 2),
        "daily_change_pct": round(daily_chg, 2),
        "weekly_change_pct":round(weekly_chg, 2),
        "rsi":              round(cur_rsi, 1),
        "macd":             round(float(m_line.iloc[-1]), 4),
        "macd_signal":      round(float(m_sig.iloc[-1]),  4),
        "macd_hist":        round(float(m_hist.iloc[-1]), 4),
        "atr":              round(cur_atr, 2),
        "atr_pct":          round(cur_atr / cur * 100, 2),
        "ma20":             round(cur_ma20, 2),
        "ma50":             round(cur_ma50, 2),
        "ma200":            round(cur_ma200, 2),
        "above_ma20":       bool(cur > cur_ma20),
        "above_ma50":       bool(cur > cur_ma50),
        "above_ma200":      bool(cur > cur_ma200),
        "bb_upper":         round(cur_bb_up, 2),
        "bb_lower":         round(cur_bb_lo, 2),
        "bb_mid":           round(float(bb_mid.iloc[-1]), 2),
        "volume_ratio":     round(cur_vol_r, 2),
        "scores":           {k: round(v, 3) for k, v in scores.items()},
        "technical_score":  round(float(technical_score), 4),
        "price_history":    [round(p, 2) for p in history_close.tolist()],
        "price_dates":      history_dates,
    }
