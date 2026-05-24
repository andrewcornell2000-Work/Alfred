import time
import yfinance as yf
import pandas as pd
from config import CACHE_TTL

_cache: dict = {}


def _cache_get(key: str):
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return data
    return None


def _cache_set(key: str, data):
    _cache[key] = (data, time.time())


def fetch_ohlcv(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    key = f"{ticker}|{period}|{interval}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    tk = yf.Ticker(ticker)
    df = tk.history(period=period, interval=interval, auto_adjust=True)
    df = df.dropna(subset=["Close"])
    # Ensure timezone-naive index for clean date formatting
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)

    _cache_set(key, df)
    return df


def fetch_current_price(ticker: str) -> dict:
    key = f"{ticker}|price"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    df = fetch_ohlcv(ticker, period="5d", interval="1d")
    if df.empty:
        return {"price": 0, "change_pct": 0}

    close = df["Close"]
    price = float(close.iloc[-1])
    prev = float(close.iloc[-2]) if len(close) > 1 else price
    change_pct = (price - prev) / prev * 100 if prev else 0

    result = {"price": round(price, 2), "change_pct": round(change_pct, 2)}
    _cache_set(key, result)
    return result


def invalidate(ticker: str | None = None):
    """Clear cache for one ticker or all tickers."""
    if ticker is None:
        _cache.clear()
    else:
        for key in list(_cache.keys()):
            if key.startswith(ticker):
                del _cache[key]
