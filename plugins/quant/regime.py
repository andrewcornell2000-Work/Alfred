"""
Probabilistic regime detection — 5-agent log-odds Bayesian update.

Evidence sources:
  1. technical_score   (RSI + MACD + MA + momentum + BB)
  2. momentum_20d      (raw 20-day price return — not fully captured by tech score)
  3. options_score     (P/C ratio + IV skew)
  4. macro_score       (VIX + yields + dollar + gold + SPY)
  5. sentiment_score   (news headline VADER)

Each source nudges log-odds(bullish vs neutral) symmetrically.
Softmax over [bull_logit, 0, -bull_logit] gives 3-class probabilities.
"""

import numpy as np
from fetcher import fetch_ohlcv
from config import REGIME_WEIGHTS


def _softmax3(a: float, b: float, c: float):
    arr = np.array([a, b, c], dtype=float)
    arr -= arr.max()
    e = np.exp(arr)
    return e / e.sum()


def detect(technical: dict, risk: dict, options: dict, sentiment: dict, ticker: str, markov: dict = None) -> dict:
    df    = fetch_ohlcv(ticker, period="1y", interval="1d")
    close = df["Close"]
    rets  = close.pct_change().dropna()

    ts           = technical["technical_score"]
    mom20        = (close.iloc[-1] - close.iloc[-21]) / (close.iloc[-21] + 1e-10) if len(close) > 21 else 0.0
    opt_score    = options.get("options_score",  0.0)
    sent_score   = sentiment.get("score",        0.0)
    markov_score = (markov or {}).get("markov_score", 0.0)
    mk_regime    = (markov or {}).get("current_regime", "Unknown")

    # Volatility expansion penalty (0 → 1)
    vol_risk = 0.0
    if risk["vol_expanding"] and risk["vol_20d_ann"] > 40:
        vol_risk = min((risk["vol_20d_ann"] - 40) / 40.0, 1.0)

    W = REGIME_WEIGHTS
    bull_lo = (
        ts           * W["technical_score"]  +
        mom20        * W["momentum_20d"]     +
        opt_score    * W["options_score"]    +
        0.0          * W["macro_score"]      +  # macro is market-wide, shown separately
        sent_score   * W["sentiment_score"]  +
        markov_score * W["markov_score"]     -
        vol_risk     * W["vol_risk"]
    )

    bull_p, side_p, bear_p = _softmax3(bull_lo, 0.0, -bull_lo)

    # Floor at 5 % and renormalise
    bull_p = max(bull_p, 0.05)
    side_p = max(side_p, 0.05)
    bear_p = max(bear_p, 0.05)
    total  = bull_p + side_p + bear_p
    bull_p /= total
    side_p /= total
    bear_p /= total

    probs  = {"bullish": bull_p, "sideways": side_p, "bearish": bear_p}
    regime = max(probs, key=probs.get)
    max_p  = probs[regime]

    confidence = "HIGH" if max_p > 0.60 else ("MEDIUM" if max_p > 0.48 else "LOW")

    labels = {
        "bullish": "Bullish Trend",
        "sideways": "Sideways / Choppy",
        "bearish": "Bearish Trend",
    }
    biases = {
        "bullish": "Long-biased. Favour longs, avoid unhedged shorts.",
        "sideways": "Neutral. Range-trading. Await directional catalyst.",
        "bearish": "Defensive. Reduce longs, consider protective hedges.",
    }

    # ── Narrative builders ───────────────────────────────────────────────────
    drivers      = []
    risk_factors = []

    if ts > 0.2:
        drivers.append(f"Strong technical score ({ts:+.2f})")
    elif ts < -0.2:
        drivers.append(f"Weak technical score ({ts:+.2f})")

    if mom20 > 0.04:
        drivers.append(f"Positive 20d momentum (+{mom20*100:.1f}%)")
    elif mom20 < -0.04:
        drivers.append(f"Negative 20d momentum ({mom20*100:.1f}%)")

    if technical["above_ma20"] and technical["above_ma50"] and technical["above_ma200"]:
        drivers.append("Price above 20 / 50 / 200-day MAs")
    elif not technical["above_ma20"] and not technical["above_ma50"]:
        drivers.append("Price below 20 / 50-day MAs")

    opt_sig = options.get("signal", "NEUTRAL")
    if opt_sig == "BULLISH":
        drivers.append(f"Bullish options flow (P/C {options.get('pc_ratio_vol', 1):.2f})")
    elif opt_sig == "BEARISH":
        risk_factors.append(f"Bearish options flow (P/C {options.get('pc_ratio_vol', 1):.2f})")

    sent_sig = sentiment.get("signal", "NEUTRAL")
    if sent_sig == "BULLISH":
        drivers.append(f"Positive news sentiment (score {sent_score:+.2f})")
    elif sent_sig == "BEARISH":
        risk_factors.append(f"Negative news sentiment (score {sent_score:+.2f})")

    if markov_score > 0.25:
        drivers.append(f"Markov: {mk_regime} → Bull transition favored ({markov_score:+.2f})")
    elif markov_score < -0.25:
        risk_factors.append(f"Markov: {mk_regime} → Bear transition favored ({markov_score:+.2f})")

    if risk["vol_20d_ann"] > 40:
        risk_factors.append(f"Elevated volatility ({risk['vol_20d_ann']:.1f}% ann.)")
    if risk["vol_expanding"]:
        risk_factors.append(f"Volatility expanding (ratio {risk['vol_ratio']:.2f}×)")
    if risk["max_drawdown_60d"] < -12:
        risk_factors.append(f"Recent drawdown ({risk['max_drawdown_60d']:.1f}%)")

    # Agent score summary (for UI display)
    agent_scores = {
        "technical":  round(float(ts), 3),
        "momentum":   round(float(mom20), 4),
        "options":    round(float(opt_score), 3),
        "sentiment":  round(float(sent_score), 3),
        "markov":     round(float(markov_score), 3),
    }

    return {
        "regime":         regime,
        "regime_label":   labels[regime],
        "confidence":     confidence,
        "bullish_prob":   round(bull_p * 100, 1),
        "sideways_prob":  round(side_p * 100, 1),
        "bearish_prob":   round(bear_p * 100, 1),
        "bias":           biases[regime],
        "drivers":        drivers[:4],
        "risk_factors":   risk_factors[:4],
        "agent_scores":   agent_scores,
        "momentum_20d":   round(float(mom20 * 100), 2),
        "bull_logit":     round(float(bull_lo), 4),
    }
