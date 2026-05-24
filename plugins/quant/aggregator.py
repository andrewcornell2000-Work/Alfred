from datetime import datetime, timezone
import technical
import risk_agent
import regime as regime_mod
import options_agent
import sentiment_agent
import macro_agent
import markov_regime


def full_analysis(ticker: str) -> dict:
    tech   = technical.analyze(ticker)
    risk   = risk_agent.analyze(ticker)
    opts   = options_agent.analyze(ticker)
    sent   = sentiment_agent.analyze(ticker)
    markov = markov_regime.analyze(ticker)
    reg    = regime_mod.detect(tech, risk, opts, sent, ticker, markov)

    return {
        "ticker":    ticker,
        "technical": tech,
        "risk":      risk,
        "options":   opts,
        "sentiment": sent,
        "markov":    markov,
        "regime":    reg,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def macro_analysis() -> dict:
    return macro_agent.analyze()
