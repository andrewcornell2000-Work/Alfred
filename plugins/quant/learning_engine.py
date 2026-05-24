"""
Learning Feedback Loop — records paper trade entry/exit snapshots,
scores signal reliability, calibrates confidence, and recommends weight changes.

Design rules:
  - No LLM calls. Pure math only.
  - Never automatically change production weights — RECOMMEND only.
  - Two modes: OBSERVE (log only) | RECOMMEND (suggest changes, user approves).
"""

import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.environ.get(
    "TRADE_ENGINE_DB_PATH",
    os.path.join(os.path.dirname(__file__), "trade_history.db"),
)

SIGNALS = [
    "markov_score",
    "momentum_score",
    "mean_reversion_score",
    "news_sentiment_score",
    "volatility_score",
    "risk_score",
    "market_breadth_score",
    "institutional_flow_score",
]

# Current production weights (must match trade_engine._W mapping)
_CURRENT_WEIGHTS: dict[str, float] = {
    "markov_score":             0.18,
    "momentum_score":           0.18,
    "mean_reversion_score":     0.14,
    "news_sentiment_score":     0.14,
    "institutional_flow_score": 0.10,
    "volatility_score":         0.10,
    "market_breadth_score":     0.08,
    "risk_score":               0.08,
}


def _db() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


def _init_tables() -> None:
    con = _db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS trade_snapshots (
        id                         INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_trade_id             INTEGER UNIQUE,
        ticker                     TEXT,
        direction                  TEXT,
        -- Entry fields
        entry_price                REAL,
        stop_loss                  REAL,
        target_price               REAL,
        expected_horizon           TEXT,
        confidence_score           REAL,
        bullish_probability        REAL,
        bearish_probability        REAL,
        sideways_probability       REAL,
        regime                     TEXT,
        markov_score               REAL,
        momentum_score             REAL,
        mean_reversion_score       REAL,
        news_sentiment_score       REAL,
        volatility_score           REAL,
        risk_score                 REAL,
        market_breadth_score       REAL,
        institutional_flow_score   REAL,
        final_trade_score          REAL,
        risk_reward_ratio          REAL,
        position_size              INTEGER,
        capital_required           REAL,
        max_loss                   REAL,
        reason_summary             TEXT,
        entry_timestamp            TEXT,
        -- Exit fields
        exit_price                 REAL,
        exit_time                  TEXT,
        pnl                        REAL,
        pnl_percent                REAL,
        win_loss                   TEXT,
        exit_reason                TEXT,
        max_favorable_excursion    REAL,
        max_adverse_excursion      REAL,
        highest_confidence_during  REAL,
        lowest_confidence_during   REAL,
        regime_at_exit             TEXT,
        institutional_flow_change  REAL,
        -- Post-trade analysis
        analysis_done              INTEGER DEFAULT 0,
        markov_correct             INTEGER,
        momentum_correct           INTEGER,
        mean_reversion_correct     INTEGER,
        news_sentiment_correct     INTEGER,
        volatility_correct         INTEGER,
        risk_correct               INTEGER,
        market_breadth_correct     INTEGER,
        institutional_correct      INTEGER,
        mistake_category           TEXT,
        thesis_played_out          INTEGER,
        signal_agreement_count     INTEGER
    );

    CREATE TABLE IF NOT EXISTS weight_recommendations (
        id                   INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp            TEXT,
        signal_name          TEXT,
        current_weight       REAL,
        recommended_weight   REAL,
        reliability_20       REAL,
        reliability_50       REAL,
        reliability_100      REAL,
        reason               TEXT,
        status               TEXT DEFAULT 'PENDING'
    );
    """)
    con.commit()
    con.close()


_init_tables()


# ── Entry recording ────────────────────────────────────────────────────────────

def record_entry(paper_trade_id: int, opp: dict) -> None:
    """Store entry snapshot when a paper trade opens."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    con = _db()
    try:
        con.execute(
            """
            INSERT OR IGNORE INTO trade_snapshots (
                paper_trade_id, ticker, direction,
                entry_price, stop_loss, target_price, expected_horizon,
                confidence_score, bullish_probability, bearish_probability,
                sideways_probability, regime,
                markov_score, momentum_score, mean_reversion_score,
                news_sentiment_score, volatility_score, risk_score,
                market_breadth_score, institutional_flow_score,
                final_trade_score, risk_reward_ratio, position_size,
                capital_required, max_loss, reason_summary, entry_timestamp
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                paper_trade_id,
                opp.get("ticker"),
                opp.get("direction"),
                opp.get("entry_price"),
                opp.get("stop_loss"),
                opp.get("target_price"),
                opp.get("expected_horizon"),
                opp.get("confidence_score"),
                opp.get("bullish_prob"),
                opp.get("bearish_prob"),
                opp.get("sideways_prob"),
                opp.get("current_regime"),
                opp.get("markov_score"),
                opp.get("momentum_score"),
                opp.get("mean_reversion_score"),
                opp.get("sentiment_score"),       # maps → news_sentiment_score
                opp.get("volatility_score"),
                opp.get("risk_score"),
                opp.get("market_breadth_score"),
                opp.get("institutional_flow_score"),
                opp.get("final_trade_score"),
                opp.get("rr_ratio"),
                opp.get("shares"),
                opp.get("capital_required"),
                opp.get("max_loss"),
                opp.get("reason_summary"),
                now,
            ),
        )
        con.commit()
    except Exception:
        pass
    finally:
        con.close()


# ── Exit recording ─────────────────────────────────────────────────────────────

def record_exit(
    paper_trade_id: int,
    exit_price: float,
    pnl_pct: float,
    exit_reason: str,
    opp_at_exit: dict | None = None,
) -> None:
    """Store exit snapshot then trigger post-trade analysis."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    win_loss = "WIN" if pnl_pct > 0 else ("LOSS" if pnl_pct < 0 else "FLAT")

    con = _db()
    try:
        # Compute dollar PnL from entry snapshot
        row = con.execute(
            "SELECT entry_price, position_size, direction "
            "FROM trade_snapshots WHERE paper_trade_id=?",
            (paper_trade_id,),
        ).fetchone()

        pnl_dollar = None
        if row:
            ep, shares, direction = row
            if ep and shares and ep > 0:
                if direction == "LONG":
                    pnl_dollar = (exit_price - ep) * shares
                else:
                    pnl_dollar = (ep - exit_price) * shares

        # Institutional flow change during trade
        inst_now = (opp_at_exit or {}).get("institutional_flow_score")
        inst_change = None
        if inst_now is not None:
            entry_inst = con.execute(
                "SELECT institutional_flow_score FROM trade_snapshots WHERE paper_trade_id=?",
                (paper_trade_id,),
            ).fetchone()
            if entry_inst and entry_inst[0] is not None:
                inst_change = round(inst_now - entry_inst[0], 1)

        regime_at_exit = (opp_at_exit or {}).get("current_regime")

        con.execute(
            """
            UPDATE trade_snapshots SET
                exit_price=?, exit_time=?, pnl=?, pnl_percent=?,
                win_loss=?, exit_reason=?, regime_at_exit=?,
                institutional_flow_change=?
            WHERE paper_trade_id=?
            """,
            (
                exit_price, now, pnl_dollar, pnl_pct,
                win_loss, exit_reason, regime_at_exit,
                inst_change, paper_trade_id,
            ),
        )
        con.commit()
    finally:
        con.close()

    _analyze_trade(paper_trade_id)
    _refresh_recommendations()


# ── Post-trade signal analysis ────────────────────────────────────────────────

def _analyze_trade(paper_trade_id: int) -> None:
    """Score each signal +1/0/-1 after trade closes and classify mistakes."""
    con = _db()
    row = con.execute(
        """
        SELECT direction, win_loss, pnl_percent,
               markov_score, momentum_score, mean_reversion_score,
               news_sentiment_score, volatility_score, risk_score,
               market_breadth_score, institutional_flow_score,
               confidence_score, risk_reward_ratio,
               regime, regime_at_exit, exit_reason
        FROM trade_snapshots WHERE paper_trade_id=?
        """,
        (paper_trade_id,),
    ).fetchone()
    if not row:
        con.close()
        return

    (direction, win_loss, pnl_pct,
     markov, momentum, mean_rev, sentiment, volatility, risk, breadth, institutional,
     confidence, rr, regime_entry, regime_exit, exit_reason) = row

    is_long = direction == "LONG"

    def _correct(score_0_100):
        """Does this 0-100 score support the trade direction?"""
        if score_0_100 is None:
            return None
        if is_long:
            if score_0_100 > 60:
                return 1    # aligned bullish for long
            if score_0_100 < 40:
                return -1   # misleading
        else:
            if score_0_100 < 40:
                return 1    # aligned bearish for short
            if score_0_100 > 60:
                return -1   # misleading
        return 0            # neutral

    # Thesis check: regime stable across trade
    thesis_played_out = None
    if regime_entry and regime_exit:
        thesis_played_out = int(regime_entry == regime_exit)

    # Count how many signals agreed with direction
    correctness_vals = [
        _correct(markov), _correct(momentum), _correct(mean_rev),
        _correct(sentiment), _correct(institutional),
    ]
    agreement = sum(1 for v in correctness_vals if v == 1)

    # Mistake classification (for losing trades)
    mistake = None
    if win_loss == "LOSS":
        mistake = _classify_mistake(
            pnl_pct, rr, confidence, volatility, sentiment,
            institutional, exit_reason, regime_entry, regime_exit, markov, momentum,
        )

    con.execute(
        """
        UPDATE trade_snapshots SET
            analysis_done=1,
            markov_correct=?, momentum_correct=?, mean_reversion_correct=?,
            news_sentiment_correct=?, volatility_correct=?, risk_correct=?,
            market_breadth_correct=?, institutional_correct=?,
            mistake_category=?, thesis_played_out=?, signal_agreement_count=?
        WHERE paper_trade_id=?
        """,
        (
            _correct(markov), _correct(momentum), _correct(mean_rev),
            _correct(sentiment), _correct(volatility), _correct(risk),
            _correct(breadth), _correct(institutional),
            mistake, thesis_played_out, agreement, paper_trade_id,
        ),
    )
    con.commit()
    con.close()


def _classify_mistake(
    pnl_pct, rr, confidence, volatility, sentiment,
    institutional, exit_reason, regime_entry, regime_exit, markov, momentum,
) -> str:
    """Rule-based mistake classification for losing trades."""
    if regime_entry and regime_exit and regime_entry != regime_exit:
        return "REGIME_SHIFT"
    if exit_reason == "STOP_HIT" and rr is not None and rr < 1.2:
        return "STOP_TOO_TIGHT"
    if exit_reason == "TARGET_HIT":
        return "TARGET_TOO_AGGRESSIVE"
    if sentiment is not None and sentiment < 35:
        return "NEWS_REVERSAL"
    if volatility is not None and volatility < 25:
        return "VOLATILITY_SPIKE"
    if confidence is not None and confidence > 85:
        return "OVERCONFIDENCE"
    if institutional is not None and institutional < 35:
        return "INSTITUTIONAL_FLOW_MISLEADING"
    if rr is not None and rr < 1.5:
        return "POOR_RISK_REWARD"
    if (markov is not None and momentum is not None
            and abs(markov - 50) < 10 and abs(momentum - 50) < 10):
        return "SIDEWAYS_CHOP"
    return "BAD_ENTRY"


# ── Signal reliability ─────────────────────────────────────────────────────────

def get_signal_reliability() -> dict:
    """
    Rolling signal reliability over last 20 / 50 / 100 analysed trades.

    +1 = signal correctly supported trade direction
     0 = neutral
    -1 = misleading

    Reliability = % of non-neutral signals that were +1.
    """
    con = _db()
    rows = con.execute(
        """
        SELECT markov_correct, momentum_correct, mean_reversion_correct,
               news_sentiment_correct, volatility_correct, risk_correct,
               market_breadth_correct, institutional_correct
        FROM trade_snapshots
        WHERE analysis_done=1 AND win_loss IS NOT NULL
        ORDER BY id DESC
        """,
    ).fetchall()
    con.close()

    col_map = {
        0: "markov_score",
        1: "momentum_score",
        2: "mean_reversion_score",
        3: "news_sentiment_score",
        4: "volatility_score",
        5: "risk_score",
        6: "market_breadth_score",
        7: "institutional_flow_score",
    }

    def _rel(vals: list) -> float | None:
        decisive = [v for v in vals if v in (1, -1)]
        if not decisive:
            return None
        positives = sum(1 for v in decisive if v == 1)
        return round(positives / len(decisive) * 100, 1)

    result = {}
    for i, sig in col_map.items():
        all_vals = [r[i] for r in rows if r[i] is not None]
        result[sig] = {
            "r20":  _rel(all_vals[:20]),
            "r50":  _rel(all_vals[:50]),
            "r100": _rel(all_vals[:100]),
            "total": len(all_vals),
            "current_weight": _CURRENT_WEIGHTS.get(sig),
        }
    return result


# ── Probability calibration ────────────────────────────────────────────────────

def get_calibration_stats() -> dict:
    """
    Brier score + bucket accuracy for confidence predictions.

    Brier score = mean((predicted_prob - outcome)^2)
    Lower is better; 0 = perfect.

    Calibration error = mean |avg predicted % - actual win rate %| per bucket.
    """
    con = _db()
    rows = con.execute(
        "SELECT confidence_score, win_loss "
        "FROM trade_snapshots "
        "WHERE analysis_done=1 AND win_loss IS NOT NULL AND confidence_score IS NOT NULL",
    ).fetchall()
    con.close()

    if not rows:
        return {"brier_score": None, "calibration_error": None, "buckets": [], "total": 0}

    bucket_defs = [
        ("50-60", 50, 60),
        ("60-70", 60, 70),
        ("70-80", 70, 80),
        ("80-90", 80, 90),
        ("90-100", 90, 101),
    ]
    buckets: dict[str, dict] = {
        lbl: {"preds": [], "wins": 0, "total": 0}
        for lbl, _, _ in bucket_defs
    }

    brier = 0.0
    for conf, wl in rows:
        p = conf / 100.0
        outcome = 1.0 if wl == "WIN" else 0.0
        brier += (p - outcome) ** 2
        for lbl, lo, hi in bucket_defs:
            if lo <= conf < hi:
                buckets[lbl]["preds"].append(p)
                buckets[lbl]["wins"] += int(wl == "WIN")
                buckets[lbl]["total"] += 1

    n = len(rows)
    brier_score = round(brier / n, 4)

    cal_errors = []
    bucket_out = []
    for lbl, _, _ in bucket_defs:
        b = buckets[lbl]
        if b["total"] == 0:
            continue
        avg_pred = sum(b["preds"]) / len(b["preds"]) * 100
        actual_wr = b["wins"] / b["total"] * 100
        err = abs(avg_pred - actual_wr)
        cal_errors.append(err)
        bucket_out.append(
            {
                "bucket": lbl,
                "count": b["total"],
                "avg_predicted_confidence": round(avg_pred, 1),
                "actual_win_rate": round(actual_wr, 1),
                "calibration_error": round(err, 1),
                "quality": "GOOD" if err < 10 else ("FAIR" if err < 20 else "POOR"),
            }
        )

    cal_error = round(sum(cal_errors) / len(cal_errors), 2) if cal_errors else None
    quality = "GOOD" if (cal_error or 100) < 10 else ("FAIR" if (cal_error or 100) < 20 else "POOR")

    return {
        "brier_score": brier_score,
        "calibration_error": cal_error,
        "calibration_quality": quality,
        "buckets": bucket_out,
        "total": n,
    }


# ── Weight recommendations ─────────────────────────────────────────────────────

def _refresh_recommendations() -> None:
    """Generate weight change recommendations based on rolling signal reliability."""
    reliability = get_signal_reliability()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    con = _db()
    try:
        for sig, stats in reliability.items():
            if stats["total"] < 20:
                continue
            r50 = stats["r50"]
            if r50 is None:
                continue

            current = _CURRENT_WEIGHTS.get(sig, 0.10)
            recommended = current
            reason = ""

            if r50 > 65:
                recommended = round(min(current * 1.15, current + 0.04), 3)
                reason = (
                    f"Reliability {r50:.0f}% over last 50 trades exceeds 65% threshold — "
                    "consider slightly increasing this signal's weight."
                )
            elif r50 < 45:
                recommended = round(max(current * 0.85, current - 0.04), 3)
                reason = (
                    f"Reliability {r50:.0f}% over last 50 trades below 45% threshold — "
                    "consider reducing this signal's weight."
                )
            else:
                continue

            if abs(recommended - current) < 0.005:
                continue

            # Don't duplicate active recommendations
            existing = con.execute(
                "SELECT id FROM weight_recommendations "
                "WHERE signal_name=? AND status='PENDING' ORDER BY id DESC LIMIT 1",
                (sig,),
            ).fetchone()
            if existing:
                continue

            con.execute(
                """
                INSERT INTO weight_recommendations
                    (timestamp, signal_name, current_weight, recommended_weight,
                     reliability_20, reliability_50, reliability_100, reason, status)
                VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    now, sig, current, recommended,
                    stats["r20"], r50, stats["r100"],
                    reason, "PENDING",
                ),
            )
        con.commit()
    finally:
        con.close()


def get_weight_recommendations() -> list[dict]:
    con = _db()
    rows = con.execute(
        """
        SELECT id, timestamp, signal_name, current_weight, recommended_weight,
               reliability_20, reliability_50, reliability_100, reason, status
        FROM weight_recommendations ORDER BY id DESC LIMIT 30
        """,
    ).fetchall()
    con.close()
    cols = [
        "id", "timestamp", "signal_name", "current_weight", "recommended_weight",
        "reliability_20", "reliability_50", "reliability_100", "reason", "status",
    ]
    return [dict(zip(cols, r)) for r in rows]


def approve_recommendation(rec_id: int) -> dict:
    """Mark a recommendation as approved (user action — weights NOT auto-changed)."""
    con = _db()
    con.execute(
        "UPDATE weight_recommendations SET status='APPROVED' WHERE id=?", (rec_id,)
    )
    con.commit()
    con.close()
    return {"status": "approved", "id": rec_id, "note": "Weight change must be applied manually in config.py"}


def dismiss_recommendation(rec_id: int) -> dict:
    """Dismiss a pending recommendation."""
    con = _db()
    con.execute(
        "UPDATE weight_recommendations SET status='DISMISSED' WHERE id=?", (rec_id,)
    )
    con.commit()
    con.close()
    return {"status": "dismissed", "id": rec_id}


# ── Mistake distribution ───────────────────────────────────────────────────────

def get_mistake_distribution() -> dict:
    con = _db()
    rows = con.execute(
        "SELECT mistake_category, COUNT(*) FROM trade_snapshots "
        "WHERE win_loss='LOSS' AND mistake_category IS NOT NULL "
        "GROUP BY mistake_category ORDER BY COUNT(*) DESC",
    ).fetchall()
    con.close()
    return {r[0]: r[1] for r in rows}


# ── Full performance review ────────────────────────────────────────────────────

def get_performance_review() -> dict:
    """Combined view for the Learning dashboard panel."""
    con = _db()
    closed = con.execute(
        """
        SELECT ticker, direction, pnl_percent, win_loss,
               entry_timestamp, exit_time, confidence_score,
               exit_reason, mistake_category, thesis_played_out,
               markov_score, momentum_score, institutional_flow_score,
               regime, signal_agreement_count
        FROM trade_snapshots
        WHERE win_loss IS NOT NULL
        ORDER BY id DESC LIMIT 50
        """,
    ).fetchall()
    con.close()

    cols = [
        "ticker", "direction", "pnl_percent", "win_loss",
        "entry_timestamp", "exit_time", "confidence_score",
        "exit_reason", "mistake_category", "thesis_played_out",
        "markov_score", "momentum_score", "institutional_flow_score",
        "regime", "signal_agreement_count",
    ]
    trades = [dict(zip(cols, r)) for r in closed]

    pnls = [t["pnl_percent"] for t in trades if t["pnl_percent"] is not None]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    n = len(pnls)

    win_rate = round(len(wins) / n * 100, 1) if n > 0 else 0.0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0.0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0.0

    wr = len(wins) / n if n > 0 else 0.0
    expectancy = round(wr * avg_win + (1 - wr) * avg_loss, 2) if n > 0 else 0.0

    max_dd = round(min(pnls), 2) if pnls else 0.0

    reliability = get_signal_reliability()
    calibration = get_calibration_stats()
    recommendations = [r for r in get_weight_recommendations() if r["status"] == "PENDING"]
    mistakes = get_mistake_distribution()

    sig_r50 = {
        s: (v["r50"] or 0.0)
        for s, v in reliability.items()
        if v["r50"] is not None
    }
    best_signal = max(sig_r50, key=sig_r50.get) if sig_r50 else None
    worst_signal = min(sig_r50, key=sig_r50.get) if sig_r50 else None

    return {
        "total_trades": n,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "max_drawdown": max_dd,
        "best_signal": best_signal,
        "best_signal_r50": sig_r50.get(best_signal),
        "worst_signal": worst_signal,
        "worst_signal_r50": sig_r50.get(worst_signal),
        "signal_reliability": reliability,
        "calibration": calibration,
        "recommendations": recommendations,
        "mistake_distribution": mistakes,
        "recent_trades": trades[:20],
        "mode": "RECOMMEND",
    }
