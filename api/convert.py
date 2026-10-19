"""Convert between API models and the engine's Profile, and engine results into response models."""
from __future__ import annotations

import math

import pandas as pd

from fo import engine
from fo.personas import Profile
from fo.profile_form import build_profile

from . import schemas as s


def _pct(fraction: float) -> float:
    # Rounded so 0.07 -> 7.0 -> 0.07 instead of drifting by a unit in the last place.
    return round(fraction * 100, 10)


def profile_to_out(profile_id: int, p: Profile) -> s.ProfileOut:
    return s.ProfileOut(
        id=profile_id, name=p.name, deciding_constraint=p.deciding_constraint, corpus_cr=p.corpus_cr,
        annual_spending_cr=p.annual_spending_cr, horizon_years=p.horizon_years, max_drawdown=p.max_drawdown,
        cover_months=p.cover_months, target_real_return=p.target_real_return, holdings=dict(p.holdings),
        illiquid=s.IlliquidModel(
            description=p.illiquid.description, expected_return=p.illiquid.expected_return,
            volatility=p.illiquid.volatility, lock_in_years=p.illiquid.lock_in_years,
            corr_with_equity=p.illiquid.corr_with_equity,
        ),
        one_offs=[s.OneOffModel(year=y, amount_cr=a) for y, a in p.one_offs],
        limits={c: s.LimitModel(min=lo, max=hi) for c, (lo, hi) in p.limits.items()},
    )


def to_domain(body: s.ProfileIn, key: str) -> tuple[Profile | None, list[str]]:
    """Apply the same rules as the Streamlit profile form (fo.profile_form), so both apps agree."""
    raw = {
        "name": body.name, "corpus": body.corpus_cr, "spending": body.annual_spending_cr,
        "horizon": body.horizon_years, "max_dd": _pct(body.max_drawdown), "cover": body.cover_months,
        "target": _pct(body.target_real_return), "holdings": {c: _pct(v) for c, v in body.holdings.items()},
        "ill_desc": body.illiquid.description, "ill_ret": _pct(body.illiquid.expected_return),
        "ill_vol": _pct(body.illiquid.volatility), "lock": body.illiquid.lock_in_years,
        "corr": body.illiquid.corr_with_equity,
        "one_offs": [(o.year, o.amount_cr) for o in body.one_offs],
        "limits": [(c, _pct(lim.min), _pct(lim.max)) for c, lim in body.limits.items()],
    }
    return build_profile(raw, key=key, deciding_constraint=body.deciding_constraint)


# ---- Engine results -> responses ---------------------------------------------------------------------------------
def _num(x) -> float | None:
    f = float(x)
    return None if math.isnan(f) else f


def portfolio_out(pf: engine.Portfolio) -> s.PortfolioOut:
    return s.PortfolioOut(
        label=pf.label, basis=pf.basis, weights_total={k: float(v) for k, v in pf.weights_total.items()},
        weights_sleeve=[float(v) for v in pf.weights_sleeve], exp_return=pf.exp_return, exp_real=pf.exp_real,
        vol=pf.vol, max_dd=pf.max_dd, cvar21=pf.cvar21, dd_ok=pf.dd_ok, meets_target=pf.meets_target,
        target_gap=pf.target_gap, required_cover_cr=pf.required_cover_cr, available_cover_cr=pf.available_cover_cr,
        cover_fraction=pf.cover_fraction, liquidity_binding=pf.liquidity_binding,
        liquidity_infeasible=pf.liquidity_infeasible, cost_of_liquidity=pf.cost_of_liquidity,
        liquid_return=pf.liquid_return, lam_base=_num(pf.lam_base), lam_used=_num(pf.lam_used),
        bounds_hit=list(pf.bounds_hit), explanation=list(pf.explanation),
        optimiser_converged=pf.optimiser_converged,
    )


def action_rows(table: pd.DataFrame) -> list[s.ActionRow]:
    return [
        s.ActionRow(
            asset_class=r["Asset class"], current_share=r["Current share"], recommended_share=r["Recommended share"],
            current_cr=r["Current (INR cr)"], recommended_cr=r["Recommended (INR cr)"], change_cr=r["Change (INR cr)"],
        )
        for r in table.to_dict("records")
    ]


def scenario_rows(table: pd.DataFrame) -> list[s.ScenarioRow]:
    return [
        s.ScenarioRow(
            scenario=r["Scenario"], value_change=r["Portfolio value change"], value_change_cr=r["Value change (INR cr)"],
            within_drawdown_limit=bool(r["Within drawdown limit"]), cover_ratio=r["Liquidity cover (x required)"],
            cover_held=bool(r["Cover held"]), real_corpus_multiple=r["Real corpus at horizon (x today)"],
        )
        for r in table.to_dict("records")
    ]


def compare_rows(table: pd.DataFrame) -> list[s.CompareRow]:
    return [
        s.CompareRow(
            option=r["Option"], value_change=r["Value change"], value_change_cr=r["Value change (INR cr)"],
            within_drawdown_limit=bool(r["Within drawdown limit"]), cover_ratio_after=r["Liquidity cover after (x required)"],
            cover_held=bool(r["Cover held"]), real_corpus_multiple=r["Real corpus at horizon (x today)"],
            exp_return=r["Expected return"], exp_real=r["Expected real return"], max_dd=r["Worst drawdown in history"],
        )
        for r in table.to_dict("records")
    ]


def ladder_rows(table: pd.DataFrame) -> list[s.LadderRow]:
    return [
        s.LadderRow(
            year=int(r["Year"]), outflows_cr=r["Outflows (INR cr)"], liquid_value_cr=r["Liquid sleeve value (INR cr)"],
            months_covered=r["Months of spending covered"],
        )
        for r in table.to_dict("records")
    ]


def projection_rows(table: pd.DataFrame) -> list[s.ProjectionRow]:
    return [
        s.ProjectionRow(year=int(r["Year"]), nominal_cr=r["Nominal (INR cr)"], real_cr=r["In today's rupees (INR cr)"])
        for r in table.to_dict("records")
    ]


def outflow_rows(table: pd.DataFrame) -> list[s.OutflowRow]:
    return [
        s.OutflowRow(
            year=int(r["Year"]), spending_cr=r["Spending (INR cr)"], one_off_cr=r["One-off (INR cr)"],
            total_cr=r["Total (INR cr)"],
        )
        for r in table.to_dict("records")
    ]


def insights_out(items: list[dict]) -> list[s.InsightOut]:
    return [s.InsightOut(tone=i["tone"], title=i.get("title"), body=i["body"]) for i in items]
