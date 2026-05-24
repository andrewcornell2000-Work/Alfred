"""
Trade Opportunity Engine — pure-math scoring, lifecycle management,
alert detection, paper trading, SQLite history, and risk/position sizing.
No LLM calls.
"""
import sqlite3
import os
import json
import math
from datetime import datetime, timezone

import aggregator
import macro_agent
import institutional_agent
import learning_engine
from config import RISK_DEFAULTS

DB_PATH       = os.environ.get("TRADE_ENGINE_DB_PATH", os.path.join(os.path.dirname(__file__), "trade_history.db"))
SETTINGS_PATH = os.environ.get("TRADE_ENGINE_SETTINGS_PATH", os.path.join(os.path.dirname(__file__), "risk_settings.json"))
ACTIVE_SCORE_THRESHOLD = 70.0

# ── Scoring weights (must sum to 1.0) ─────────────────────────────────────────
# Updated to include mean_reversion and institutional_flow as independent signals
_W = {
    "markov":         0.18,
    "technical":      0.18,   # momentum / technical composite
    "mean_reversion": 0.14,   # RSI + BB counter-trend signal
    "sentiment":      0.14,   # news sentiment
    "institutional":  0.10,   # institutional flow
    "volatility":     0.10,
    "breadth":        0.08,
    "risk":           0.08,
}

# Minimum independent signal confirmations required for ACTIVE status
_MIN_CONFIRMATIONS = 3

# ── Settings persistence ───────────────────────────────────────────────────────
def load_settings() -> dict:
    try:
        with open(SETTINGS_PATH) as f:
            overrides = json.load(f)
        return {**RISK_DEFAULTS, **overrides}
    except FileNotFoundError:
        return dict(RISK_DEFAULTS)
    except Exception:
        return dict(RISK_DEFAULTS)

def save_settings(data: dict) -> dict:
    merged = {**RISK_DEFAULTS, **{k: float(v) for k, v in data.items() if k in RISK_DEFAULTS}}
    with open(SETTINGS_PATH, "w") as f:
        json.dump(merged, f, indent=2)
    return merged

def get_settings() -> dict:
    return load_settings()

def update_settings(data: dict) -> dict:
    return save_settings(data)

# ── DB init / migration ────────────────────────────────────────────────────────
def _db():
    return sqlite3.connect(DB_PATH)

def _init_db():
    con = _db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS active_opportunities (
        ticker TEXT PRIMARY KEY,
        direction TEXT, confidence_score REAL, status TEXT,
        peak_score REAL, previous_score REAL, expected_horizon TEXT,
        current_regime TEXT, bullish_prob REAL, sideways_prob REAL, bearish_prob REAL,
        markov_score REAL, technical_score REAL, sentiment_score REAL,
        volatility_score REAL, risk_score REAL, market_breadth_score REAL,
        final_trade_score REAL, reason_summary TEXT, invalidation_condition TEXT,
        created_at TEXT, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS opportunity_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, ticker TEXT,
        bullish_prob REAL, sideways_prob REAL, bearish_prob REAL,
        final_trade_score REAL, technical_score REAL, sentiment_score REAL,
        volatility_score REAL, risk_score REAL, markov_score REAL,
        market_breadth_score REAL, direction TEXT, status TEXT,
        alert_triggered INTEGER DEFAULT 0, reason_summary TEXT
    );
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT, ticker TEXT, alert_type TEXT,
        message TEXT, confidence_score REAL, status TEXT, seen INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker TEXT, direction TEXT,
        entry_price REAL, entry_time TEXT,
        exit_price REAL, exit_time TEXT,
        confidence_score REAL, expected_horizon TEXT,
        reason_summary TEXT, status TEXT, pnl_pct REAL
    );
    """)
    con.commit()
    con.close()
    _migrate_db()

def _migrate_db():
    """Add new columns if not yet present (idempotent)."""
    con = _db()
    existing_opp   = {r[1] for r in con.execute("PRAGMA table_info(active_opportunities)").fetchall()}
    existing_paper = {r[1] for r in con.execute("PRAGMA table_info(paper_trades)").fetchall()}

    new_opp_cols = [
        "entry_price REAL", "stop_loss REAL", "target_price REAL",
        "risk_per_share REAL", "reward_per_share REAL", "rr_ratio REAL",
        "shares INTEGER", "capital_required REAL", "leverage_used REAL",
        "max_loss REAL", "account_risk_pct REAL",
        "expected_value REAL", "kelly_fraction REAL", "safe_kelly REAL",
        "win_prob REAL", "no_trade_reason TEXT",
        # New: institutional + mean reversion
        "mean_reversion_score REAL", "institutional_flow_score REAL",
        "momentum_score REAL", "smart_money_bias TEXT",
        "confirmation_count INTEGER", "institutional_warning TEXT",
    ]
    new_paper_cols = [
        "stop_loss REAL", "target_price REAL", "risk_per_share REAL",
        "reward_per_share REAL", "shares INTEGER", "capital_required REAL",
        "leverage_used REAL", "max_loss REAL", "account_risk_pct REAL",
        "rr_ratio REAL", "expected_value REAL", "kelly_fraction REAL",
        "safe_kelly REAL", "exit_reason TEXT", "hold_duration_h REAL",
        # New
        "mean_reversion_score REAL", "institutional_flow_score REAL",
        "momentum_score REAL",
    ]
    for col_def in new_opp_cols:
        col_name = col_def.split()[0]
        if col_name not in existing_opp:
            con.execute(f"ALTER TABLE active_opportunities ADD COLUMN {col_def}")
    for col_def in new_paper_cols:
        col_name = col_def.split()[0]
        if col_name not in existing_paper:
            con.execute(f"ALTER TABLE paper_trades ADD COLUMN {col_def}")
    con.commit()
    con.close()

_init_db()

# ── Normalisation helpers ─────────────────────────────────────────────────────
def _n11(x):
    """[-1, +1] → [0, 100]"""
    return max(0.0, min(100.0, (float(x) + 1.0) / 2.0 * 100.0))

def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(x)))

# ── Mean-reversion score (RSI + Bollinger) ────────────────────────────────────
def _mean_reversion_score(tech: dict) -> float:
    """
    Counter-trend signal from RSI oversold/overbought + Bollinger Band position.
    Returns 0-100 (>50 = mean-reversion opportunity to the upside).
    """
    rsi   = tech.get("rsi", 50.0)
    bb_u  = tech.get("bb_upper", 1e10)
    bb_l  = tech.get("bb_lower", 0.0)
    price = tech.get("price", 1.0)

    # RSI signal
    if rsi < 30:
        rsi_s = 0.80
    elif rsi < 40:
        rsi_s = 0.40
    elif rsi > 70:
        rsi_s = -0.80
    elif rsi > 60:
        rsi_s = -0.40
    else:
        rsi_s = (rsi - 50.0) / 25.0  # linear, centred at 0

    # Bollinger Band position signal
    band = bb_u - bb_l + 1e-10
    bb_pos = (price - bb_l) / band  # 0 = at lower, 1 = at upper
    if bb_pos < 0.10:
        bb_s = 0.80
    elif bb_pos < 0.25:
        bb_s = 0.40
    elif bb_pos > 0.90:
        bb_s = -0.80
    elif bb_pos > 0.75:
        bb_s = -0.40
    else:
        bb_s = 0.0

    raw = rsi_s * 0.60 + bb_s * 0.40
    return _clamp((raw + 1.0) / 2.0 * 100.0)


# ── Component scores ──────────────────────────────────────────────────────────
def _components(data: dict, macro: dict, inst_data: dict) -> dict:
    reg  = data["regime"]
    risk = data["risk"]
    mk   = data["markov"]
    tech = data["technical"]

    markov   = _n11(mk.get("markov_score", 0.0))
    momentum = _n11(reg["agent_scores"].get("technical", 0.0))
    mean_rev = _mean_reversion_score(tech)
    sent     = _n11(reg["agent_scores"].get("sentiment", 0.0))
    inst     = _clamp(inst_data.get("institutional_flow_score", 50.0))

    vol_ann = risk.get("vol_20d_ann", 30.0)
    vol_s   = _clamp(100.0 - (vol_ann - 10.0) / 70.0 * 100.0)
    if risk.get("vol_expanding"):
        vol_s *= 0.82
    vol_s = _clamp(vol_s)

    risk_s  = _clamp(risk.get("risk_score", 0.5) * 100.0)
    breadth = _n11(macro.get("macro_score", 0.0))

    return {
        "markov":         round(markov,   1),
        "technical":      round(momentum, 1),
        "mean_reversion": round(mean_rev, 1),
        "sentiment":      round(sent,     1),
        "institutional":  round(inst,     1),
        "volatility":     round(vol_s,    1),
        "risk":           round(risk_s,   1),
        "breadth":        round(breadth,  1),
    }


def _final_score(c: dict) -> float:
    s = (c["markov"]         * _W["markov"]         +
         c["technical"]      * _W["technical"]      +
         c["mean_reversion"] * _W["mean_reversion"] +
         c["sentiment"]      * _W["sentiment"]      +
         c["institutional"]  * _W["institutional"]  +
         c["volatility"]     * _W["volatility"]     +
         c["breadth"]        * _W["breadth"]        +
         c["risk"]           * _W["risk"])
    return round(s, 1)


# ── Signal confirmation count ─────────────────────────────────────────────────
def _count_confirmations(c: dict, direction: str) -> tuple[int, list[str]]:
    """
    Count how many independent signals confirm the trade direction.
    LONG: signal > 57 = confirms bullish.
    SHORT: signal < 43 = confirms bearish.
    Volatility/risk: > 55 confirms either direction (stable environment).
    """
    confirmed = []
    directional = ["markov", "technical", "mean_reversion", "sentiment", "institutional", "breadth"]
    environment = ["volatility", "risk"]

    for sig in directional:
        val = c.get(sig, 50.0)
        if direction == "LONG" and val >= 57:
            confirmed.append(sig)
        elif direction == "SHORT" and val <= 43:
            confirmed.append(sig)

    for sig in environment:
        if c.get(sig, 0.0) >= 55:
            confirmed.append(sig)

    return len(confirmed), confirmed


def _institutional_warning(c: dict, direction: str) -> str | None:
    """Return a warning string if institutional flow strongly disagrees with trade."""
    score = c.get("institutional", 50.0)
    if direction == "LONG" and score < 35:
        return f"Institutional flow bearish ({score:.0f}/100) — smart money disagrees"
    if direction == "SHORT" and score > 65:
        return f"Institutional flow bullish ({score:.0f}/100) — smart money disagrees"
    return None

# ── Risk / position sizing ─────────────────────────────────────────────────────
def _conf_multiplier(score: float) -> float:
    if score >= 85.0: return 1.0
    if score >= 75.0: return 0.75
    if score >= 70.0: return 0.5
    return 0.0

def _win_probability(direction: str, data: dict) -> float:
    reg = data["regime"]
    if direction == "LONG":
        return reg["bullish_prob"] / 100.0
    if direction == "SHORT":
        return reg["bearish_prob"] / 100.0
    return 0.5

def _positive_float(value, fallback: float) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        x = float(fallback)
    if not math.isfinite(x) or x <= 0:
        return float(fallback)
    return x

def _nonnegative_float(value, fallback: float = 0.0) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        x = float(fallback)
    if not math.isfinite(x) or x < 0:
        return float(fallback)
    return x

def _atr_stop_prices(
    entry_price: float,
    atr: float,
    direction: str,
    atr_multiplier: float,
    rr_ratio: float,
) -> dict:
    """Return ATR stop/target levels for a LONG or SHORT setup."""
    if direction not in ("LONG", "SHORT"):
        raise ValueError("direction must be LONG or SHORT")

    price = _positive_float(entry_price, 0.0)
    atr_v = _positive_float(atr, 0.0)
    mult = _positive_float(atr_multiplier, RISK_DEFAULTS["atr_multiplier"])
    rr = _positive_float(rr_ratio, RISK_DEFAULTS["minimum_risk_reward_ratio"])

    risk_per_share = round(atr_v * mult, 4)
    reward_per_share = round(risk_per_share * rr, 4)

    if direction == "LONG":
        stop_loss = round(price - risk_per_share, 4)
        target_price = round(price + reward_per_share, 4)
    else:
        stop_loss = round(price + risk_per_share, 4)
        target_price = round(price - reward_per_share, 4)

    return {
        "stop_loss": stop_loss,
        "target_price": target_price,
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "rr_ratio": round(rr, 2),
    }

def _expected_value(win_probability: float, risk_per_share: float, reward_per_share: float) -> float:
    win_p = _clamp(win_probability, 0.0, 1.0)
    risk = _nonnegative_float(risk_per_share, 0.0)
    reward = _nonnegative_float(reward_per_share, 0.0)
    return round(win_p * reward - (1.0 - win_p) * risk, 4)

def _kelly_fraction(win_probability: float, rr_ratio: float) -> float:
    win_p = _clamp(win_probability, 0.0, 1.0)
    rr = _positive_float(rr_ratio, 0.0)
    if rr <= 0:
        return 0.0
    return round(win_p - ((1.0 - win_p) / rr), 4)

def _position_sizing(data: dict, direction: str, score: float, cfg: dict) -> dict:
    """Compute ATR-based stop, target, position size, EV, and Kelly."""
    tech  = data["technical"]
    price = _positive_float(tech.get("price"), 0.0)
    atr_fallback = price * 0.015 if price > 0 else 0.0
    atr = _positive_float(tech.get("atr"), atr_fallback)

    mult = _positive_float(cfg.get("atr_multiplier"), RISK_DEFAULTS["atr_multiplier"])
    rr_min = _positive_float(
        cfg.get("minimum_risk_reward_ratio"),
        RISK_DEFAULTS["minimum_risk_reward_ratio"],
    )
    balance = _positive_float(cfg.get("account_balance"), RISK_DEFAULTS["account_balance"])
    risk_pct = _nonnegative_float(
        cfg.get("risk_per_trade_percent"),
        RISK_DEFAULTS["risk_per_trade_percent"],
    )

    tradeable_direction = direction in ("LONG", "SHORT")
    if tradeable_direction:
        stop = _atr_stop_prices(price, atr, direction, mult, rr_min)
        stop_loss = stop["stop_loss"]
        target_price = stop["target_price"]
        risk_per_share = stop["risk_per_share"]
        reward_per_share = stop["reward_per_share"]
        rr_ratio = stop["rr_ratio"]
    else:
        risk_per_share = round(atr * mult, 4)
        reward_per_share = round(risk_per_share * rr_min, 4)
        rr_ratio = round(rr_min, 2)
        stop_loss = None
        target_price = None

    conf_mult = _conf_multiplier(score) if tradeable_direction else 0.0
    risk_amt = balance * (risk_pct / 100.0) * conf_mult
    shares = int(risk_amt / risk_per_share) if risk_per_share > 0 else 0

    capital_req = round(shares * price, 2)
    leverage    = round(capital_req / balance, 2) if balance > 0 else 0.0
    max_loss    = round(shares * risk_per_share, 2)
    acct_risk   = round(max_loss / balance * 100.0, 2) if balance > 0 else 0.0

    win_p = _win_probability(direction, data) if tradeable_direction else 0.0
    ev = _expected_value(win_p, risk_per_share, reward_per_share) if tradeable_direction else 0.0

    kelly = _kelly_fraction(win_p, rr_ratio) if tradeable_direction else 0.0
    safe_kelly = round(min(max(0.0, kelly * 0.25), 0.25), 4)

    return {
        "entry_price":      round(price, 4),
        "stop_loss":        stop_loss,
        "target_price":     target_price,
        "risk_per_share":   risk_per_share,
        "reward_per_share": reward_per_share,
        "rr_ratio":         round(rr_ratio, 2),
        "shares":           shares,
        "capital_required": capital_req,
        "leverage_used":    leverage,
        "max_loss":         max_loss,
        "account_risk_pct": acct_risk,
        "expected_value":   ev,
        "kelly_fraction":   kelly,
        "safe_kelly":       safe_kelly,
        "win_prob":         round(win_p * 100.0, 1),
    }

def _portfolio_open_risk(ticker: str, direction: str, cfg: dict) -> dict:
    """Return portfolio-level open risk stats for limit checks."""
    con  = _db()
    rows = con.execute(
        "SELECT ticker, direction, max_loss, capital_required FROM paper_trades WHERE status='OPEN'"
    ).fetchall()
    con.close()
    balance  = cfg["account_balance"]
    total_r  = sum((r[2] or 0.0) for r in rows)
    same_cap = sum((r[3] or 0.0) for r in rows if r[1] == direction and r[0] != ticker)
    return {
        "total_open_risk_pct": round(total_r / balance * 100.0, 2) if balance else 0.0,
        "same_dir_cap":        round(same_cap, 2),
    }

def _no_trade_reason(
    data: dict, c: dict, direction: str, ticker: str,
    ps: dict, score: float, cfg: dict, confirmations: int = 0
) -> str | None:
    """Return a plain-text reason this is a NO TRADE, or None if tradeable."""
    reg    = data["regime"]
    bull_p = reg["bullish_prob"]
    bear_p = reg["bearish_prob"]
    side_p = reg["sideways_prob"]

    if score < 55.0:
        return f"Score {score:.0f} below minimum threshold (55)"
    if score < ACTIVE_SCORE_THRESHOLD:
        return f"Score {score:.0f} below active trade threshold ({ACTIVE_SCORE_THRESHOLD:.0f})"
    if c["risk"] < 40.0:
        return f"Risk score too low ({c['risk']:.0f}/100)"
    if c["volatility"] < 30.0:
        return f"Volatility environment unfavourable ({c['volatility']:.0f}/100)"
    if side_p >= bull_p and side_p >= bear_p:
        return f"Sideways regime dominant ({side_p:.0f}%)"
    if abs(bull_p - bear_p) < 5.0:
        return f"Bull/Bear too close ({bull_p:.0f}% vs {bear_p:.0f}%)"
    if ps["rr_ratio"] < cfg["minimum_risk_reward_ratio"]:
        return f"RR {ps['rr_ratio']:.2f} below minimum ({cfg['minimum_risk_reward_ratio']:.1f})"
    if ps["expected_value"] <= 0:
        return f"Negative EV (EV={ps['expected_value']:.4f}/share)"
    if ps["shares"] == 0:
        return "Position size rounds to 0 shares (ATR stop too wide for balance)"
    if ps["leverage_used"] > cfg["max_leverage"]:
        return f"Leverage {ps['leverage_used']:.2f}x exceeds max ({cfg['max_leverage']:.1f}x)"
    if confirmations < _MIN_CONFIRMATIONS:
        return f"Only {confirmations}/{_MIN_CONFIRMATIONS} signals confirm direction — insufficient agreement"
    pf = _portfolio_open_risk(ticker, direction, cfg)
    if pf["total_open_risk_pct"] >= 3.0:
        return f"Portfolio already at max open risk ({pf['total_open_risk_pct']:.1f}%)"
    new_cap_pct = ps["capital_required"] / cfg["account_balance"] * 100.0 if cfg["account_balance"] else 0.0
    same_pct = (pf["same_dir_cap"] + ps["capital_required"]) / cfg["account_balance"] * 100.0 if cfg["account_balance"] else 0.0
    if same_pct > 50.0:
        return f"Same-direction exposure would exceed 50% of capital"
    if new_cap_pct > cfg["max_position_percent"]:
        return f"Position {new_cap_pct:.0f}% exceeds max ({cfg['max_position_percent']:.0f}%)"
    return None

# ── Direction logic ───────────────────────────────────────────────────────────
def _direction(data: dict, c: dict, score: float) -> str:
    reg    = data["regime"]
    bull_p = reg["bullish_prob"]
    bear_p = reg["bearish_prob"]
    side_p = reg["sideways_prob"]

    if score < ACTIVE_SCORE_THRESHOLD or c["risk"] < 40.0 or c["volatility"] < 30.0:
        return "NO TRADE"
    if side_p >= bull_p and side_p >= bear_p:
        return "NO TRADE"
    if abs(bull_p - bear_p) < 5.0:
        return "NO TRADE"
    if bull_p > bear_p:
        return "LONG"
    return "SHORT"

# ── Horizon classification ────────────────────────────────────────────────────
def _horizon(c: dict) -> str:
    if c["volatility"] < 35.0 and abs(c["sentiment"] - 50.0) > 30.0:
        return "INTRADAY"
    if c["markov"] > 70.0 and c["volatility"] > 60.0 and c["technical"] > 65.0:
        return "1-2 WEEKS"
    if c["markov"] > 60.0 and c["technical"] > 55.0:
        return "2-5 DAYS"
    if abs(c["sentiment"] - 50.0) > 20.0:
        return "1-2 DAYS"
    return "2-5 DAYS"

# ── Lifecycle state ───────────────────────────────────────────────────────────
def _status(
    score: float, direction: str, peak: float, data: dict,
    no_trade_rsn: str | None, confirmations: int = 0,
) -> str:
    if direction == "NO TRADE" or no_trade_rsn is not None:
        return "NO TRADE"

    reg = data["regime"]
    if direction == "LONG"  and reg["bearish_prob"] > reg["bullish_prob"]  + 10.0:
        return "EXIT"
    if direction == "SHORT" and reg["bullish_prob"]  > reg["bearish_prob"] + 10.0:
        return "EXIT"

    if score < 55.0:
        return "INVALIDATED"
    if data["risk"]["risk_level"] == "HIGH" and data["risk"]["vol_expanding"]:
        return "INVALIDATED"
    if peak - score >= 10.0:
        return "WEAKENING"
    if score >= 85.0 and confirmations >= _MIN_CONFIRMATIONS:
        return "HIGH CONVICTION"
    if score >= 70.0 and confirmations >= _MIN_CONFIRMATIONS:
        return "ACTIVE"
    return "WATCHLIST"

# ── Reason summary ─────────────────────────────────────────────────────────────
def _reason(data: dict, c: dict, direction: str) -> str:
    reg   = data["regime"]
    parts = []
    if c["markov"] > 65.0:
        parts.append(f"Markov regime persistence ({c['markov']:.0f}/100)")
    elif c["markov"] < 40.0:
        parts.append(f"weak Markov signal ({c['markov']:.0f}/100)")
    if c["technical"] > 65.0:
        parts.append(f"strong technical momentum ({c['technical']:.0f}/100)")
    elif c["technical"] < 40.0:
        parts.append(f"weak technical setup ({c['technical']:.0f}/100)")
    if c["sentiment"] > 65.0:
        parts.append(f"positive news sentiment ({c['sentiment']:.0f}/100)")
    elif c["sentiment"] < 35.0:
        parts.append(f"negative news flow ({c['sentiment']:.0f}/100)")
    if c["risk"] < 45.0:
        parts.append(f"elevated risk conditions ({c['risk']:.0f}/100)")
    if c["volatility"] < 35.0:
        parts.append(f"high volatility environment ({c['volatility']:.0f}/100)")
    prefix = reg["regime_label"] + ". "
    body   = (", ".join(parts[:4]) + ".") if parts else "Mixed signals."
    return prefix + body[0].upper() + body[1:]

def _invalidation(direction: str) -> str:
    if direction == "LONG":
        return ("Exit if bearish probability exceeds bullish by 10%+, "
                "confidence drops below 55, or major negative news appears.")
    if direction == "SHORT":
        return ("Exit if bullish probability exceeds bearish by 10%+, "
                "confidence drops below 55, or strong positive catalyst appears.")
    return "No active setup — monitor for directional catalyst."

# ── Persistence ────────────────────────────────────────────────────────────────
_OPP_COLS = [
    "ticker","direction","confidence_score","status","peak_score","previous_score",
    "expected_horizon","current_regime","bullish_prob","sideways_prob","bearish_prob",
    "markov_score","technical_score","sentiment_score","volatility_score","risk_score",
    "market_breadth_score","final_trade_score","reason_summary","invalidation_condition",
    "created_at","updated_at",
    # risk / sizing fields
    "entry_price","stop_loss","target_price","risk_per_share","reward_per_share","rr_ratio",
    "shares","capital_required","leverage_used","max_loss","account_risk_pct",
    "expected_value","kelly_fraction","safe_kelly","win_prob","no_trade_reason",
    # new signals
    "mean_reversion_score","institutional_flow_score","momentum_score",
    "smart_money_bias","confirmation_count","institutional_warning",
]

def _load_prev(ticker: str) -> dict | None:
    con    = _db()
    pragma = con.execute("PRAGMA table_info(active_opportunities)").fetchall()
    cols   = [r[1] for r in pragma]
    row    = con.execute(
        "SELECT * FROM active_opportunities WHERE ticker=?", (ticker,)
    ).fetchone()
    con.close()
    return dict(zip(cols, row)) if row else None

def _save_opp(opp: dict):
    con    = _db()
    pragma = con.execute("PRAGMA table_info(active_opportunities)").fetchall()
    db_cols   = [r[1] for r in pragma]
    save_cols = [c for c in _OPP_COLS if c in db_cols]
    vals      = tuple(opp.get(k) for k in save_cols)
    upd       = ", ".join(f"{c}=excluded.{c}" for c in save_cols if c != "ticker")
    con.execute(
        f"INSERT INTO active_opportunities ({','.join(save_cols)}) "
        f"VALUES ({','.join('?'*len(save_cols))}) "
        f"ON CONFLICT(ticker) DO UPDATE SET {upd}",
        vals,
    )
    snap_cols = [
        "timestamp","ticker","bullish_prob","sideways_prob","bearish_prob",
        "final_trade_score","technical_score","sentiment_score","volatility_score",
        "risk_score","markov_score","market_breadth_score","direction","status","reason_summary",
    ]
    snap_vals = (
        opp["updated_at"], opp["ticker"],
        opp["bullish_prob"], opp["sideways_prob"], opp["bearish_prob"],
        opp["final_trade_score"], opp["technical_score"], opp["sentiment_score"],
        opp["volatility_score"], opp["risk_score"], opp["markov_score"],
        opp["market_breadth_score"], opp["direction"], opp["status"], opp["reason_summary"],
    )
    con.execute(
        f"INSERT INTO opportunity_snapshots ({','.join(snap_cols)}) VALUES ({','.join('?'*len(snap_cols))})",
        snap_vals,
    )
    con.commit()
    con.close()

# ── Alert detection ────────────────────────────────────────────────────────────
def _check_alerts(opp: dict, prev: dict | None) -> list[dict]:
    alerts = []
    now    = opp["updated_at"]
    t      = opp["ticker"]
    score  = opp["confidence_score"]
    status = opp["status"]

    def _a(atype, msg):
        alerts.append({"timestamp": now, "ticker": t, "alert_type": atype,
                        "message": msg, "confidence_score": score, "status": status})

    ep = opp.get("entry_price") or 0.0
    sl = opp.get("stop_loss") or 0.0
    tp = opp.get("target_price") or 0.0
    rr = opp.get("rr_ratio") or 0.0
    ev = opp.get("expected_value") or 0.0

    if prev is None:
        if status in ("ACTIVE", "HIGH CONVICTION"):
            _a("NEW_OPPORTUNITY",
               f"NEW TRADE OPPORTUNITY: {t} {opp['direction']}\n"
               f"Confidence: {score:.0f}%  |  Horizon: {opp['expected_horizon']}\n"
               f"Entry: ${ep:.2f}  Stop: ${sl:.2f}  Target: ${tp:.2f}\n"
               f"RR: {rr:.2f}  EV: ${ev:.4f}/share  Shares: {opp.get('shares', 0)}\n"
               f"Reason: {opp['reason_summary']}")
        elif status == "WATCHLIST":
            _a("WATCHLIST_ADDED", f"WATCHLIST: {t} {opp['direction']} added (score {score:.0f}%)")
        return alerts

    prev_score  = prev.get("confidence_score", 0.0)
    prev_status = prev.get("status", "")

    if status in ("ACTIVE","HIGH CONVICTION") and prev_status == "WATCHLIST":
        _a("NEW_OPPORTUNITY",
           f"NEW TRADE OPPORTUNITY: {t} {opp['direction']}\n"
           f"Confidence: {score:.0f}%  |  Horizon: {opp['expected_horizon']}\n"
           f"Entry: ${ep:.2f}  Stop: ${sl:.2f}  Target: ${tp:.2f}\n"
           f"RR: {rr:.2f}  EV: ${ev:.4f}/share  Shares: {opp.get('shares', 0)}")
    elif status in ("ACTIVE","HIGH CONVICTION") and score - prev_score >= 10.0:
        _a("OPPORTUNITY_STRENGTHENED",
           f"STRENGTHENED: {t} {opp['direction']} confidence now {score:.0f}% "
           f"(+{score - prev_score:.0f}pts)")
    elif status == "WEAKENING" and prev_status in ("ACTIVE","HIGH CONVICTION"):
        _a("OPPORTUNITY_WEAKENING",
           f"WEAKENING: {t} setup losing momentum (score {score:.0f}%, was {prev_score:.0f}%)")
    elif status == "EXIT" and prev_status in ("ACTIVE","HIGH CONVICTION","WEAKENING"):
        _a("EXIT_SIGNAL",
           f"EXIT SIGNAL: {t} — opposite regime becoming dominant")
    elif status == "INVALIDATED" and prev_status not in ("INVALIDATED","NO TRADE",""):
        _a("SETUP_INVALIDATED",
           f"RISK ALERT: {t} setup invalidated.\nReason: {opp['reason_summary']}")
    elif status == "NO TRADE" and prev_status in ("ACTIVE","HIGH CONVICTION","WEAKENING","WATCHLIST"):
        _a("SETUP_INVALIDATED",
           f"NO TRADE: {t} setup no longer passes risk checks.\n"
           f"Reason: {opp.get('no_trade_reason') or opp['reason_summary']}")

    if opp.get("risk_score", 100.0) < 35.0 and prev.get("risk_score", 100.0) >= 35.0:
        _a("RISK_ALERT",
           f"RISK SPIKE: {t} — volatility/risk conditions deteriorating rapidly")

    return alerts

def _save_alerts(alerts: list[dict]):
    if not alerts:
        return
    con = _db()
    for a in alerts:
        con.execute(
            "INSERT INTO alerts (timestamp,ticker,alert_type,message,confidence_score,status) "
            "VALUES (?,?,?,?,?,?)",
            (a["timestamp"], a["ticker"], a["alert_type"], a["message"],
             a["confidence_score"], a["status"]),
        )
    con.commit()
    con.close()

# ── Paper trading ──────────────────────────────────────────────────────────────
def _paper_pnl_pct(entry_price: float, exit_price: float, direction: str) -> float:
    if not entry_price or entry_price <= 0:
        return 0.0
    if direction == "SHORT":
        pnl = (entry_price - exit_price) / entry_price * 100.0
    else:
        pnl = (exit_price - entry_price) / entry_price * 100.0
    return round(pnl, 2)

def _hold_hours(entry_time: str | None, exit_time: str) -> float | None:
    if not entry_time:
        return None
    try:
        e = datetime.fromisoformat(entry_time.replace("Z", "+00:00"))
        x = datetime.fromisoformat(exit_time.replace("Z", "+00:00"))
        return round((x - e).total_seconds() / 3600.0, 1)
    except Exception:
        return None

def _paper_trigger(direction: str, price: float, stop_loss: float | None, target_price: float | None) -> str | None:
    if direction == "LONG":
        if stop_loss is not None and price <= stop_loss:
            return "STOP_LOSS"
        if target_price is not None and price >= target_price:
            return "TARGET_HIT"
    elif direction == "SHORT":
        if stop_loss is not None and price >= stop_loss:
            return "STOP_LOSS"
        if target_price is not None and price <= target_price:
            return "TARGET_HIT"
    return None

def _close_paper_trade(
    con,
    db_cols: set[str],
    trade_id: int,
    entry_price: float,
    direction: str,
    entry_time: str | None,
    exit_price: float,
    exit_time: str,
    exit_status: str,
    opp: dict | None = None,
):
    pnl = _paper_pnl_pct(entry_price, exit_price, direction)
    hold_h = _hold_hours(entry_time, exit_time) if "hold_duration_h" in db_cols else None
    if "exit_reason" in db_cols and "hold_duration_h" in db_cols:
        con.execute(
            "UPDATE paper_trades SET exit_price=?,exit_time=?,pnl_pct=?,status=?,"
            "exit_reason=?,hold_duration_h=? WHERE id=?",
            (exit_price, exit_time, pnl, exit_status, exit_status, hold_h, trade_id),
        )
    else:
        con.execute(
            "UPDATE paper_trades SET exit_price=?,exit_time=?,pnl_pct=?,status=? WHERE id=?",
            (exit_price, exit_time, pnl, exit_status, trade_id),
        )
    # Record exit in learning engine (non-blocking)
    try:
        learning_engine.record_exit(trade_id, exit_price, pnl, exit_status, opp)
    except Exception:
        pass

def _update_paper(opp: dict, prev: dict | None):
    con         = _db()
    now         = opp["updated_at"]
    t           = opp["ticker"]
    price       = opp.get("entry_price") or 0.0
    prev_status = prev.get("status", "") if prev else ""

    pragma  = con.execute("PRAGMA table_info(paper_trades)").fetchall()
    db_cols = {r[1] for r in pragma}

    open_with_exits = con.execute(
        "SELECT id, entry_price, direction, entry_time, stop_loss, target_price "
        "FROM paper_trades WHERE ticker=? AND status='OPEN'",
        (t,),
    ).fetchall()

    closed_on_price = False
    if price > 0:
        for tid, entry_price, direction, entry_time, stop_loss, target_price in open_with_exits:
            trigger = _paper_trigger(direction, price, stop_loss, target_price)
            if trigger:
                _close_paper_trade(con, db_cols, tid, entry_price, direction, entry_time, price, now, trigger, opp)
                closed_on_price = True

    # Open new paper trade when setup becomes ACTIVE
    if (opp["status"] in ("ACTIVE","HIGH CONVICTION")
            and prev_status not in ("ACTIVE","HIGH CONVICTION")
            and not closed_on_price):
        already_open = con.execute(
            "SELECT 1 FROM paper_trades WHERE ticker=? AND status='OPEN' LIMIT 1",
            (t,),
        ).fetchone()
        if already_open:
            con.commit()
            con.close()
            return

        base_cols = ["ticker","direction","entry_price","entry_time","confidence_score",
                     "expected_horizon","reason_summary","status"]
        extra_cols = ["stop_loss","target_price","risk_per_share","reward_per_share",
                      "shares","capital_required","leverage_used","max_loss",
                      "account_risk_pct","rr_ratio","expected_value","kelly_fraction","safe_kelly",
                      "mean_reversion_score","institutional_flow_score","momentum_score"]
        use_cols = base_cols + [c for c in extra_cols if c in db_cols]
        vals = [t, opp["direction"], price, now, opp["confidence_score"],
                opp["expected_horizon"], opp["reason_summary"], "OPEN"]
        vals += [opp.get(c) for c in extra_cols if c in db_cols]
        cur = con.execute(
            f"INSERT INTO paper_trades ({','.join(use_cols)}) VALUES ({','.join('?'*len(use_cols))})",
            vals,
        )
        # Hook learning engine entry snapshot
        try:
            learning_engine.record_entry(cur.lastrowid, opp)
        except Exception:
            pass

    # Close open paper trades when the setup is no longer tradeable
    elif opp["status"] in ("EXIT","INVALIDATED","NO TRADE"):
        open_trades = con.execute(
            "SELECT id, entry_price, direction, entry_time FROM paper_trades "
            "WHERE ticker=? AND status='OPEN'",
            (t,),
        ).fetchall()
        for tid, entry_price, direction, entry_time in open_trades:
            if not entry_price or entry_price <= 0:
                continue
            _close_paper_trade(con, db_cols, tid, entry_price, direction, entry_time, price, now, opp["status"], opp)

    con.commit()
    con.close()

# ── Main evaluate entry point ─────────────────────────────────────────────────
def evaluate(ticker: str) -> dict:
    cfg   = load_settings()
    data  = aggregator.full_analysis(ticker)
    macro = macro_agent.analyze()
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Institutional flow (uses options_score already computed in data)
    opts_score = data["options"].get("options_score", 0.0)
    try:
        inst_data = institutional_agent.analyze(ticker, opts_score)
    except Exception:
        inst_data = {"institutional_flow_score": 50.0, "smart_money_bias": "NEUTRAL", "data_confidence": "LOW"}

    c     = _components(data, macro, inst_data)
    score = _final_score(c)
    prev  = _load_prev(ticker)

    prev_score = prev["confidence_score"] if prev else score
    peak_score = max((prev["peak_score"] if prev else 0.0), score)

    direction = _direction(data, c, score)
    horizon   = _horizon(c)
    reason    = _reason(data, c, direction)
    invalid   = _invalidation(direction)

    ps = _position_sizing(data, direction, score, cfg)

    confs, conf_list = _count_confirmations(c, direction) if direction not in ("NO TRADE",) else (0, [])
    inst_warn = _institutional_warning(c, direction)

    no_trade_rsn = _no_trade_reason(data, c, direction, ticker, ps, score, cfg, confs)

    status = _status(score, direction, peak_score, data, no_trade_rsn, confs)

    reg = data["regime"]
    opp = {
        "ticker":                 ticker,
        "direction":              direction,
        "confidence_score":       score,
        "status":                 status,
        "peak_score":             round(peak_score, 1),
        "previous_score":         round(prev_score, 1),
        "expected_horizon":       horizon,
        "current_regime":         reg["regime_label"],
        "bullish_prob":           reg["bullish_prob"],
        "sideways_prob":          reg["sideways_prob"],
        "bearish_prob":           reg["bearish_prob"],
        "markov_score":           c["markov"],
        "technical_score":        c["technical"],
        "momentum_score":         c["technical"],   # alias for learning engine
        "mean_reversion_score":   c["mean_reversion"],
        "sentiment_score":        c["sentiment"],
        "volatility_score":       c["volatility"],
        "risk_score":             c["risk"],
        "market_breadth_score":   c["breadth"],
        "institutional_flow_score": c["institutional"],
        "smart_money_bias":       inst_data.get("smart_money_bias", "NEUTRAL"),
        "institutional_detail":   inst_data,
        "confirmation_count":     confs,
        "confirmation_signals":   conf_list,
        "institutional_warning":  inst_warn,
        "final_trade_score":      score,
        "reason_summary":         reason,
        "invalidation_condition": invalid,
        "created_at":             (prev["created_at"] if prev else now),
        "updated_at":             now,
        # risk / sizing
        "entry_price":            ps["entry_price"],
        "stop_loss":              ps["stop_loss"],
        "target_price":           ps["target_price"],
        "risk_per_share":         ps["risk_per_share"],
        "reward_per_share":       ps["reward_per_share"],
        "rr_ratio":               ps["rr_ratio"],
        "shares":                 ps["shares"],
        "capital_required":       ps["capital_required"],
        "leverage_used":          ps["leverage_used"],
        "max_loss":               ps["max_loss"],
        "account_risk_pct":       ps["account_risk_pct"],
        "expected_value":         ps["expected_value"],
        "kelly_fraction":         ps["kelly_fraction"],
        "safe_kelly":             ps["safe_kelly"],
        "win_prob":               ps["win_prob"],
        "no_trade_reason":        no_trade_rsn,
    }

    new_alerts = _check_alerts(opp, prev)
    _save_opp(opp)
    _save_alerts(new_alerts)
    _update_paper(opp, prev)

    opp["alerts"] = new_alerts
    return opp

# ── Read-only query helpers ────────────────────────────────────────────────────
def get_all() -> list[dict]:
    con    = _db()
    pragma = con.execute("PRAGMA table_info(active_opportunities)").fetchall()
    cols   = [r[1] for r in pragma]
    rows   = con.execute("SELECT * FROM active_opportunities").fetchall()
    con.close()
    return [dict(zip(cols, r)) for r in rows]

def get_recent_alerts(limit: int = 30) -> list[dict]:
    con  = _db()
    rows = con.execute(
        "SELECT id,timestamp,ticker,alert_type,message,confidence_score,status,seen "
        "FROM alerts ORDER BY id DESC LIMIT ?", (limit,),
    ).fetchall()
    con.close()
    cols = ["id","timestamp","ticker","alert_type","message","confidence_score","status","seen"]
    return [dict(zip(cols, r)) for r in rows]

def get_paper_stats() -> dict:
    con    = _db()
    pragma = con.execute("PRAGMA table_info(paper_trades)").fetchall()
    all_cols  = [r[1] for r in pragma]
    db_cols   = {r[1] for r in pragma}

    closed = con.execute(
        "SELECT * FROM paper_trades "
        "WHERE status IN ('EXIT','INVALIDATED','NO TRADE','STOP_LOSS','TARGET_HIT') "
        "AND pnl_pct IS NOT NULL"
    ).fetchall()
    open_t = con.execute(
        "SELECT * FROM paper_trades WHERE status='OPEN'"
    ).fetchall()
    con.close()

    closed_dicts = [dict(zip(all_cols, r)) for r in closed]
    open_dicts   = [dict(zip(all_cols, r)) for r in open_t]

    pnls     = [r["pnl_pct"] for r in closed_dicts if r.get("pnl_pct") is not None]
    total    = len(pnls)
    wins     = sum(1 for p in pnls if p > 0)
    avg_ret  = round(sum(pnls) / total, 2) if total else 0.0
    win_rate = round(wins / total * 100, 1) if total else 0.0
    max_dd   = round(min(pnls), 2) if pnls else 0.0

    exit_types: dict[str, int] = {}
    if "exit_reason" in db_cols:
        for r in closed_dicts:
            er = r.get("exit_reason") or "UNKNOWN"
            exit_types[er] = exit_types.get(er, 0) + 1

    avg_hold = None
    if "hold_duration_h" in db_cols:
        holds = [r["hold_duration_h"] for r in closed_dicts if r.get("hold_duration_h") is not None]
        avg_hold = round(sum(holds) / len(holds), 1) if holds else None

    open_fields = ["ticker","direction","entry_price","entry_time","confidence_score",
                   "expected_horizon","stop_loss","target_price","shares","capital_required",
                   "rr_ratio","expected_value","max_loss","account_risk_pct"]
    open_out = [{f: r.get(f) for f in open_fields} for r in open_dicts]

    return {
        "total_trades": total,
        "win_rate":     win_rate,
        "avg_return":   avg_ret,
        "max_drawdown": max_dd,
        "exit_types":   exit_types,
        "avg_hold_h":   avg_hold,
        "open_trades":  open_out,
    }
