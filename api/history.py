"""The replay of each portfolio over the sample years, shaped for charts.

Daily data is thinned to one point per `STEP_DAYS` trading days so the response stays small. Thinning must not hide the
worst moment, so each drawdown point is the deepest day inside its step, and the headline "worst fall" is the engine's
own number measured on every day. The curve starts from a base day (value 100) so its deepest fall equals the engine's.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from fo import engine

from . import schemas as s

STEP_DAYS = 5  # a week of trading days
FULL_YEAR_DAYS = 252
PARTIAL_BELOW = 0.9 * FULL_YEAR_DAYS  # fewer trading days than this and the calendar year counts as partial

NOTE = (
    "The same constant mix is replayed over the sample years. Illiquid holdings accrue smoothly in this replay, "
    "so real drawdowns would look worse than shown. Past sample returns do not predict future ones."
)


def curves(returns: pd.Series) -> tuple[list[str], list[float], list[float]]:
    """Dates, growth of 100 and drawdown, one point per step, starting from a base day."""
    r = returns.to_numpy(dtype=float)
    value = 100.0 * np.concatenate([[1.0], np.cumprod(1.0 + r)])
    peak = np.maximum.accumulate(value)
    drawdown = value / peak - 1.0
    # Step k covers returns [k*STEP_DAYS, (k+1)*STEP_DAYS); its point is the last day, with the deepest fall inside it.
    ends = list(range(STEP_DAYS, len(r) + 1, STEP_DAYS))
    if not ends or ends[-1] != len(r):
        ends.append(len(r))
    starts = [1] + [e + 1 for e in ends[:-1]]  # positions in `value`, where position 0 is the base day
    thin_value = [value[0]] + [value[e] for e in ends]
    thin_drawdown = [0.0] + [float(drawdown[a : e + 1].min()) for a, e in zip(starts, ends)]
    base = returns.index[0] - pd.offsets.BDay(1)
    dates = [base.date().isoformat()] + [returns.index[e - 1].date().isoformat() for e in ends]
    return dates, [round(float(v), 4) for v in thin_value], [round(v, 6) for v in thin_drawdown]


def annual(returns: pd.Series) -> list[s.AnnualReturn]:
    out = []
    for year, chunk in returns.groupby(returns.index.year):
        out.append(
            s.AnnualReturn(
                year=int(year), portfolio_return=float(np.prod(1.0 + chunk.to_numpy()) - 1.0),
                trading_days=len(chunk), partial=len(chunk) < PARTIAL_BELOW,
            )
        )
    return out


def build(
    profile_id: int, basis: str, source: str, max_drawdown_limit: float,
    portfolios: list[engine.Portfolio],
) -> s.HistoryOut:
    dates: list[str] = []
    result = []
    for pf in portfolios:
        d, value, drawdown = curves(pf.replay_returns)
        dates = dates or d  # every portfolio is replayed over the same days
        result.append(
            s.PortfolioHistory(
                label=pf.label, value=value, drawdown=drawdown, max_drawdown=pf.max_dd, cvar21=pf.cvar21,
                annual=annual(pf.replay_returns),
            )
        )
    return s.HistoryOut(
        profile_id=profile_id, basis=basis, data_source=source, dates=dates, step_days=STEP_DAYS,
        drawdown_limit=max_drawdown_limit, portfolios=result, note=NOTE,
    )
