from dataclasses import replace

import numpy as np
import pytest

from fo import engine
from fo.data import ASSET_CLASSES, make_sample_returns
from fo.personas import PERSONAS


@pytest.fixture(scope="module")
def daily():
    return make_sample_returns()


@pytest.fixture(scope="module")
def inputs(daily):
    return engine.estimate_inputs(daily)


# --- hand-worked cases -----------------------------------------------------------------------
def test_max_drawdown_hand_example():
    # values 1.0, 1.1, 0.88, 0.924: peak 1.1, trough 0.88, drawdown = 0.22 / 1.1 = 0.2
    assert engine.max_drawdown([0.10, -0.20, 0.05]) == pytest.approx(0.2)


def test_max_drawdown_never_negative_for_rising_series():
    assert engine.max_drawdown([0.01] * 50) == 0.0


def test_required_cover_matches_hand_calculation():
    a = PERSONAS["A"]  # 36 months, spending 8, one-off of 12 in year 2 (inside window), 20 in year 4 (outside)
    expected = 8 / 12 * 12 * (1 + 0.045) ** 0 + 8 * 1.045 + 8 * 1.045**2 + 12
    assert engine.required_cover_cr(a) == pytest.approx(expected)


def test_shrunk_covariance_is_symmetric_positive_semidefinite(inputs):
    cov = inputs.cov
    assert np.allclose(cov, cov.T)
    assert np.linalg.eigvalsh(cov).min() > -1e-12
    assert 0.0 <= inputs.shrink_delta <= 1.0


# --- constraints respected ---------------------------------------------------------------------
@pytest.mark.parametrize("key", ["A", "B", "C"])
@pytest.mark.parametrize("basis", ["all", "strict"])
def test_weights_respect_sum_and_limits(key, basis, daily, inputs):
    p = PERSONAS[key]
    for pf in engine.recommend(p, daily, basis, inputs):
        assert pf.weights_sleeve.sum() == pytest.approx(1.0)
        for i, c in enumerate(ASSET_CLASSES):
            lo, hi = p.limits[c]
            assert lo - 1e-6 <= pf.weights_sleeve[i] <= hi + 1e-6
        assert sum(pf.weights_total.values()) == pytest.approx(1.0)
        assert pf.weights_total["Illiquid"] == pytest.approx(p.illiquid_share)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_liquidity_requirement_met_unless_flagged(key, daily, inputs):
    p = PERSONAS[key]
    for pf in engine.recommend(p, daily, "all", inputs):
        if not pf.liquidity_infeasible:
            assert pf.available_cover_cr >= pf.required_cover_cr - 1e-6


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_drawdown_within_limit_unless_flagged(key, daily, inputs):
    p = PERSONAS[key]
    for pf in engine.recommend(p, daily, "all", inputs):
        if pf.dd_ok:
            assert pf.max_dd <= p.max_drawdown + 1e-9
        else:
            assert pf.max_dd > p.max_drawdown


# --- behavioural sanity ------------------------------------------------------------------------
@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_higher_risk_aversion_never_raises_volatility(key, inputs):
    p = PERSONAS[key]
    vols = []
    for lam in (1.0, 3.0, 8.0, 20.0, 60.0):
        sol = engine.solve_weights(p, inputs, lam)
        vols.append(engine._stats(p, inputs, sol.w)[1])
    assert all(b <= a + 1e-9 for a, b in zip(vols, vols[1:]))


def test_stricter_liquidity_requirement_never_raises_expected_return(inputs):
    p = PERSONAS["A"]
    returns = []
    for months in (12, 60, 120, 240):
        q = replace(p, cover_months=months)
        sol = engine.solve_weights(q, inputs, 8.0, "strict")
        returns.append(engine._stats(q, inputs, sol.w)[0])
    # 1e-6 absorbs SLSQP termination noise (observed about 1e-7); a binding constraint moves returns by ~1e-2.
    assert all(b <= a + 1e-6 for a, b in zip(returns, returns[1:]))
    assert returns[-1] < returns[0] - 1e-3  # the stricter requirement must actually cost something


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_three_portfolios_are_distinct_and_ordered_by_risk(key, daily, inputs):
    pfs = engine.recommend(PERSONAS[key], daily, "all", inputs)
    assert [pf.label for pf in pfs] == ["Growth", "Balanced", "Defensive"]
    assert pfs[0].vol > pfs[1].vol > pfs[2].vol
    assert not np.allclose(pfs[0].weights_sleeve, pfs[2].weights_sleeve, atol=1e-3)


def test_sample_data_realised_means_match_targets(daily):
    realised = daily.mean().to_numpy() * 252
    assert np.allclose(realised, [0.12, 0.14, 0.07, 0.08, 0.06], atol=1e-9)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_current_allocation_is_analysed_like_a_recommendation(key, daily, inputs):
    p = PERSONAS[key]
    cur = engine.analyse_current(p, daily, "all", inputs)
    assert cur.label == "Current"
    assert cur.weights_sleeve.sum() == pytest.approx(1.0)
    assert sum(cur.weights_total.values()) == pytest.approx(1.0)
    assert cur.weights_total["Illiquid"] == pytest.approx(p.illiquid_share)
    assert cur.max_dd > 0 and cur.vol > 0
    assert cur.dd_ok == (cur.max_dd <= p.max_drawdown)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_action_plan_buys_and_sells_net_to_zero(key, daily, inputs):
    p = PERSONAS[key]
    rec = engine.recommend(p, daily, "all", inputs)[1]
    plan = engine.action_plan(p, rec)
    assert len(plan) == 5  # the illiquid bucket is never traded
    assert plan["Change (INR cr)"].sum() == pytest.approx(0.0, abs=1e-6)
    assert plan["Recommended (INR cr)"].sum() == pytest.approx(p.corpus_cr * p.sleeve_share)


def test_projection_starts_at_corpus_and_pays_outflows(daily, inputs):
    p = PERSONAS["A"]
    flat = engine.project_corpus(p, 0.0)
    assert flat.loc[0, "Nominal (INR cr)"] == p.corpus_cr
    # with zero return, year 1 value is corpus minus year-1 spending
    assert flat.loc[1, "Nominal (INR cr)"] == pytest.approx(p.corpus_cr - p.annual_spending_cr)
    assert len(flat) == p.horizon_years + 1
    assert (engine.project_corpus(p, 0.12)["Nominal (INR cr)"] >= flat["Nominal (INR cr)"]).all()


def test_upcoming_outflows_include_one_offs_in_the_right_year():
    p = PERSONAS["A"]  # one-offs in years 2, 4 and 7
    table = engine.upcoming_outflows(p, 5).set_index("Year")
    assert table.loc[2, "One-off (INR cr)"] == 12 and table.loc[4, "One-off (INR cr)"] == 20
    assert table.loc[1, "One-off (INR cr)"] == 0
    assert table.loc[3, "Total (INR cr)"] == pytest.approx(8 * 1.045**2)


@pytest.mark.parametrize("key", ["A", "B", "C"])
def test_insights_are_well_formed(key, daily, inputs):
    p = PERSONAS[key]
    pfs = engine.recommend(p, daily, "all", inputs)
    cur = engine.analyse_current(p, daily, "all", inputs)
    insights = engine.build_insights(p, cur, pfs[1])
    assert len(insights) >= 4
    assert all(i["tone"] in {"good", "warn", "info"} and i["title"] and i["body"] for i in insights)
    assert not any("INR" in i["body"] for i in insights)  # amounts use the rupee-crore format


def test_custom_scenario_matches_the_equivalent_preset(daily, inputs):
    p = PERSONAS["A"]
    pf = engine.recommend(p, daily, "all", inputs)[1]
    preset = engine.run_scenarios(p, pf).set_index("Scenario").loc["Market crash"]
    again = engine.scenario_row(p, pf, "Market crash", engine.SCENARIOS["Market crash"])
    assert again["Portfolio value change"] == pytest.approx(preset["Portfolio value change"])
    assert again["Liquidity cover (x required)"] == pytest.approx(preset["Liquidity cover (x required)"])


def test_scenarios_table_has_baseline_and_five_presets(daily, inputs):
    p = PERSONAS["A"]
    pf = engine.recommend(p, daily, "all", inputs)[1]
    table = engine.run_scenarios(p, pf)
    assert len(table) == 6
    crash = table.loc[table["Scenario"] == "Market crash", "Portfolio value change"].iloc[0]
    assert crash < 0
