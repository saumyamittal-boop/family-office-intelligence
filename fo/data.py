"""Market data for the prototype.

By default this module generates SYNTHETIC sample returns so the app runs with no downloads.
The numbers are NOT real market data. To use real data later, put a CSV of daily returns at
data/snapshot/daily_returns.csv (a date index plus one column per asset class below) and
load_returns() will use it instead.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ASSET_CLASSES = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid"]
TRADING_DAYS = 252
SNAPSHOT_PATH = Path(__file__).resolve().parent.parent / "data" / "snapshot" / "daily_returns.csv"

# Parameters used ONLY to generate the synthetic sample (annual arithmetic mean and volatility).
_MU = np.array([0.12, 0.14, 0.07, 0.08, 0.06])
_SIGMA = np.array([0.16, 0.20, 0.035, 0.14, 0.005])
_CORR = np.array(
    [
        [1.00, 0.90, 0.10, 0.00, 0.00],
        [0.90, 1.00, 0.05, 0.00, 0.00],
        [0.10, 0.05, 1.00, 0.10, 0.20],
        [0.00, 0.00, 0.10, 1.00, 0.00],
        [0.00, 0.00, 0.20, 0.00, 1.00],
    ]
)


def _inject_episode(rets: pd.DataFrame, start: str, days: int, total_moves: dict[str, float]) -> None:
    """Spread a total price move per class evenly (in log terms) over `days` trading days."""
    i0 = int(rets.index.searchsorted(pd.Timestamp(start)))
    window = slice(i0, i0 + days)
    for col, move in total_moves.items():
        step = np.log1p(move) / days
        rets.iloc[window, rets.columns.get_loc(col)] = (
            (1 + rets.iloc[window, rets.columns.get_loc(col)]) * np.exp(step) - 1
        )


def make_sample_returns(seed: int = 42) -> pd.DataFrame:
    """Synthetic daily returns for the five asset classes, 2016 to 2025.

    Fat-tailed noise plus two stylised episodes (a sharp crash and rebound in 2020, a rate shock
    in 2022) so that drawdowns are non-trivial. Reproducible for a given seed.
    """
    dates = pd.bdate_range("2016-01-01", "2025-12-31")
    n, p = len(dates), len(ASSET_CLASSES)
    rng = np.random.default_rng(seed)
    chol = np.linalg.cholesky(_CORR)
    t = rng.standard_t(df=5, size=(n, p)) / np.sqrt(5 / 3)  # unit-variance Student-t
    noise = t @ chol.T
    noise -= noise.mean(axis=0)  # exactly zero-mean, so the drift below is the realised mean
    daily = _MU / TRADING_DAYS + _SIGMA / np.sqrt(TRADING_DAYS) * noise
    rets = pd.DataFrame(daily, index=dates, columns=ASSET_CLASSES)

    large, mid, debt, gold, _cash = ASSET_CLASSES
    _inject_episode(rets, "2020-02-20", 25, {large: -0.30, mid: -0.38, debt: -0.02, gold: 0.05})
    _inject_episode(rets, "2020-03-26", 120, {large: 0.32, mid: 0.42})
    _inject_episode(rets, "2022-02-01", 60, {large: -0.10, mid: -0.13, debt: -0.05, gold: 0.04})

    # Re-centre so each class's realised annual arithmetic mean equals its target even after the
    # episodes. Without this, a random 10-year draw can land a few points away from the target.
    realised = rets.mean().to_numpy() * TRADING_DAYS
    return rets + (_MU - realised) / TRADING_DAYS


def load_returns() -> tuple[pd.DataFrame, str]:
    """Return (daily returns, source). Source is "snapshot" or "sample"."""
    if SNAPSHOT_PATH.exists():
        df = pd.read_csv(SNAPSHOT_PATH, index_col=0, parse_dates=True)
        missing = [c for c in ASSET_CLASSES if c not in df.columns]
        if missing:
            raise ValueError(f"Snapshot is missing columns: {missing}")
        return df[ASSET_CLASSES].dropna(), "snapshot"
    return make_sample_returns(), "sample"
