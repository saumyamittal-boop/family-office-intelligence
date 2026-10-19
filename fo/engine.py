"""Allocation engine: estimation, constrained optimisation, drawdown replay, liquidity and scenarios.

Conventions (docs/requirements.md section 5.8, ADR-0013):
- The illiquid bucket is held fixed. Only the five market-data classes (the "liquid sleeve") are optimised.
- Class limits apply to the sleeve. Reported weights are shares of total corpus.
- The drawdown limit is enforced by replaying the portfolio through the daily history and raising the
  risk aversion until the worst drawdown fits (ADR-0005).
- Target real return is a reported goal, not a constraint.

Simplifications in this sample: the replay holds constant weights (daily rebalancing) with no costs, and
the illiquid bucket accrues smoothly at its assumed return.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.optimize import linprog, minimize

from .data import ASSET_CLASSES, TRADING_DAYS
from .personas import Profile

LARGE, MID, DEBT, GOLD, CASH = ASSET_CLASSES
EQUITY = (LARGE, MID)

INFLATION = 0.045
# Prior half of the 50/50 return blend (draft values, docs/personas-and-assumptions.md section 2).
PRIOR_RETURNS = {LARGE: 0.11, MID: 0.125, DEBT: 0.07, GOLD: 0.065, CASH: 0.06}
# Share of value NOT counted towards the liquidity cover (draft values, section 3).
HAIRCUTS = {CASH: 0.0, DEBT: 0.08, GOLD: 0.15, LARGE: 0.30, MID: 0.40}

# Each level sits at a position between the lowest-risk and the highest-return mix the limits allow,
# measured in volatility (1.0 = highest return). This keeps the three portfolios distinct whatever the
# data or limits, instead of using fixed risk-aversion values that can all land on the same corner.
RISK_POSITIONS = (("Growth", 0.75), ("Balanced", 0.50), ("Defensive", 0.25))
LAMBDA_STEP = 1.35
MAX_STEPS = 30

COVER_BASES = {
    "all": "All liquid tiers, haircut-adjusted (as specified)",
    "strict": "Cash, debt and gold only (stricter; equities not counted)",
}

SCENARIOS = {
    "Equities fall 25%": {
        "shocks": {LARGE: -0.25, MID: -0.25, DEBT: 0.0, GOLD: 0.0, CASH: 0.0},
        "illiquid": 0.0,
        "extra_outflow": 0.0,
        "return_drag": 0.0,
    },
    "Market crash": {
        "shocks": {LARGE: -0.35, MID: -0.45, DEBT: -0.02, GOLD: 0.05, CASH: 0.0},
        "illiquid": -0.20,
        "extra_outflow": 0.0,
        "return_drag": 0.0,
    },
    "Inflation and rate spike": {
        "shocks": {LARGE: -0.12, MID: -0.15, DEBT: -0.09, GOLD: 0.08, CASH: 0.0},
        "illiquid": -0.05,
        "extra_outflow": 0.0,
        "return_drag": 0.0,
    },
    "Large unexpected expense": {
        "shocks": {c: 0.0 for c in ASSET_CLASSES},
        "illiquid": 0.0,
        "extra_outflow": 0.08,
        "return_drag": 0.0,
    },
    "Lost decade": {
        "shocks": {c: 0.0 for c in ASSET_CLASSES},
        "illiquid": 0.0,
        "extra_outflow": 0.0,
        "return_drag": 0.04,
    },
}


# ----------------------------------------------------------------------------------------------
# Estimation
# ----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Inputs:
    mu: np.ndarray  # blended expected returns (annual)
    hist_mu: np.ndarray
    prior_mu: np.ndarray
    cov: np.ndarray  # annual covariance, shrunk
    shrink_delta: float


def monthly_returns(daily: pd.DataFrame) -> pd.DataFrame:
    return daily.groupby(daily.index.to_period("M")).apply(lambda x: (1 + x).prod() - 1)


def shrink_cov(x: np.ndarray) -> tuple[np.ndarray, float]:
    """Covariance with correlations shrunk towards zero (Schaefer-Strimmer intensity).

    Variances are kept as estimated, so a low-risk class such as cash is not distorted.
    """
    n, p = x.shape
    sd = x.std(axis=0, ddof=1)
    z = (x - x.mean(axis=0)) / sd
    corr = z.T @ z / (n - 1)
    w = z[:, :, None] * z[:, None, :]
    var_r = n / (n - 1) ** 3 * ((w - w.mean(axis=0)) ** 2).sum(axis=0)
    off = ~np.eye(p, dtype=bool)
    delta = float(np.clip(var_r[off].sum() / (corr[off] ** 2).sum(), 0.0, 1.0))
    corr_shrunk = corr.copy()
    corr_shrunk[off] *= 1.0 - delta
    return corr_shrunk * np.outer(sd, sd), delta


def estimate_inputs(daily: pd.DataFrame) -> Inputs:
    monthly = monthly_returns(daily)
    cov_m, delta = shrink_cov(monthly.to_numpy())
    hist = daily.mean().to_numpy() * TRADING_DAYS
    prior = np.array([PRIOR_RETURNS[c] for c in ASSET_CLASSES])
    return Inputs(mu=0.5 * hist + 0.5 * prior, hist_mu=hist, prior_mu=prior, cov=cov_m * 12, shrink_delta=delta)


def _extended(profile: Profile, inputs: Inputs) -> tuple[np.ndarray, np.ndarray]:
    """Expected returns and covariance with the illiquid bucket appended as a sixth asset."""
    p = len(ASSET_CLASSES)
    ill = profile.illiquid
    mu = np.append(inputs.mu, ill.expected_return)
    cov = np.zeros((p + 1, p + 1))
    cov[:p, :p] = inputs.cov
    sd = np.sqrt(np.diag(inputs.cov))
    for i, c in enumerate(ASSET_CLASSES):
        rho = ill.corr_with_equity if c in EQUITY else 0.0
        cov[i, p] = cov[p, i] = rho * sd[i] * ill.volatility
    cov[p, p] = ill.volatility**2
    return mu, cov


# ----------------------------------------------------------------------------------------------
# Liquidity
# ----------------------------------------------------------------------------------------------
def required_cover_cr(profile: Profile) -> float:
    """Outflows to be covered over the cover window: spending (inflation-indexed) plus dated one-offs."""
    total = 0.0
    for m in range(1, profile.cover_months + 1):
        total += profile.annual_spending_cr / 12 * (1 + INFLATION) ** ((m - 1) // 12)
    for year, amount in profile.one_offs:
        if 12 * year <= profile.cover_months:
            total += amount
    return total


def cover_factors(basis: str) -> np.ndarray:
    """Per-class share of value that counts towards the cover."""
    f = np.array([1.0 - HAIRCUTS[c] for c in ASSET_CLASSES])
    if basis == "strict":
        for i, c in enumerate(ASSET_CLASSES):
            if c in EQUITY:
                f[i] = 0.0
    return f


# ----------------------------------------------------------------------------------------------
# Optimisation
# ----------------------------------------------------------------------------------------------
@dataclass
class Solution:
    w: np.ndarray  # sleeve weights
    liquidity_infeasible: bool
    success: bool


def _bounds(profile: Profile) -> tuple[np.ndarray, np.ndarray]:
    lo = np.array([profile.limits[c][0] for c in ASSET_CLASSES])
    hi = np.array([profile.limits[c][1] for c in ASSET_CLASSES])
    if lo.sum() > 1 + 1e-9 or hi.sum() < 1 - 1e-9:
        raise ValueError("The class limits cannot add up to 100% of the liquid sleeve.")
    return lo, hi


def solve_weights(
    profile: Profile, inputs: Inputs, lam: float, basis: str = "all", enforce_liquidity: bool = True
) -> Solution:
    lo, hi = _bounds(profile)
    s, ill = profile.sleeve_share, profile.illiquid_share
    mu_ext, cov_ext = _extended(profile, inputs)

    def total(w: np.ndarray) -> np.ndarray:
        return np.append(s * w, ill)

    def objective(w: np.ndarray) -> float:
        wt = total(w)
        return float(-(wt @ mu_ext - 0.5 * lam * wt @ cov_ext @ wt))

    f = cover_factors(basis)
    need = required_cover_cr(profile) / (profile.corpus_cr * s)  # as a share of the sleeve
    constraints = [{"type": "eq", "fun": lambda w: w.sum() - 1.0}]

    spread = (hi - lo).sum()
    w0 = lo + (1.0 - lo.sum()) * (hi - lo) / spread if spread > 0 else lo.copy()

    infeasible = False
    if enforce_liquidity:
        lp = linprog(-f, A_eq=[np.ones(len(f))], b_eq=[1.0], bounds=list(zip(lo, hi)))
        best_cover = float(f @ lp.x)
        target = need
        if best_cover < need - 1e-9:
            infeasible = True
            target = best_cover * (1 - 1e-6)
        constraints.append({"type": "ineq", "fun": lambda w: f @ w - target})
        if f @ w0 < target:
            w0 = lp.x

    res = minimize(
        objective, w0, method="SLSQP", bounds=list(zip(lo, hi)), constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    w = np.clip(res.x, lo, hi)
    return Solution(w=w / w.sum(), liquidity_infeasible=infeasible, success=bool(res.success))


# ----------------------------------------------------------------------------------------------
# Risk measurement
# ----------------------------------------------------------------------------------------------
def replay(profile: Profile, w_sleeve: np.ndarray, daily: pd.DataFrame) -> pd.Series:
    """Daily return of the whole corpus at constant weights, illiquid bucket accruing smoothly."""
    s, ill = profile.sleeve_share, profile.illiquid_share
    ill_daily = (1 + profile.illiquid.expected_return) ** (1 / TRADING_DAYS) - 1
    return pd.Series(daily.to_numpy() @ (s * w_sleeve) + ill * ill_daily, index=daily.index)


def max_drawdown(returns) -> float:
    values = np.concatenate([[1.0], np.cumprod(1.0 + np.asarray(returns))])
    peak = np.maximum.accumulate(values)
    return float(np.max(1.0 - values / peak))


def cvar_21d(returns, level: float = 0.95) -> float:
    """Average loss in the worst (1 - level) of rolling 21-trading-day windows, as a positive number."""
    c = np.log1p(np.asarray(returns)).cumsum()
    window = np.exp(c[21:] - c[:-21]) - 1.0
    cutoff = np.quantile(window, 1.0 - level)
    return float(-window[window <= cutoff].mean())


# ----------------------------------------------------------------------------------------------
# Recommendation
# ----------------------------------------------------------------------------------------------
@dataclass
class Portfolio:
    label: str
    lam_base: float
    lam_used: float
    basis: str
    weights_sleeve: np.ndarray
    weights_total: dict
    exp_return: float
    exp_real: float
    vol: float
    max_dd: float
    cvar21: float
    dd_ok: bool
    meets_target: bool
    target_gap: float
    required_cover_cr: float
    available_cover_cr: float
    cover_fraction: float
    liquidity_binding: bool
    liquidity_infeasible: bool
    cost_of_liquidity: float
    liquid_return: float
    bounds_hit: list = field(default_factory=list)
    explanation: list = field(default_factory=list)
    replay_returns: pd.Series | None = None
    optimiser_converged: bool = True  # False if the solver reported failure for the mix that was kept


def _stats(profile: Profile, inputs: Inputs, w_sleeve: np.ndarray) -> tuple[float, float, float]:
    mu_ext, cov_ext = _extended(profile, inputs)
    wt = np.append(profile.sleeve_share * w_sleeve, profile.illiquid_share)
    exp = float(wt @ mu_ext)
    return exp, float(np.sqrt(wt @ cov_ext @ wt)), (1 + exp) / (1 + INFLATION) - 1


def _lambda_at_position(
    profile: Profile, inputs: Inputs, basis: str, position: float, v_min: float, v_max: float
) -> float:
    """Risk aversion whose portfolio volatility sits `position` of the way from v_min to v_max."""
    if v_max - v_min < 1e-6:
        return 8.0  # the limits leave no room to vary risk
    target = v_min + position * (v_max - v_min)
    lo, hi = np.log(1e-3), np.log(1e4)
    for _ in range(30):  # volatility falls as risk aversion rises, so bisect on its logarithm
        mid = 0.5 * (lo + hi)
        w = solve_weights(profile, inputs, float(np.exp(mid)), basis).w
        if _stats(profile, inputs, w)[1] > target:
            lo = mid
        else:
            hi = mid
    return float(np.exp(0.5 * (lo + hi)))


def recommend(
    profile: Profile, daily: pd.DataFrame, basis: str = "all", inputs: Inputs | None = None
) -> list[Portfolio]:
    inputs = inputs or estimate_inputs(daily)
    lo, hi = _bounds(profile)
    s, ill = profile.sleeve_share, profile.illiquid_share
    sleeve_cr = profile.corpus_cr * s
    need_cr = required_cover_cr(profile)
    f = cover_factors(basis)
    out: list[Portfolio] = []

    v_max = _stats(profile, inputs, solve_weights(profile, inputs, 1e-3, basis).w)[1]
    v_min = _stats(profile, inputs, solve_weights(profile, inputs, 1e4, basis).w)[1]

    for label, position in RISK_POSITIONS:
        lam0 = _lambda_at_position(profile, inputs, basis, position, v_min, v_max)
        tried = []
        lam = lam0
        for _ in range(MAX_STEPS):
            sol = solve_weights(profile, inputs, lam, basis)
            r = replay(profile, sol.w, daily)
            tried.append((lam, sol, r, max_drawdown(r)))
            if tried[-1][3] <= profile.max_drawdown:
                break
            lam *= LAMBDA_STEP
        dd_ok = tried[-1][3] <= profile.max_drawdown
        lam_used, sol, r, mdd = tried[-1] if dd_ok else min(tried, key=lambda t: t[3])

        w = sol.w
        exp, vol, real = _stats(profile, inputs, w)
        cover_fraction = float(f @ w)
        available = cover_fraction * sleeve_cr
        binding = (cover_fraction - need_cr / sleeve_cr) < 5e-4
        cost = 0.0
        if binding:
            free = solve_weights(profile, inputs, lam_used, basis, enforce_liquidity=False)
            cost = max(0.0, _stats(profile, inputs, free.w)[0] - exp)

        hits = []
        for i, c in enumerate(ASSET_CLASSES):
            if w[i] >= hi[i] - 1e-4:
                hits.append(f"{c} is at its maximum ({hi[i]:.0%} of the liquid sleeve)")
            elif lo[i] > 0 and w[i] <= lo[i] + 1e-4:
                hits.append(f"{c} is at its minimum ({lo[i]:.0%} of the liquid sleeve)")

        pf = Portfolio(
            label=label, lam_base=lam0, lam_used=lam_used, basis=basis, weights_sleeve=w,
            weights_total={**{c: float(s * w[i]) for i, c in enumerate(ASSET_CLASSES)}, "Illiquid": float(ill)},
            exp_return=exp, exp_real=real, vol=vol, max_dd=mdd, cvar21=cvar_21d(r), dd_ok=dd_ok,
            meets_target=real >= profile.target_real_return, target_gap=real - profile.target_real_return,
            required_cover_cr=need_cr, available_cover_cr=available, cover_fraction=cover_fraction,
            liquidity_binding=binding, liquidity_infeasible=sol.liquidity_infeasible, cost_of_liquidity=cost,
            liquid_return=float(w @ inputs.mu), bounds_hit=hits, replay_returns=r,
            optimiser_converged=sol.success,
        )
        pf.explanation = _explain(profile, pf)
        out.append(pf)
    return out


def _explain(profile: Profile, pf: Portfolio) -> list[str]:
    lines = []
    if not pf.optimiser_converged:
        lines.append(
            "The optimiser did not report a clean solution for this mix, so treat the weights as approximate "
            "and check them before relying on them."
        )
    if not pf.dd_ok:
        lines.append(
            f"Even the safest permitted mix has a historical worst drawdown of {pf.max_dd:.1%}, above your "
            f"{profile.max_drawdown:.0%} limit. This is the closest feasible portfolio."
        )
    elif pf.lam_used > pf.lam_base * 1.0001:
        lines.append(
            f"Risk was tightened (risk aversion {pf.lam_base:.3g} to {pf.lam_used:.3g}) so that the historical "
            f"worst drawdown, {pf.max_dd:.1%}, fits your {profile.max_drawdown:.0%} limit."
        )
    else:
        lines.append(
            f"The historical worst drawdown is {pf.max_dd:.1%}, inside your {profile.max_drawdown:.0%} limit, "
            "so the drawdown cap did not force any change."
        )
    if pf.bounds_hit:
        lines.append("Class limits shaping this portfolio: " + "; ".join(pf.bounds_hit) + ".")
    if pf.liquidity_infeasible:
        lines.append(
            f"Your liquidity requirement (₹{pf.required_cover_cr:.0f} Cr) cannot be met within the class "
            "limits. This is the most liquid mix the limits allow."
        )
    elif pf.liquidity_binding:
        lines.append(
            f"The liquidity cover is binding: the portfolio holds just the ₹{pf.required_cover_cr:.0f} Cr "
            f"needed for {profile.cover_months} months of outflows. Without that requirement, expected return "
            f"would be about {pf.cost_of_liquidity:.2%} a year higher."
        )
    else:
        lines.append(
            f"The liquidity cover is comfortably met (₹{pf.available_cover_cr:.0f} Cr counted against "
            f"₹{pf.required_cover_cr:.0f} Cr needed), so it does not limit this portfolio."
        )
    if pf.meets_target:
        lines.append(
            f"Expected real return is {pf.exp_real:.1%}, above your {profile.target_real_return:.1%} target."
        )
    elif -pf.target_gap < 0.0005:
        lines.append(
            f"Expected real return is {pf.exp_real:.1%}, just under your {profile.target_real_return:.1%} target "
            "(by less than 0.05 percentage points)."
        )
    else:
        lines.append(
            f"Expected real return is {pf.exp_real:.1%}, short of your {profile.target_real_return:.1%} target "
            f"by {-pf.target_gap:.1%}."
        )
    lines.append(
        f"{profile.illiquid_share:.0%} of the corpus is illiquid ({profile.illiquid.description.lower()}) and is "
        "held fixed until its lock-in ends. It is not part of the optimisation."
    )
    return lines


# ----------------------------------------------------------------------------------------------
# Liquidity ladder and scenarios
# ----------------------------------------------------------------------------------------------
def liquidity_ladder(profile: Profile, pf: Portfolio, years: int = 10) -> pd.DataFrame:
    value = profile.corpus_cr * profile.sleeve_share
    rows = []
    for y in range(1, years + 1):
        spend = profile.annual_spending_cr * (1 + INFLATION) ** (y - 1)
        one_off = sum(a for yr, a in profile.one_offs if yr == y)
        outflow = spend + one_off
        value = value * (1 + pf.liquid_return) - outflow
        next_spend = spend * (1 + INFLATION)
        months = max(value, 0.0) * pf.cover_fraction / (next_spend / 12)
        rows.append(
            {"Year": y, "Outflows (INR cr)": outflow, "Liquid sleeve value (INR cr)": value,
             "Months of spending covered": months}
        )
    return pd.DataFrame(rows)


def _project_real_corpus(profile: Profile, start_cr: float, nominal_return: float) -> float:
    value = start_cr
    for y in range(1, profile.horizon_years + 1):
        outflow = profile.annual_spending_cr * (1 + INFLATION) ** (y - 1)
        outflow += sum(a for yr, a in profile.one_offs if yr == y)
        value = value * (1 + nominal_return) - outflow
        if value <= 0:
            return 0.0
    return value / (1 + INFLATION) ** profile.horizon_years / profile.corpus_cr


def scenario_row(profile: Profile, pf: Portfolio, name: str, sc: dict) -> dict:
    """Apply one scenario (a dict shaped like the entries of SCENARIOS) to a portfolio."""
    s, ill = profile.sleeve_share, profile.illiquid_share
    w_liq = s * pf.weights_sleeve
    f = cover_factors(pf.basis)
    shocks = np.array([sc["shocks"][c] for c in ASSET_CLASSES])
    change = float(w_liq @ shocks + ill * sc["illiquid"]) - sc["extra_outflow"]
    liquid_after = profile.corpus_cr * (float((w_liq * (1 + shocks) * f).sum()) - sc["extra_outflow"])
    cover_ratio = liquid_after / pf.required_cover_cr
    projected = _project_real_corpus(profile, profile.corpus_cr * (1 + change), pf.exp_return - sc["return_drag"])
    return {
        "Scenario": name,
        "Portfolio value change": change,
        "Value change (INR cr)": change * profile.corpus_cr,
        "Within drawdown limit": -change <= profile.max_drawdown,
        "Liquidity cover (x required)": cover_ratio,
        "Cover held": cover_ratio >= 1.0,
        "Real corpus at horizon (x today)": projected,
    }


def run_scenarios(profile: Profile, pf: Portfolio) -> pd.DataFrame:
    baseline = {"shocks": {c: 0.0 for c in ASSET_CLASSES}, "illiquid": 0.0, "extra_outflow": 0.0, "return_drag": 0.0}
    rows = [scenario_row(profile, pf, "Baseline (no shock)", baseline)]
    rows += [scenario_row(profile, pf, name, sc) for name, sc in SCENARIOS.items()]
    return pd.DataFrame(rows)


def compare_options(profile: Profile, options: list, scenario: dict) -> pd.DataFrame:
    """One scenario applied to several portfolios, side by side (the current mix plus the recommended options)."""
    rows = []
    for pf in options:
        r = scenario_row(profile, pf, pf.label, scenario)
        rows.append(
            {
                "Option": pf.label,
                "Value change": r["Portfolio value change"],
                "Value change (INR cr)": r["Value change (INR cr)"],
                "Within drawdown limit": r["Within drawdown limit"],
                "Liquidity cover after (x required)": r["Liquidity cover (x required)"],
                "Cover held": r["Cover held"],
                "Real corpus at horizon (x today)": r["Real corpus at horizon (x today)"],
                "Expected return": pf.exp_return,
                "Expected real return": pf.exp_real,
                "Worst drawdown in history": pf.max_dd,
            }
        )
    return pd.DataFrame(rows)


def _signed_cr(value: float) -> str:
    return f"{'+' if value >= 0 else '−'}₹{abs(value):,.1f} Cr"


def comparison_insights(table: pd.DataFrame) -> list[dict]:
    """Plain-language reading of a compare_options table. The first row must be the current mix."""
    current = table.iloc[0]
    others = table.iloc[1:]
    notes: list[dict] = []
    safest = others.loc[others["Value change"].idxmax()]
    less = safest["Value change (INR cr)"] - current["Value change (INR cr)"]
    if less > 0.5:
        notes.append({"tone": "good", "body": f"{safest['Option']} holds up best: it changes by {_signed_cr(safest['Value change (INR cr)'])}, "
                      f"against {_signed_cr(current['Value change (INR cr)'])} for your current mix, ₹{less:,.1f} Cr better."})
    else:
        notes.append({"tone": "info", "body": "None of the options does meaningfully better than your current mix in this scenario."})
    give_up = current["Expected return"] - safest["Expected return"]
    if give_up > 0.0005:
        notes.append({"tone": "info", "body": f"The price of that safety is growth: expected return falls from {current['Expected return']:.1%} to "
                      f"{safest['Expected return']:.1%} a year, about {give_up * 100:.1f} points."})
    growth = others.loc[others["Expected return"].idxmax()]
    if growth["Option"] != safest["Option"]:
        notes.append({"tone": "info", "body": f"{growth['Option']} keeps the most growth ({growth['Expected return']:.1%} expected) and changes by "
                      f"{_signed_cr(growth['Value change (INR cr)'])}: the middle ground between safety and growth."})
    held = [o for o, ok in zip(others["Option"], others["Cover held"]) if ok]
    if not current["Cover held"]:
        notes.append({"tone": "warn", "body": f"Your current mix would fall short of the safety net after this scenario "
                      f"({current['Liquidity cover after (x required)']:.1f}x of what you need). "
                      + (f"{', '.join(held)} {'holds' if len(held) == 1 else 'all hold'} it." if held else "No option holds it.")})
    elif len(held) < len(others):
        notes.append({"tone": "warn", "body": f"Only {', '.join(held) or 'none of the options'} keep the safety net intact in this scenario."})
    return notes


# ----------------------------------------------------------------------------------------------
# Current allocation, action plan, projections and insights (used by the app's overview)
# ----------------------------------------------------------------------------------------------
def analyse_current(
    profile: Profile, daily: pd.DataFrame, basis: str = "all", inputs: Inputs | None = None
) -> Portfolio:
    """Risk, return and liquidity of the family's existing holdings, measured like a recommendation."""
    inputs = inputs or estimate_inputs(daily)
    holdings = np.array([profile.holdings[c] for c in ASSET_CLASSES])
    w = holdings / holdings.sum()  # share of the liquid sleeve
    r = replay(profile, w, daily)
    exp, vol, real = _stats(profile, inputs, w)
    mdd = max_drawdown(r)
    sleeve_cr = profile.corpus_cr * profile.sleeve_share
    need_cr = required_cover_cr(profile)
    cover_fraction = float(cover_factors(basis) @ w)
    return Portfolio(
        label="Current", lam_base=float("nan"), lam_used=float("nan"), basis=basis, weights_sleeve=w,
        weights_total={**{c: float(profile.holdings[c]) for c in ASSET_CLASSES}, "Illiquid": profile.illiquid_share},
        exp_return=exp, exp_real=real, vol=vol, max_dd=mdd, cvar21=cvar_21d(r),
        dd_ok=mdd <= profile.max_drawdown, meets_target=real >= profile.target_real_return,
        target_gap=real - profile.target_real_return, required_cover_cr=need_cr,
        available_cover_cr=cover_fraction * sleeve_cr, cover_fraction=cover_fraction,
        liquidity_binding=False, liquidity_infeasible=False, cost_of_liquidity=0.0,
        liquid_return=float(w @ inputs.mu), replay_returns=r,
    )


def action_plan(profile: Profile, pf: Portfolio) -> pd.DataFrame:
    """What to buy or sell, in INR crore, to move from current holdings to a recommended portfolio."""
    rows = []
    for c in ASSET_CLASSES:
        current = profile.holdings[c] * profile.corpus_cr
        target = pf.weights_total[c] * profile.corpus_cr
        rows.append(
            {
                "Asset class": c,
                "Current share": profile.holdings[c],
                "Recommended share": pf.weights_total[c],
                "Current (INR cr)": current,
                "Recommended (INR cr)": target,
                "Change (INR cr)": target - current,
            }
        )
    return pd.DataFrame(rows)


def project_corpus(profile: Profile, nominal_return: float, years: int | None = None) -> pd.DataFrame:
    """Year-by-year corpus at a constant return, after spending and one-off outflows."""
    years = years or profile.horizon_years
    value = profile.corpus_cr
    rows = [{"Year": 0, "Nominal (INR cr)": value, "In today's rupees (INR cr)": value}]
    for y in range(1, years + 1):
        outflow = profile.annual_spending_cr * (1 + INFLATION) ** (y - 1)
        outflow += sum(a for yr, a in profile.one_offs if yr == y)
        value = max(value * (1 + nominal_return) - outflow, 0.0)
        rows.append({"Year": y, "Nominal (INR cr)": value, "In today's rupees (INR cr)": value / (1 + INFLATION) ** y})
    return pd.DataFrame(rows)


def upcoming_outflows(profile: Profile, years: int = 5) -> pd.DataFrame:
    rows = []
    for y in range(1, years + 1):
        spend = profile.annual_spending_cr * (1 + INFLATION) ** (y - 1)
        one_off = sum(a for yr, a in profile.one_offs if yr == y)
        rows.append({"Year": y, "Spending (INR cr)": spend, "One-off (INR cr)": one_off, "Total (INR cr)": spend + one_off})
    return pd.DataFrame(rows)


def build_insights(profile: Profile, current: Portfolio, recommended: Portfolio) -> list[dict]:
    """Plain-language observations with a tone of "good", "warn" or "info". Rule-based, no LLM."""
    out: list[dict] = []
    plan = action_plan(profile, recommended)
    biggest = plan.reindex(plan["Change (INR cr)"].abs().sort_values(ascending=False).index).iloc[0]
    share_move = abs(biggest["Change (INR cr)"]) / profile.corpus_cr
    if share_move < 0.02:
        out.append({"tone": "good", "title": "Allocation is close to the recommendation",
                    "body": f"No asset class is more than 2% of the corpus away from the {recommended.label} mix."})
    else:
        sells = plan[plan["Change (INR cr)"] < -0.5].sort_values("Change (INR cr)")
        buys = plan[plan["Change (INR cr)"] > 0.5].sort_values("Change (INR cr)", ascending=False)
        parts = []
        if len(sells):
            parts.append(f"reduce {sells.iloc[0]['Asset class']} by ₹{-sells.iloc[0]['Change (INR cr)']:.1f} Cr")
        if len(buys):
            parts.append(f"add ₹{buys.iloc[0]['Change (INR cr)']:.1f} Cr to {buys.iloc[0]['Asset class']}")
        out.append({"tone": "info", "title": "Rebalancing opportunity",
                    "body": f"To move towards the {recommended.label} mix, " + " and ".join(parts) + "."})

    ratio = current.available_cover_cr / current.required_cover_cr
    if ratio < 1.0:
        out.append({"tone": "warn", "title": "Liquidity shortfall",
                    "body": f"Counted liquid assets (₹{current.available_cover_cr:.0f} Cr) are below the ₹"
                            f"{current.required_cover_cr:.0f} Cr needed over the next {profile.cover_months} months."})
    elif ratio < 1.5:
        out.append({"tone": "warn", "title": "Thin liquidity cover",
                    "body": f"Liquid assets cover your next {profile.cover_months} months of outflows only {ratio:.1f} times."})
    else:
        out.append({"tone": "good", "title": "Comfortable liquidity",
                    "body": f"Liquid assets cover your next {profile.cover_months} months of outflows {ratio:.1f} times."})

    if current.dd_ok:
        out.append({"tone": "good", "title": "Drawdown within your limit",
                    "body": f"Your current mix lost at most {current.max_dd:.1%} peak to trough in the sample history, "
                            f"inside your {profile.max_drawdown:.0%} limit."})
    else:
        out.append({"tone": "warn", "title": "Drawdown above your limit",
                    "body": f"Your current mix lost {current.max_dd:.1%} peak to trough in the sample history, above "
                            f"your {profile.max_drawdown:.0%} limit. The {recommended.label} mix lost {recommended.max_dd:.1%}."})

    if current.meets_target:
        out.append({"tone": "good", "title": "On track for your return goal",
                    "body": f"Expected real return is {current.exp_real:.1%} against a {profile.target_real_return:.1%} target."})
    else:
        out.append({"tone": "warn", "title": "Return goal not met",
                    "body": f"Expected real return is {current.exp_real:.1%}, {-current.target_gap:.1%} below your "
                            f"{profile.target_real_return:.1%} target. The {recommended.label} mix expects {recommended.exp_real:.1%}."})

    if profile.illiquid_share >= 0.40:
        out.append({"tone": "warn", "title": "High illiquid share",
                    "body": f"{profile.illiquid_share:.0%} of the corpus ({profile.illiquid.description.lower()}) cannot be "
                            f"sold quickly, with a lock-in of {profile.illiquid.lock_in_years} years."})
    elif profile.illiquid_share >= 0.25:
        out.append({"tone": "info", "title": "Meaningful illiquid holdings",
                    "body": f"{profile.illiquid_share:.0%} of the corpus is illiquid ({profile.illiquid.description.lower()})."})

    near = upcoming_outflows(profile, 3)["Total (INR cr)"].sum()
    sleeve = profile.corpus_cr * profile.sleeve_share
    out.append({"tone": "warn" if near / sleeve > 0.35 else "info", "title": "Planned outflows, next 3 years",
                "body": f"₹{near:.0f} Cr of spending and one-off outflows, {near / sleeve:.0%} of the liquid sleeve."})
    return out
