"""
Sentiment agent: scores recent news headlines for each ticker using
VADER augmented with a financial-domain lexicon.
Source: yfinance .news (10-20 articles, no API key needed).
"""

import time
import numpy as np
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Financial lexicon extension for VADER ────────────────────────────────────
_FIN_LEXICON = {
    # Bullish
    "beats": 2.5, "beat": 2.0, "surges": 2.5, "surge": 2.0,
    "soars": 2.5, "soar": 2.0, "rallies": 2.0, "rally": 1.5,
    "jumps": 2.0, "upgraded": 2.5, "upgrade": 2.0,
    "bullish": 2.5, "upside": 1.5, "outperforms": 2.0,
    "robust": 1.5, "booming": 2.0, "record-high": 2.5,
    "profit": 1.0, "profits": 1.2, "growth": 1.0,
    "partnership": 1.0, "deal": 0.8, "contract": 0.8,
    # Bearish
    "plunges": -2.5, "plunge": -2.0, "crashes": -2.5, "crash": -2.0,
    "tumbles": -2.0, "tumble": -1.5, "misses": -2.0, "miss": -1.5,
    "disappoints": -2.0, "disappointing": -1.8, "layoffs": -2.0,
    "layoff": -1.5, "recession": -2.5, "bearish": -2.5,
    "downgraded": -2.5, "downgrade": -2.0, "downside": -1.5,
    "selloff": -2.0, "sell-off": -2.0, "slump": -1.5,
    "plummets": -2.5, "warns": -1.5, "warning": -1.5,
    "concern": -1.0, "concerns": -1.0, "uncertainty": -1.2,
    "volatile": -1.0, "lawsuit": -1.5, "fine": -1.2,
    "debt": -0.8, "loss": -1.5, "losses": -1.5,
}

_analyzer = SentimentIntensityAnalyzer()
_analyzer.lexicon.update(_FIN_LEXICON)

_news_cache: dict = {}
_CACHE_TTL = 600  # 10 minutes (news doesn't change that fast)


def _get_title(article: dict) -> str:
    """Handle both old and new yfinance news formats."""
    content = article.get("content", {})
    if isinstance(content, dict):
        return content.get("title", "") or content.get("summary", "")
    return article.get("title", "") or article.get("summary", "")


def _get_timestamp(article: dict) -> float:
    """Extract publish timestamp (epoch seconds)."""
    content = article.get("content", {})
    if isinstance(content, dict):
        pub = content.get("pubDate", "")
        if pub:
            try:
                import datetime
                dt = datetime.datetime.fromisoformat(pub.replace("Z", "+00:00"))
                return dt.timestamp()
            except Exception:
                pass
    return float(article.get("providerPublishTime", time.time()))


def _fetch_news(ticker: str) -> list[dict]:
    now = time.time()
    if ticker in _news_cache:
        articles, ts = _news_cache[ticker]
        if now - ts < _CACHE_TTL:
            return articles

    try:
        tk = yf.Ticker(ticker)
        articles = tk.news or []
    except Exception:
        articles = []

    _news_cache[ticker] = (articles, now)
    return articles


def analyze(ticker: str) -> dict:
    articles = _fetch_news(ticker)

    if not articles:
        return {
            "score": 0.0,
            "signal": "NEUTRAL",
            "article_count": 0,
            "top_headlines": [],
            "avg_compound": 0.0,
        }

    now = time.time()
    scored = []

    for art in articles:
        title = _get_title(art)
        if not title:
            continue
        ts    = _get_timestamp(art)
        age_h = (now - ts) / 3600           # hours old
        decay = np.exp(-age_h / 24)         # half-life ≈ 24 hrs

        compound = _analyzer.polarity_scores(title)["compound"]
        scored.append({
            "title":    title[:120],
            "compound": compound,
            "decay":    decay,
            "age_h":    round(age_h, 1),
        })

    if not scored:
        return {"score": 0.0, "signal": "NEUTRAL", "article_count": 0,
                "top_headlines": [], "avg_compound": 0.0}

    # Weighted average by time-decay
    total_weight  = sum(s["decay"] for s in scored)
    weighted_comp = sum(s["compound"] * s["decay"] for s in scored) / (total_weight + 1e-10)

    # Clip and convert to [-1, +1]
    score = float(np.clip(weighted_comp, -1, 1))

    if score > 0.15:
        signal = "BULLISH"
    elif score < -0.15:
        signal = "BEARISH"
    else:
        signal = "NEUTRAL"

    # Top 3 most recent headlines with their scores
    top = sorted(scored, key=lambda x: -x["decay"])[:3]

    return {
        "score":        round(score, 4),
        "signal":       signal,
        "article_count":len(scored),
        "avg_compound": round(float(np.mean([s["compound"] for s in scored])), 4),
        "top_headlines": [
            {"title": h["title"], "compound": round(h["compound"], 3), "age_h": h["age_h"]}
            for h in top
        ],
    }
