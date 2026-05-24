"""
Institutional Flow Agent — free smart-money signals via yfinance.

Sources (priority: free / no API key):
  A. Insider transactions      → 0.30 weight
  B. Options flow score        → 0.25 weight  (passed in from options_agent)
  C. Hedge fund / inst holders → 0.20 weight
  D. Short interest            → 0.15 weight
  E. Analyst upgrades/downgrades → 0.10 weight

Score: 0 (strongly bearish) … 50 (neutral) … 100 (strongly bullish)

No LLM calls. Pure math. Graceful degradation if any source is unavailable.
"""

import math
import time
import numpy as np
import yfinance as yf

_cache: dict = {}
_CACHE_TTL = 1800  # 30 min — these sources change slowly


def _cget(key):
    if key in _cache:
        d, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return d
    return None


def _cset(key, val):
    _cache[key] = (val, time.time())
    return val


def _clamp(x, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(x)))


# ── A. Insider activity ───────────────────────────────────────────────────────

def _insider_score(ticker: str) -> tuple[float, str]:
    """Parse insider transactions → score 0-100 and detail string."""
    try:
        tk = yf.Ticker(ticker)
        trans = tk.insider_transactions
        if trans is None or (hasattr(trans, "empty") and trans.empty):
            return 50.0, "UNAVAILABLE"

        import pandas as pd
        df = trans.copy()
        df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]

        # Locate date column
        date_col = next(
            (c for c in df.columns if "date" in c or "start" in c), None
        )
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
            df = df.dropna(subset=[date_col])
            cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)
            df = df[df[date_col] >= cutoff]

        if df.empty:
            return 50.0, "NO_RECENT_ACTIVITY"

        shares_col = next((c for c in df.columns if "shares" in c), None)
        txn_col = next(
            (c for c in df.columns if "transaction" in c or "text" in c), None
        )
        if shares_col is None:
            return 50.0, "UNAVAILABLE"

        df[shares_col] = pd.to_numeric(df[shares_col], errors="coerce").fillna(0)

        net = 0.0
        for _, row in df.iterrows():
            shares = abs(float(row[shares_col]))
            txn_txt = str(row.get(txn_col, "") if txn_col else "").lower()
            is_buy = any(w in txn_txt for w in ("buy", "purchase", "acqui"))
            is_sell = any(w in txn_txt for w in ("sell", "sale", "dispos"))
            if is_buy:
                net += shares
            elif is_sell:
                net -= shares

        if net > 0:
            score = _clamp(55 + min(net / 10_000, 1.0) * 28)
            detail = f"Net buy {int(net):,} shares (90d)"
        elif net < 0:
            score = _clamp(45 - min(abs(net) / 10_000, 1.0) * 25)
            detail = f"Net sell {int(abs(net)):,} shares (90d)"
        else:
            score = 50.0
            detail = "No net insider activity (90d)"

        return round(score, 1), detail

    except Exception:
        return 50.0, "UNAVAILABLE"


# ── C. Hedge fund / institutional positioning ─────────────────────────────────

def _institutional_score(ticker: str) -> tuple[float, str]:
    """
    Institutional ownership % + number of holders as smart-money confidence proxy.
    Note: 13F data is quarterly / lagging — treated as slow-moving signal only.
    """
    try:
        import pandas as pd
        tk = yf.Ticker(ticker)

        inst_pct = None
        try:
            mh = tk.major_holders
            if mh is not None and not (hasattr(mh, "empty") and mh.empty):
                vals = []
                for idx in range(len(mh)):
                    try:
                        raw = str(mh.iloc[idx, 0]).strip().replace("%", "")
                        v = float(raw)
                        vals.append(v)
                    except Exception:
                        pass
                # major_holders rows: [insider%, institution%, shares_float, #institutions]
                if len(vals) >= 2:
                    inst_pct = vals[1]
                    if inst_pct < 1.0:  # might be a decimal
                        inst_pct *= 100.0
        except Exception:
            pass

        num_holders = 0
        try:
            ih = tk.institutional_holders
            if ih is not None and not (hasattr(ih, "empty") and ih.empty):
                num_holders = len(ih)
        except Exception:
            pass

        if inst_pct is None and num_holders == 0:
            return 50.0, "UNAVAILABLE"

        # Score by ownership level
        if inst_pct is not None:
            if inst_pct > 80:
                base = 63
            elif inst_pct > 60:
                base = 58
            elif inst_pct > 40:
                base = 53
            elif inst_pct > 20:
                base = 49
            else:
                base = 45
        else:
            base = 50

        # Adjust for breadth of holders
        if num_holders > 80:
            base += 4
        elif num_holders > 40:
            base += 2
        elif num_holders < 5:
            base -= 3

        score = _clamp(base)
        detail_parts = []
        if num_holders:
            detail_parts.append(f"{num_holders} institutions")
        if inst_pct is not None:
            detail_parts.append(f"{inst_pct:.0f}% held")
        detail = ", ".join(detail_parts) if detail_parts else "UNAVAILABLE"

        return round(score, 1), detail

    except Exception:
        return 50.0, "UNAVAILABLE"


# ── D. Short interest ─────────────────────────────────────────────────────────

def _short_score(ticker: str) -> tuple[float, str]:
    """
    Short interest as % of float → score 0-100.
    High short = bearish lean; rapid decrease (shorts covering) = bullish lean.
    High short + strong momentum = potential squeeze (ambiguous — handled in edge model).
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}

        short_pct = info.get("shortPercentOfFloat")
        if short_pct is None:
            short_pct = info.get("sharesPercentSharesOut")
        if short_pct is None:
            return 50.0, "UNAVAILABLE"

        if short_pct < 1.0:  # decimal form
            short_pct = short_pct * 100.0

        # Base score
        if short_pct < 3:
            base = 63
        elif short_pct < 6:
            base = 57
        elif short_pct < 10:
            base = 50
        elif short_pct < 15:
            base = 43
        elif short_pct < 20:
            base = 37
        else:
            base = 31

        # Trend adjustment (shorts covering = bullish signal)
        prior = info.get("sharesShortPriorMonth")
        current = info.get("sharesShort")
        trend_adj = 0
        if prior and current and prior > 0:
            chg = (current - prior) / prior
            if chg < -0.10:
                trend_adj = +9    # aggressively covering
            elif chg < -0.05:
                trend_adj = +4
            elif chg > 0.10:
                trend_adj = -9    # building short position
            elif chg > 0.05:
                trend_adj = -4

        score = _clamp(base + trend_adj)
        bias = "NEUTRAL" if abs(score - 50) < 8 else ("BULLISH" if score > 50 else "BEARISH")
        return round(score, 1), f"{short_pct:.1f}% short float — {bias}"

    except Exception:
        return 50.0, "UNAVAILABLE"


# ── E. Analyst upgrades / downgrades ─────────────────────────────────────────

def _analyst_score(ticker: str) -> tuple[float, str]:
    """Recent analyst actions (60d, time-decayed) → score 0-100."""
    try:
        import pandas as pd
        tk = yf.Ticker(ticker)
        upg = tk.upgrades_downgrades
        if upg is None or (hasattr(upg, "empty") and upg.empty):
            return 50.0, "UNAVAILABLE"

        df = upg.copy()
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index, utc=True, errors="coerce")
        else:
            if df.index.tz is None:
                df.index = df.index.tz_localize("UTC")

        now = pd.Timestamp.now(tz="UTC")
        cutoff = now - pd.Timedelta(days=60)
        df = df[df.index >= cutoff]

        if df.empty:
            return 50.0, "NO_RECENT_ANALYST_ACTIVITY"

        df.columns = [str(c).lower().strip() for c in df.columns]
        action_col = next(
            (c for c in df.columns if "action" in c or "tograde" in c or "grade" in c),
            None,
        )

        ups = 0.0
        downs = 0.0
        for idx, row in df.iterrows():
            age_days = max((now - idx).days, 0)
            decay = math.exp(-age_days / 20.0)  # ~20-day half-life

            if action_col:
                action = str(row.get(action_col, "")).lower()
            else:
                action = str(row.tolist()).lower()

            if any(w in action for w in ("upgrade", "init", "buy", "overweight", "outperform", "strong buy")):
                ups += decay
            elif any(w in action for w in ("downgrade", "sell", "underweight", "underperform")):
                downs += decay

        net = ups - downs
        total = ups + downs + 1e-10

        if net > 0.5:
            score = _clamp(55 + min(net / total, 1.0) * 25)
        elif net < -0.5:
            score = _clamp(45 - min(abs(net) / total, 1.0) * 20)
        else:
            score = 50.0

        n_up = round(ups)
        n_dn = round(downs)
        detail = f"{n_up} ups / {n_dn} downs (60d, time-decayed)"
        return round(score, 1), detail

    except Exception:
        return 50.0, "UNAVAILABLE"


# ── Main analyze ──────────────────────────────────────────────────────────────

def analyze(ticker: str, options_score: float = 0.0) -> dict:
    """
    Compute institutional_flow_score (0-100) for ticker.

    options_score: pass in the existing options_agent score [-1, +1].
                   Defaults to neutral (0.0) if not provided.
    """
    # Sub-components that don't depend on options_score are cached
    cached = _cget(f"{ticker}|inst_base")
    if cached is not None:
        insider_s = cached["insider_activity_score"]
        inst_s = cached["hedge_fund_score"]
        short_s = cached["short_interest_score"]
        analyst_s = cached["analyst_score"]
        insider_detail = cached["insider_detail"]
        inst_detail = cached["hedge_fund_detail"]
        short_detail = cached["short_detail"]
        analyst_detail = cached["analyst_detail"]
    else:
        insider_s, insider_detail = _insider_score(ticker)
        inst_s, inst_detail = _institutional_score(ticker)
        short_s, short_detail = _short_score(ticker)
        analyst_s, analyst_detail = _analyst_score(ticker)

        base = {
            "insider_activity_score": insider_s,
            "hedge_fund_score": inst_s,
            "short_interest_score": short_s,
            "analyst_score": analyst_s,
            "insider_detail": insider_detail,
            "hedge_fund_detail": inst_detail,
            "short_detail": short_detail,
            "analyst_detail": analyst_detail,
        }
        _cset(f"{ticker}|inst_base", base)

    # B. Options flow: convert [-1, +1] → [0, 100]
    opts_s = _clamp((options_score + 1.0) / 2.0 * 100.0)

    composite = round(
        0.30 * insider_s
        + 0.25 * opts_s
        + 0.20 * inst_s
        + 0.15 * short_s
        + 0.10 * analyst_s,
        1,
    )
    composite = _clamp(composite)

    if composite >= 65:
        bias = "BULLISH"
    elif composite <= 35:
        bias = "BEARISH"
    elif composite >= 57:
        bias = "MILDLY_BULLISH"
    elif composite <= 43:
        bias = "MILDLY_BEARISH"
    else:
        bias = "NEUTRAL"

    unavailable_count = sum(
        1 for d in [insider_detail, inst_detail, short_detail, analyst_detail]
        if "UNAVAILABLE" in str(d)
    )
    data_confidence = "LOW" if unavailable_count >= 3 else (
        "MEDIUM" if unavailable_count >= 2 else "HIGH"
    )

    return {
        "institutional_flow_score": composite,
        "smart_money_bias": bias,
        "data_confidence": data_confidence,
        # Component scores
        "insider_activity_score": insider_s,
        "insider_detail": insider_detail,
        "options_flow_score": round(opts_s, 1),
        "hedge_fund_score": inst_s,
        "hedge_fund_detail": inst_detail,
        "short_interest_score": short_s,
        "short_detail": short_detail,
        "analyst_score": analyst_s,
        "analyst_detail": analyst_detail,
        # Explanation (plain English summary, no LLM)
        "explanation": _explain(composite, bias, insider_detail, short_detail, analyst_detail),
    }


def _explain(composite: float, bias: str, insider: str, short: str, analyst: str) -> str:
    parts = []
    if bias in ("BULLISH", "MILDLY_BULLISH"):
        parts.append(f"Smart money leans {bias.replace('_', ' ').lower()} ({composite:.0f}/100).")
    elif bias in ("BEARISH", "MILDLY_BEARISH"):
        parts.append(f"Smart money leans {bias.replace('_', ' ').lower()} ({composite:.0f}/100).")
    else:
        parts.append(f"Smart money is neutral ({composite:.0f}/100).")

    if "UNAVAILABLE" not in str(insider) and "NO_RECENT" not in str(insider):
        parts.append(f"Insiders: {insider}.")
    if "UNAVAILABLE" not in str(short):
        parts.append(f"Short interest: {short}.")
    if "UNAVAILABLE" not in str(analyst) and "NO_RECENT" not in str(analyst):
        parts.append(f"Analysts (60d): {analyst}.")

    return " ".join(parts) if parts else "Insufficient data for institutional analysis."
