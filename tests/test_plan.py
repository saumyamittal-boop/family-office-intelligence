from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from fo import accounts, engine, plan
from fo.data import ASSET_CLASSES, make_sample_returns
from fo.personas import ILLIQUID

APP = Path(__file__).resolve().parent.parent / "app.py"


def _answers(**overrides):
    base = {**plan.default_answers(), "name": "Test family", "wealth": 200.0, "spending": 6.0,
            "commitments": [("Education", 5, 12.0), ("Wedding", 2, 8.0)], "risk": "Balance", "months": 18}
    base["amounts"] = plan.typical_split(base["wealth"])
    base.update(overrides)
    return base


# ---- turning answers into a profile ----------------------------------------------------------------------------
def test_answers_become_a_valid_profile():
    p = plan.profile_from_answers(_answers())
    assert p.corpus_cr == pytest.approx(200.0, abs=0.05)
    assert sum(p.holdings.values()) == pytest.approx(1.0)
    assert p.holdings[ILLIQUID] == pytest.approx(0.30, abs=0.01)
    assert p.one_offs == ((2, 8.0), (5, 12.0))  # sorted by year, labels dropped
    assert p.cover_months == 18 and p.horizon_years == plan.HORIZON_YEARS
    engine._bounds(p)  # the guided limits must be feasible


@pytest.mark.parametrize("risk, drawdown, target", [("Protect", 0.08, 0.02), ("Balance", 0.15, 0.04), ("Grow", 0.25, 0.06)])
def test_comfort_level_sets_drawdown_and_target(risk, drawdown, target):
    p = plan.profile_from_answers(_answers(risk=risk))
    assert p.max_drawdown == drawdown and p.target_real_return == target


def test_amounts_define_the_corpus_even_if_they_differ_from_the_stated_wealth():
    amounts = plan.typical_split(100.0)
    p = plan.profile_from_answers(_answers(wealth=500.0, amounts=amounts))
    assert p.corpus_cr == pytest.approx(sum(amounts.values()))


def test_typical_split_adds_up_to_the_wealth():
    assert sum(plan.typical_split(250.0).values()) == pytest.approx(250.0, abs=0.1)


# ---- validation ------------------------------------------------------------------------------------------------------
def test_validation_catches_bad_answers():
    assert plan.validate_answers(_answers()) == []
    assert any("owns" in e for e in plan.validate_answers(_answers(amounts={c: 0.0 for c in plan.typical_split(1)})))
    mostly_illiquid = {c: 1.0 for c in ASSET_CLASSES} | {ILLIQUID: 1000.0}
    assert any("5%" in e for e in plan.validate_answers(_answers(amounts=mostly_illiquid)))
    assert any("at most" in e for e in plan.validate_answers(_answers(commitments=[("Other", 1, 1.0)] * 4)))
    assert any("outside" in e for e in plan.validate_answers(_answers(commitments=[("Other", 40, 1.0)])))
    assert any("above zero" in e for e in plan.validate_answers(_answers(commitments=[("Other", 2, 0.0)])))
    with pytest.raises(ValueError):
        plan.profile_from_answers(_answers(commitments=[("Other", 40, 1.0)]))


# ---- yearly ranges --------------------------------------------------------------------------------------------------
def test_rolling_year_range_for_a_constant_return_is_a_single_number():
    daily = np.full(600, 0.0004)
    year = plan.rolling_year_range(daily)
    expected = 1.0004**252 - 1
    assert all(year[k] == pytest.approx(expected) for k in ("low", "median", "high", "worst", "best"))


def test_rolling_year_range_is_ordered_on_realistic_data():
    r = make_sample_returns()["Large-cap equity"].to_numpy()
    year = plan.rolling_year_range(r)
    assert year["worst"] <= year["low"] <= year["median"] <= year["high"] <= year["best"]
    assert year["worst"] < -0.1  # the sample contains a deep crash


# ---- the three strategies ---------------------------------------------------------------------------------------------
def _strategies(**overrides):
    """Strategy A, B, C for one family: each is built for its own comfort level."""
    daily = make_sample_returns()
    base = plan.profile_from_answers(_answers(**overrides))
    out = {}
    for key, spec in plan.RISK_CHOICES.items():
        variant = plan.variant_profile(base, key)
        out[key] = (variant, next(p for p in engine.recommend(variant, daily, "strict") if p.label == spec["portfolio"]))
    return out


def test_variant_profile_changes_only_the_comfort_level():
    base = plan.profile_from_answers(_answers(risk="Balance"))
    grow = plan.variant_profile(base, "Grow")
    assert (grow.max_drawdown, grow.target_real_return) == (0.25, 0.06)
    assert grow.corpus_cr == base.corpus_cr and grow.holdings == base.holdings and grow.one_offs == base.one_offs


def test_strategies_a_to_c_genuinely_differ_in_risk_and_return():
    s = _strategies()
    (_, a), (_, b), (_, c) = s["Protect"], s["Balance"], s["Grow"]
    assert a.vol < b.vol < c.vol
    assert a.max_dd < b.max_dd < c.max_dd
    assert a.exp_return < b.exp_return < c.exp_return  # more risk, more expected return
    assert c.max_dd - a.max_dd > 0.05  # clearly apart, not three near-identical mixes


def test_each_strategy_respects_its_own_comfort_limit():
    for key, (variant, pf) in _strategies().items():
        assert pf.dd_ok and pf.max_dd <= plan.RISK_CHOICES[key]["max_dd"] + 1e-9


def test_plain_language_description_uses_no_jargon_and_states_the_essentials():
    variant, pf = _strategies()["Balance"]
    text = " ".join(plan.describe_strategy(variant, pf, "Balance"))
    assert "₹" in text and "shares" in text and "months" in text and "after inflation" in text
    for jargon in ("volatility", "CVaR", "risk aversion", "Sharpe", "covariance"):
        assert jargon.lower() not in text.lower()


def test_every_comfort_level_maps_to_a_real_portfolio_label():
    daily = make_sample_returns()
    labels = {p.label for p in engine.recommend(plan.profile_from_answers(_answers()), daily, "strict")}
    assert {v["portfolio"] for v in plan.RISK_CHOICES.values()} == labels


def test_every_asset_class_has_a_plain_instrument_description():
    for name in ASSET_CLASSES + [ILLIQUID]:
        label, blurb = plan.INSTRUMENTS[name]
        assert label and blurb


# ---- the wizard in the app -----------------------------------------------------------------------------------------------
@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "plan_test.db"
    monkeypatch.setattr(accounts, "DB_PATH", path)
    accounts.init_db(path)
    return path


def _click(at, label):
    next(b for b in at.button if b.label == label).click()
    return at.run()


def test_a_brand_new_account_lands_on_the_guided_plan(db):
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    at.text_input(key="signup_user").set_value("newcomer_fo")
    at.text_input(key="signup_pass").set_value("newcomer password 1")
    _click(at, "Create account")
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(h.value for h in at.get("html"))
    assert "Plan my money" in text and "Tell us about the family" in text  # step one of the wizard
    assert "Welcome back" not in text  # not the overview


def test_a_returning_demo_user_still_lands_on_the_overview(db):
    at = AppTest.from_file(str(APP), default_timeout=240)
    at.session_state["user"] = accounts.demo_user("legacy", db)
    at.run()
    text = " ".join(h.value for h in at.get("html"))
    assert "Welcome back" in text and "Tell us about the family" not in text


def test_wizard_walkthrough_ends_in_three_strategies_and_saves_a_profile(db):
    user = accounts.create_user("wizard_fo", "wizard password 1", db)
    at = AppTest.from_file(str(APP), default_timeout=240)
    at.session_state["user"] = user
    at.run()
    at.switch_page("app_pages/plan.py").run()
    assert not at.exception

    at.text_input[0].set_value("Walkthrough family")
    _click(at, "Continue")  # step 1 -> 2
    _click(at, "Continue")  # no commitments
    at.radio[0].set_value("Grow")
    _click(at, "Continue")  # comfort
    _click(at, "Continue")  # safety net
    _click(at, "See my strategies")
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error

    text = " ".join(h.value for h in at.get("html"))
    assert "Strategy C" in text and "Recommended for you" in text
    assert "Three ways to run" in text and "Large-cap index fund" in text

    before = len(accounts.list_profiles(user["id"], db))
    _click(at, "Save Strategy C to my profiles")
    after = accounts.list_profiles(user["id"], db)
    assert len(after) == before + 1
    saved = next(p for _, p in after if p.name == "Walkthrough family · Strategy C")
    assert saved.max_drawdown == plan.RISK_CHOICES["Grow"]["max_dd"]  # the saved profile is built for that strategy
    assert not at.exception
