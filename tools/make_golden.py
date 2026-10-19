"""Freeze the financial engine's current outputs as a golden master.

Run from the project root:  python tools/make_golden.py

The snapshot (tests/golden/engine_golden.json) records every number the app can show for the four
synthetic families, two cover bases and the guided plan, plus the protected assumptions themselves. Tests
compare the live engine and the API against it, so a change to the financial model can never slip in
unnoticed: it either leaves these numbers alone or the test fails and the change is reviewed.

Only regenerate after a financial-model change has been explicitly approved, and say so in the changelog.
"""
from __future__ import annotations

import json
import math
import platform
import sys
from dataclasses import fields
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fo import engine, plan  # noqa: E402
from fo.data import make_sample_returns  # noqa: E402
from fo.personas import PERSONAS, profile_to_dict  # noqa: E402

GOLDEN_PATH = ROOT / "tests" / "golden" / "engine_golden.json"
BASES = ("all", "strict")


def plain(x):
    """Turn numpy, pandas and tuples into JSON-safe values. NaN becomes None."""
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (float, np.floating)):
        f = float(x)
        return None if math.isnan(f) else f
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, np.ndarray):
        return [plain(v) for v in x.tolist()]
    if isinstance(x, pd.DataFrame):
        return plain(x.to_dict("records"))
    if isinstance(x, dict):
        return {str(k): plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    return x


def portfolio_dict(pf: engine.Portfolio) -> dict:
    out = {f.name: plain(getattr(pf, f.name)) for f in fields(pf) if f.name != "replay_returns"}
    r = pf.replay_returns
    out["replay"] = {
        "days": int(len(r)),
        "final_value_of_1": float(np.prod(1.0 + r.to_numpy())),
        "sum_of_returns": float(r.sum()),
        "worst_day": float(r.min()),
    }
    return out


def analysis(profile, daily, inputs, basis: str) -> dict:
    current = engine.analyse_current(profile, daily, basis, inputs)
    options = engine.recommend(profile, daily, basis, inputs)
    by_label = {}
    for pf in options:
        by_label[pf.label] = {
            "action_plan": plain(engine.action_plan(profile, pf)),
            "scenarios": plain(engine.run_scenarios(profile, pf)),
            "insights": plain(engine.build_insights(profile, current, pf)),
            "ladder": plain(engine.liquidity_ladder(profile, pf, years=min(profile.horizon_years, 12))),
            "projection": plain(engine.project_corpus(profile, pf.exp_return)),
        }
    table = engine.compare_options(profile, [current] + options, engine.SCENARIOS["Equities fall 25%"])
    return {
        "current": portfolio_dict(current),
        "current_projection": plain(engine.project_corpus(profile, current.exp_return)),
        "portfolios": [portfolio_dict(pf) for pf in options],
        "per_portfolio": by_label,
        "upcoming_outflows": plain(engine.upcoming_outflows(profile, 5)),
        "compare_equities_fall_25": plain(table),
        "compare_insights": plain(engine.comparison_insights(table)),
    }


GUIDED_CASES = {
    "default_family": lambda: {**plan.default_answers(), "amounts": plan.typical_split(plan.default_answers()["wealth"])},
    "family_with_commitments": lambda: {
        "name": "Golden family", "wealth": 250.0, "spending": 6.0, "risk": "Grow", "months": 18,
        "commitments": [("Education", 5, 4.0), ("Wedding", 8, 6.0)], "amounts": plan.typical_split(250.0),
    },
}


def guided(daily, inputs, answers: dict) -> dict:
    base = plan.profile_from_answers(answers)
    out = {"profile": plain(profile_to_dict(base)), "answers_risk": answers["risk"], "strategies": {}}
    for risk, spec in plan.RISK_CHOICES.items():
        variant = plan.variant_profile(base, risk)
        pf = next(p for p in engine.recommend(variant, daily, "strict", inputs) if p.label == spec["portfolio"])
        out["strategies"][risk] = {
            "portfolio": portfolio_dict(pf),
            "rolling_year": plain(plan.rolling_year_range(pf.replay_returns)),
            "description": plan.describe_strategy(variant, pf, risk),
            "scenarios": plain(engine.run_scenarios(variant, pf)),
            "action_plan": plain(engine.action_plan(variant, pf)),
        }
    return out


def protected_assumptions() -> dict:
    """Every hard-coded financial assumption, so a silent edit to any of them fails a test."""
    base = plan.profile_from_answers(GUIDED_CASES["default_family"]())
    return plain({
        "inflation": engine.INFLATION,
        "prior_returns": engine.PRIOR_RETURNS,
        "haircuts": engine.HAIRCUTS,
        "risk_positions": engine.RISK_POSITIONS,
        "lambda_step": engine.LAMBDA_STEP,
        "max_steps": engine.MAX_STEPS,
        "cover_bases": engine.COVER_BASES,
        "scenarios": engine.SCENARIOS,
        "risk_choices": plan.RISK_CHOICES,
        "guided_limits": plan.GUIDED_LIMITS,
        "guided_horizon_years": plan.HORIZON_YEARS,
        "guided_illiquid_bucket": {
            "description": base.illiquid.description, "expected_return": base.illiquid.expected_return,
            "volatility": base.illiquid.volatility, "lock_in_years": base.illiquid.lock_in_years,
            "corr_with_equity": base.illiquid.corr_with_equity,
        },
        "personas": {k: profile_to_dict(p) for k, p in PERSONAS.items()},
    })


def build_snapshot() -> dict:
    daily = make_sample_returns()
    inputs = engine.estimate_inputs(daily)
    return {
        "meta": {
            "purpose": "Golden master of the financial engine on the synthetic sample. See tools/make_golden.py.",
            "data": {"source": "make_sample_returns(seed=42)", "rows": int(len(daily)),
                     "first": str(daily.index[0].date()), "last": str(daily.index[-1].date())},
            "generated_with": {"python": platform.python_version(), "numpy": np.__version__,
                               "pandas": pd.__version__, "scipy": scipy.__version__},
        },
        "assumptions": protected_assumptions(),
        "inputs": plain({"mu": inputs.mu, "hist_mu": inputs.hist_mu, "prior_mu": inputs.prior_mu,
                         "cov": inputs.cov, "shrink_delta": inputs.shrink_delta}),
        "families": {
            key: {basis: analysis(profile, daily, inputs, basis) for basis in BASES}
            for key, profile in PERSONAS.items()
        },
        "guided": {name: guided(daily, inputs, make()) for name, make in GUIDED_CASES.items()},
    }


def main() -> None:
    snapshot = build_snapshot()
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(json.dumps(snapshot, indent=1, sort_keys=True), encoding="utf-8", newline="\n")
    print(f"Wrote {GOLDEN_PATH} ({GOLDEN_PATH.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
