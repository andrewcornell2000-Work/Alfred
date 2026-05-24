"""
Options flow agent: derives institutional sentiment from the live options chain.

Metrics:
  - Put/Call ratio (volume-weighted, then OI-weighted)
  - Average implied volatility (calls vs puts)
  - IV skew (put IV - call IV near ATM) — positive = market buying protection
  - Max pain strike (strike where total open interest loss is minimised for holders)

Signal: bullish when calls dominate volume and IV skew is low.
"""

import numpy as np
import pandas as pd
import yfinance as yf
import time

_cache: dict = {}
_CACHE_TTL = 300  # 5 minutes


def _get_chain(ticker: str, expiry: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    key = f"{ticker}|{expiry}"
    now = time.time()
    if key in _cache:
        data, ts = _cache[key]
        if now - ts < _CACHE_TTL:
            return data

    tk    = yf.Ticker(ticker)
    chain = tk.option_chain(expiry)
    calls = chain.calls.copy()
    puts  = chain.puts.copy()

    for col in ["volume", "openInterest"]:
        calls[col] = pd.to_numeric(calls[col], errors="coerce").fillna(0)
        puts[col]  = pd.to_numeric(puts[col],  errors="coerce").fillna(0)

    for col in ["impliedVolatility"]:
        calls[col] = pd.to_numeric(calls[col], errors="coerce").fillna(np.nan)
        puts[col]  = pd.to_numeric(puts[col],  errors="coerce").fillna(np.nan)

    _cache[key] = ((calls, puts), now)
    return calls, puts


def _pick_expiry(expirations: tuple) -> str | None:
    """
    Skip very-near-dated expiries (<5 calendar days away); use the
    first expiry at least 5 days out with meaningful volume.
    """
    import datetime
    today = datetime.date.today()
    for exp in expirations:
        try:
            exp_date = datetime.date.fromisoformat(exp)
            if (exp_date - today).days >= 5:
                return exp
        except Exception:
            continue
    return expirations[0] if expirations else None


def _max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> float:
    """
    Strike at which total option holders lose the most money
    (market makers' target pin at expiry).
    """
    strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
    losses  = []
    for s in strikes:
        call_loss = (calls[calls["strike"] < s]["openInterest"]
                     * (s - calls[calls["strike"] < s]["strike"])).sum()
        put_loss  = (puts[puts["strike"] > s]["openInterest"]
                     * (puts[puts["strike"] > s]["strike"] - s)).sum()
        losses.append(call_loss + put_loss)

    if not losses:
        return 0.0
    return float(strikes[int(np.argmin(losses))])


def analyze(ticker: str) -> dict:
    try:
        tk          = yf.Ticker(ticker)
        expirations = tk.options
        if not expirations:
            raise ValueError("No options expirations found")

        expiry = _pick_expiry(expirations)
        if expiry is None:
            raise ValueError("No suitable expiry found")

        calls, puts = _get_chain(ticker, expiry)

        # ── Volume P/C ratio ──────────────────────────────────────────────────
        call_vol = calls["volume"].sum()
        put_vol  = puts["volume"].sum()
        pc_vol   = float(put_vol / (call_vol + 1e-10))

        # ── OI P/C ratio ─────────────────────────────────────────────────────
        call_oi = calls["openInterest"].sum()
        put_oi  = puts["openInterest"].sum()
        pc_oi   = float(put_oi / (call_oi + 1e-10))

        # ── IV levels ─────────────────────────────────────────────────────────
        call_iv_mean = float(calls["impliedVolatility"].mean(skipna=True) * 100)
        put_iv_mean  = float(puts["impliedVolatility"].mean(skipna=True) * 100)
        iv_skew      = round(put_iv_mean - call_iv_mean, 2)  # + = fear

        # ── Max pain ─────────────────────────────────────────────────────────
        mp = _max_pain(calls, puts)

        # ── Score: P/C volume is the primary signal ───────────────────────────
        if pc_vol < 0.5:
            pc_score = 0.6
        elif pc_vol < 0.7:
            pc_score = 0.35
        elif pc_vol < 0.9:
            pc_score = 0.10
        elif pc_vol < 1.1:
            pc_score = -0.05
        elif pc_vol < 1.5:
            pc_score = -0.30
        else:
            pc_score = -0.55

        # IV skew adjustment (high put IV = hedging demand = mild bearish)
        if iv_skew > 8:
            skew_adj = -0.25
        elif iv_skew > 4:
            skew_adj = -0.12
        elif iv_skew < -4:
            skew_adj = 0.12
        else:
            skew_adj = 0.0

        options_score = float(np.clip(pc_score + skew_adj, -1.0, 1.0))

        if options_score > 0.2:
            signal = "BULLISH"
        elif options_score < -0.2:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        return {
            "expiry":          expiry,
            "pc_ratio_vol":    round(pc_vol,  3),
            "pc_ratio_oi":     round(pc_oi,   3),
            "call_iv":         round(call_iv_mean, 1),
            "put_iv":          round(put_iv_mean,  1),
            "iv_skew":         round(iv_skew, 2),
            "max_pain":        round(mp, 2),
            "call_volume":     int(call_vol),
            "put_volume":      int(put_vol),
            "options_score":   round(options_score, 4),
            "signal":          signal,
            "error":           None,
        }

    except Exception as e:
        return {
            "expiry": None, "pc_ratio_vol": 1.0, "pc_ratio_oi": 1.0,
            "call_iv": 0.0, "put_iv": 0.0, "iv_skew": 0.0, "max_pain": 0.0,
            "call_volume": 0, "put_volume": 0,
            "options_score": 0.0, "signal": "NEUTRAL", "error": str(e),
        }
