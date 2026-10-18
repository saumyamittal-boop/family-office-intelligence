from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import numpy as np

from fo import accounts, engine, ui
from fo.data import make_sample_returns
from fo.personas import PERSONAS

APP = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture(scope="module")
def daily():
    return make_sample_returns()


@pytest.fixture(scope="module")
def gap(daily):
    """The ₹1,000 Cr liquidity-gap family under the stricter cover (cash, debt and gold only)."""
    profile = PERSONAS["D"]
    return {
        "profile": profile,
        "current": engine.analyse_current(profile, daily, "strict"),
        "options": engine.recommend(profile, daily, "strict"),
    }


# ---- the slide's numbers --------------------------------------------------------------------------------------------
def test_the_gap_family_needs_120_crore_and_holds_only_50_in_easy_money(gap):
    assert engine.required_cover_cr(gap["profile"]) == pytest.approx(120.0)
    assert gap["current"].available_cover_cr == pytest.approx(50.0)
    assert gap["current"].available_cover_cr / gap["current"].required_cover_cr < 0.5


def test_the_shortfall_is_flagged_automatically(gap):
    insights = engine.build_insights(gap["profile"], gap["current"], gap["options"][1])
    assert any(i["title"] == "Liquidity shortfall" and i["tone"] == "warn" for i in insights)


def test_the_shortfall_is_not_flagged_when_equities_count_as_liquid(daily):
    # With the default cover, equities (haircut) count, so the same family looks fine: why the toggle matters.
    profile = PERSONAS["D"]
    current = engine.analyse_current(profile, daily, "all")
    assert current.available_cover_cr > current.required_cover_cr


def test_a_25_percent_equity_fall_costs_exactly_137_5_crore(gap):
    row = engine.scenario_row(gap["profile"], gap["current"], "x", engine.SCENARIOS["Equities fall 25%"])
    assert row["Value change (INR cr)"] == pytest.approx(-137.5)
    assert row["Portfolio value change"] == pytest.approx(-0.1375)  # the slide's 13.8%


def test_every_option_loses_less_than_the_current_mix_and_restores_the_safety_net(gap):
    table = engine.compare_options(gap["profile"], [gap["current"]] + gap["options"], engine.SCENARIOS["Equities fall 25%"])
    current, options = table.iloc[0], table.iloc[1:]
    assert not current["Cover held"]
    assert (options["Value change (INR cr)"] > current["Value change (INR cr)"] + 20).all()
    assert options["Cover held"].all()


def test_the_safest_option_gives_up_growth(gap):
    table = engine.compare_options(gap["profile"], [gap["current"]] + gap["options"], engine.SCENARIOS["Equities fall 25%"])
    options = table.iloc[1:].set_index("Option")
    assert options.loc["Defensive", "Value change (INR cr)"] > options.loc["Growth", "Value change (INR cr)"]
    assert options.loc["Defensive", "Expected return"] < options.loc["Growth", "Expected return"] < table.iloc[0]["Expected return"]


# ---- the comparison and its plain-language reading -------------------------------------------------------------------
def test_compare_options_has_a_row_per_option_in_order(gap):
    table = engine.compare_options(gap["profile"], [gap["current"]] + gap["options"], engine.SCENARIOS["Market crash"])
    assert list(table["Option"]) == ["Current", "Growth", "Balanced", "Defensive"]
    assert {"Value change", "Value change (INR cr)", "Expected return", "Cover held"} <= set(table.columns)


def test_comparison_insights_name_the_winner_the_price_and_the_shortfall(gap):
    table = engine.compare_options(gap["profile"], [gap["current"]] + gap["options"], engine.SCENARIOS["Equities fall 25%"])
    notes = engine.comparison_insights(table)
    text = " ".join(n["body"] for n in notes)
    assert "Defensive holds up best" in text
    assert "price of that safety is growth" in text
    assert any(n["tone"] == "warn" and "fall short of the safety net" in n["body"] for n in notes)
    assert all(n["tone"] in {"good", "info", "warn"} for n in notes)


def test_comparison_insights_stay_calm_when_nothing_is_wrong(daily):
    profile = PERSONAS["A"]
    current = engine.analyse_current(profile, daily, "all")
    options = engine.recommend(profile, daily, "all")
    table = engine.compare_options(profile, [current] + options, engine.SCENARIOS["Equities fall 25%"])
    notes = engine.comparison_insights(table)
    assert notes and not any("fall short" in n["body"] for n in notes)


def test_the_new_preset_is_in_the_scenario_table_and_changes_only_equities(daily):
    profile = PERSONAS["A"]
    pf = engine.recommend(profile, daily, "all")[1]
    table = engine.run_scenarios(profile, pf)
    assert len(table) == 6  # baseline plus five presets
    assert "Equities fall 25%" in set(table["Scenario"])
    sc = engine.SCENARIOS["Equities fall 25%"]
    assert sc["illiquid"] == 0 and sc["extra_outflow"] == 0 and sc["return_drag"] == 0


# ---- the one-click demo and the page ---------------------------------------------------------------------------------
@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "scenarios_test.db"
    monkeypatch.setattr(accounts, "DB_PATH", path)
    accounts.init_db(path)
    return path


def test_the_liquidity_gap_demo_exists_with_the_right_profile(db):
    demo = accounts.demo_user("gap", db)
    assert demo and demo["is_demo"]
    (_, profile), = accounts.list_profiles(demo["id"], db)
    assert profile.corpus_cr == 1000 and profile.holdings["Cash & liquid"] == 0.05
    assert profile.one_offs == ((1, 100.0),) and profile.cover_months == 12


def test_one_click_demo_opens_with_the_stricter_cover_on_and_the_shortfall_visible(db):
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    next(b for b in at.button if b.label == "₹1,000 Cr liquidity-gap example").click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.session_state["strict_cover"] is True
    text = " ".join(h.value for h in at.get("html"))
    assert "Liquidity shortfall" in text and "0.4x" in text  # flagged on the overview straight away


def test_other_demos_do_not_switch_the_stricter_cover_on(db):
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    next(b for b in at.button if b.label == "Legacy-conservative family").click()
    at.run()
    assert not at.session_state["strict_cover"]


def test_scenarios_page_shows_the_side_by_side_comparison_for_the_demo(db):
    at = AppTest.from_file(str(APP), default_timeout=240)
    at.session_state["user"] = accounts.demo_user("gap", db)
    at.session_state["strict_cover"] = True
    at.run()
    at.switch_page("app_pages/scenarios.py").run()
    assert not at.exception, [e.value for e in at.exception]
    text = " ".join(h.value for h in at.get("html"))
    assert "Compare your options under one scenario" in text
    assert "Defensive holds up best" in text and "fall short of the safety net" in text
    assert "−₹137.5 Cr" in text and "₹-" not in text  # the slide's loss, formatted properly


# ---- formatting -----------------------------------------------------------------------------------------------------
def test_percentages_round_half_up_so_the_slide_figure_matches():
    assert ui.signed_pct(-0.1375) == "−13.8%"  # float formatting alone would print 13.7
    assert ui.pct(0.1375) == "13.8%"
    assert ui.pct(0.0) == "0.0%" and ui.signed_pct(0.0) == "+0.0%"
    assert ui.pct(0.123456, 2) == "12.35%"
    assert ui.signed_cr(-137.5) == "−₹137.5 Cr" and ui.cr(1000) == "₹1,000.0 Cr"


def test_formatting_accepts_numpy_numbers_and_survives_nan():
    assert ui.pct(np.float64(0.0875)) == "8.8%"
    assert ui.signed_pct(np.float64(-0.05)) == "−5.0%"
    assert ui.pct(float("nan")) == "n/a"
