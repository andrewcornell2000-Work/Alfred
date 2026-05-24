"""
Macro agent: scores the broader market environment using freely available
yfinance data — no API key required.

Signals:
  VIX      → fear / complacency gauge
  ^TNX     → 10-year Treasury yield trend (rising = headwind for growth)
  DX-Y.NYB → US Dollar Index trend (strong dollar = headwind for multinationals)
  GLD      → Gold trend (rising gold = risk-off)
  SPY      → S&P 500 breadth / trend (market regime backdrop)
"""

import numpy as np
from fetcher import fetch_ohlcv

MACRO_SYMBOLS = {
    "vix":    "^VIX",
    "yield":  "^TNX",
    "dollar": "DX-Y.NYB",
    "gold":   "GLD",
    "spy":    "SPY",
}


def _score_vix(level: float, trend_20d: float) -> float:
    """VIX level + direction → score in [-1, +1]."""
    if level < 13:
        base = 0.60    # extreme complacency / risk-on
    elif level < 17:
        base = 0.30    # calm market
    elif level < 22:
        base = -0.10   # mildly elevated
    elif level < 28:
        base = -0.40   # elevated / cautious
    else:
        base = -0.70   # fear / panic

    # Rising VIX is an additional headwind
    trend_adj = -0.15 if trend_20d > 2.0 else (0.10 if trend_20d < -2.0 else 0.0)
    return float(np.clip(base + trend_adj, -1.0, 1.0))


def _score_yield(level: float, change_20d: float) -> float:
    """Rising yields = headwind for growth stocks."""
    if change_20d > 0.30:
        return -0.40
    if change_20d > 0.10:
        return -0.20
    if change_20d < -0.30:
        return 0.30   # falling yields = tailwind
    if change_20d < -0.10:
        return 0.15
    return 0.0


def _score_dollar(mom_20d: float) -> float:
    """Strong/rising dollar = mild headwind for US multinationals."""
    if mom_20d > 0.03:
        return -0.30
    if mom_20d > 0.01:
        return -0.10
    if mom_20d < -0.03:
        return 0.25   # weakening dollar = risk-on
    if mom_20d < -0.01:
        return 0.10
    return 0.0


def _score_gold(mom_20d: float) -> float:
    """Rapidly rising gold = risk-off / flight to safety."""
    if mom_20d > 0.04:
        return -0.25
    if mom_20d > 0.02:
        return -0.10
    if mom_20d < -0.04:
        return 0.15
    return 0.0


def _score_spy(close_series) -> float:
    """SPY trend acts as a market-backdrop multiplier."""
    cur  = float(close_series.iloc[-1])
    ma20 = float(close_series.rolling(20).mean().iloc[-1])
    ma50 = float(close_series.rolling(50).mean().iloc[-1])
    mom  = (cur - float(close_series.iloc[-21])) / (float(close_series.iloc[-21]) + 1e-10)

    score = 0.0
    if cur > ma20:  score += 0.20
    if cur > ma50:  score += 0.20
    score += float(np.clip(mom * 5, -0.40, 0.40))
    return float(np.clip(score, -0.80, 0.80))


def analyze() -> dict:
    results = {}
    errors  = {}

    for key, sym in MACRO_SYMBOLS.items():
        try:
            results[key] = fetch_ohlcv(sym, period="3mo", interval="1d")
        except Exception as e:
            errors[key] = str(e)

    # ── VIX ──────────────────────────────────────────────────────────────────
    if "vix" in results and not results["vix"].empty:
        vdf         = results["vix"]["Close"]
        vix_now     = float(vdf.iloc[-1])
        vix_20d_avg = float(vdf.rolling(20).mean().iloc[-1])
        vix_trend   = round(vix_now - vix_20d_avg, 2)
        vix_score   = _score_vix(vix_now, vix_trend)
    else:
        vix_now = vix_trend = 20.0; vix_score = -0.10

    # ── 10yr yield ───────────────────────────────────────────────────────────
    if "yield" in results and not results["yield"].empty:
        ydf           = results["yield"]["Close"]
        yield_now     = float(ydf.iloc[-1])
        yield_20d_chg = float(ydf.iloc[-1] - ydf.iloc[-20]) if len(ydf) >= 20 else 0.0
        yield_score   = _score_yield(yield_now, yield_20d_chg)
    else:
        yield_now = 4.5; yield_20d_chg = 0.0; yield_score = 0.0

    # ── Dollar ───────────────────────────────────────────────────────────────
    if "dollar" in results and not results["dollar"].empty:
        ddf      = results["dollar"]["Close"]
        dxy_now  = float(ddf.iloc[-1])
        dxy_mom  = (dxy_now - float(ddf.iloc[-21])) / (float(ddf.iloc[-21]) + 1e-10) if len(ddf) >= 21 else 0.0
        dxy_score = _score_dollar(dxy_mom)
    else:
        dxy_now = 100.0; dxy_mom = 0.0; dxy_score = 0.0

    # ── Gold ─────────────────────────────────────────────────────────────────
    if "gold" in results and not results["gold"].empty:
        gdf      = results["gold"]["Close"]
        gld_now  = float(gdf.iloc[-1])
        gld_mom  = (gld_now - float(gdf.iloc[-21])) / (float(gdf.iloc[-21]) + 1e-10) if len(gdf) >= 21 else 0.0
        gld_score = _score_gold(gld_mom)
    else:
        gld_now = 0.0; gld_mom = 0.0; gld_score = 0.0

    # ── SPY ──────────────────────────────────────────────────────────────────
    if "spy" in results and not results["spy"].empty:
        spy_score   = _score_spy(results["spy"]["Close"])
        spy_now     = float(results["spy"]["Close"].iloc[-1])
        spy_ma20    = float(results["spy"]["Close"].rolling(20).mean().iloc[-1])
        spy_above   = bool(spy_now > spy_ma20)
    else:
        spy_score = 0.0; spy_now = 0.0; spy_ma20 = 0.0; spy_above = True

    # ── Composite macro score ─────────────────────────────────────────────────
    macro_score = (
        vix_score   * 0.30 +
        yield_score * 0.25 +
        dxy_score   * 0.15 +
        gld_score   * 0.10 +
        spy_score   * 0.20
    )
    macro_score = float(np.clip(macro_score, -1.0, 1.0))

    if macro_score > 0.15:
        macro_signal = "BULLISH"
    elif macro_score < -0.15:
        macro_signal = "BEARISH"
    else:
        macro_signal = "NEUTRAL"

    return {
        "vix":               round(vix_now, 1),
        "vix_trend_20d":     round(vix_trend, 2),
        "vix_score":         round(vix_score, 3),
        "yield_10y":         round(yield_now, 3),
        "yield_change_20d":  round(yield_20d_chg, 3),
        "yield_score":       round(yield_score, 3),
        "dollar_index":      round(dxy_now, 2),
        "dollar_mom_20d_pct":round(dxy_mom * 100, 2),
        "dollar_score":      round(dxy_score, 3),
        "gold_price":        round(gld_now, 2),
        "gold_mom_20d_pct":  round(gld_mom * 100, 2),
        "gold_score":        round(gld_score, 3),
        "spy_price":         round(spy_now, 2),
        "spy_above_ma20":    spy_above,
        "spy_score":         round(spy_score, 3),
        "macro_score":       round(macro_score, 4),
        "macro_signal":      macro_signal,
        "errors":            errors,
    }
