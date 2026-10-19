"""fo.profile_form holds the profile rules that both the Streamlit page and the API apply."""
import copy

import pytest

from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID
from fo.profile_form import build_profile

GOOD = {
    "name": "  Test family ", "corpus": 100.0, "spending": 2.0, "horizon": 20, "max_dd": 15.0, "cover": 12, "target": 4.0,
    "holdings": {"Large-cap equity": 25.0, "Mid-cap equity": 10.0, "Debt": 25.0, "Gold": 5.0, "Cash & liquid": 5.0, ILLIQUID: 30.0},
    "ill_desc": " Property ", "ill_ret": 8.0, "ill_vol": 15.0, "lock": 5, "corr": 0.3,
    "one_offs": [(5, 3.0), (2, 1.0)],
    "limits": [(c, 0.0, 100.0) for c in ASSET_CLASSES],
}


def build(**changes):
    raw = {**copy.deepcopy(GOOD), **changes}
    return build_profile(raw, key="t")


def test_a_valid_form_becomes_a_profile_with_fractions_sorted_one_offs_and_trimmed_text():
    profile, problems = build()
    assert problems == []
    assert profile.name == "Test family" and profile.illiquid.description == "Property"
    assert profile.max_drawdown == pytest.approx(0.15) and profile.target_real_return == pytest.approx(0.04)
    assert profile.one_offs == ((2, 1.0), (5, 3.0))
    assert sum(profile.holdings.values()) == pytest.approx(1.0)
    assert profile.limits["Gold"] == (0.0, 1.0)


def test_holdings_a_little_off_100_percent_are_normalised_but_far_off_is_an_error():
    profile, _ = build(holdings={**GOOD["holdings"], "Debt": 25.4})
    assert sum(profile.holdings.values()) == pytest.approx(1.0)
    none, problems = build(holdings={**GOOD["holdings"], "Debt": 30.0})
    assert none is None and "100%" in problems[0]


def test_every_rule_reports_its_own_message():
    _, problems = build(name="  ", one_offs=[(25, 1.0), (1, -2.0)], limits=[(c, 60.0, 10.0) for c in ASSET_CLASSES])
    text = " | ".join(problems)
    assert "name" in text and "outside the 20-year horizon" in text and "above zero" in text
    assert "Large-cap equity: the minimum must be between" in text and "can't add up" in text


def test_an_empty_illiquid_description_gets_a_default():
    profile, _ = build(ill_desc="   ")
    assert profile.illiquid.description == "Illiquid holdings"
