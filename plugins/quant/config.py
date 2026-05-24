STOCKS = ["NVDA", "TSLA", "QQQ"]

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 300

# Technical signal weights (must sum to 1.0)
INDICATOR_WEIGHTS = {
    "rsi":      0.20,
    "macd":     0.25,
    "ma":       0.25,
    "momentum": 0.15,
    "bb":       0.10,
    "volume":   0.05,
}

# Regime log-odds update strengths.
# Target: all signals max-bullish → ~70-75% bullish probability.
# logit(0.72) ≈ 0.94, so realistic bull_logit ceiling ≈ 1.0.
REGIME_WEIGHTS = {
    # Price-based signals
    "technical_score": 0.80,  # RSI+MACD+MA+momentum+BB composite
    "momentum_20d":    0.80,  # raw 20-day return (non-overlapping with tech)
    # New independent agents
    "options_score":   0.60,  # P/C ratio + IV skew
    "macro_score":     0.50,  # VIX + yields + dollar + gold + SPY
    "sentiment_score": 0.40,  # news headline VADER score
    "markov_score":    0.40,  # Markov: P(Bull|state) - P(Bear|state)
    # Risk dampening
    "vol_risk":        0.50,  # penalty when volatility is spiking
}

import os
PORT = int(os.environ.get("PORT", 5000))

# Risk / position sizing defaults (overridable via /api/settings)
RISK_DEFAULTS = {
    "account_balance":           10000.0,   # $ paper account size
    "risk_per_trade_percent":    1.0,        # % of balance risked per trade
    "max_position_percent":      25.0,       # max % of balance in one position
    "max_leverage":              2.0,        # max position/balance ratio
    "atr_multiplier":            1.5,        # ATR x mult = stop distance
    "minimum_risk_reward_ratio": 1.5,        # minimum RR to accept a trade
}
