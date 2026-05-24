"""
Observable Markov regime model.

Labels each trading day Bull (2) / Bear (0) / Sideways (1) from a 20-day
rolling return threshold, builds the 3x3 transition matrix via MLE counting,
solves the stationary distribution (Chapman-Kolmogorov eigenvector), and emits
a directional signal for integration into the multi-agent regime detector.
"""
import numpy as np
import pandas as pd
from fetcher import fetch_ohlcv

STATES = ["Bear", "Sideways", "Bull"]  # indices 0, 1, 2


def _label_regimes(close: pd.Series, window: int = 20, threshold: float = 0.02) -> pd.Series:
    """Bull if rolling return > +threshold, Bear if < -threshold, else Sideways."""
    roll = close.pct_change(window)
    labels = pd.Series(1, index=close.index, dtype=int)
    labels[roll >  threshold] = 2
    labels[roll < -threshold] = 0
    return labels.dropna()


def _build_matrix(labels: pd.Series) -> np.ndarray:
    """MLE 3x3 transition matrix counted from the label sequence."""
    counts = np.zeros((3, 3), dtype=float)
    arr = labels.to_numpy()
    for i in range(len(arr) - 1):
        counts[arr[i], arr[i + 1]] += 1
    row_sums = counts.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return counts / row_sums


def _stationary(P: np.ndarray) -> np.ndarray:
    """Left eigenvector with eigenvalue 1 — the long-run regime mix."""
    eigvals, eigvecs = np.linalg.eig(P.T)
    idx = np.argmin(np.abs(eigvals - 1.0))
    vec = np.abs(np.real(eigvecs[:, idx]))
    return vec / vec.sum()


def analyze(ticker: str, window: int = 20, threshold: float = 0.02) -> dict:
    """Transition matrix + stationary distribution + n-step forecasts + signal."""
    try:
        df    = fetch_ohlcv(ticker, period="2y", interval="1d")
        close = df["Close"].dropna()

        labels = _label_regimes(close, window, threshold)
        if len(labels) < window + 50:
            return {"markov_score": 0.0, "error": "insufficient data"}

        P  = _build_matrix(labels)
        pi = _stationary(P)
        current_state = int(labels.iloc[-1])

        # Core signal: P(Bull | current) - P(Bear | current)  in [-1, +1]
        signal = float(P[current_state, 2] - P[current_state, 0])

        # Chapman-Kolmogorov n-step distributions from current state
        P5  = np.linalg.matrix_power(P, 5)
        P20 = np.linalg.matrix_power(P, 20)

        return {
            "markov_score":      round(signal, 4),
            "current_regime":    STATES[current_state],
            "current_state_idx": current_state,
            "transition_matrix": [
                [round(float(P[i, j]) * 100, 1) for j in range(3)]
                for i in range(3)
            ],
            "stationary": [round(float(p) * 100, 1) for p in pi],
            "fwd5":  [round(float(P5[current_state, j])  * 100, 1) for j in range(3)],
            "fwd20": [round(float(P20[current_state, j]) * 100, 1) for j in range(3)],
            "states": STATES,
        }
    except Exception as exc:
        return {"markov_score": 0.0, "error": str(exc)}
