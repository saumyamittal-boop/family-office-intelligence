"""The API must return exactly the numbers the engine produced before the migration began.

Each demo family is opened through the real HTTP API and compared, field by field, with the frozen
golden master (tests/golden/engine_golden.json, made before any code change).
"""
import json

import pytest

from tests.helpers import demo
from tests.test_golden import differences
from tools.make_golden import GOLDEN_PATH

FAMILY_FOR_DEMO = {"legacy": "A", "business": "B", "nextgen": "C", "gap": "D"}

PORTFOLIO_FIELDS = [
    "label", "basis", "weights_total", "weights_sleeve", "exp_return", "exp_real", "vol", "max_dd", "cvar21",
    "dd_ok", "meets_target", "target_gap", "required_cover_cr", "available_cover_cr", "cover_fraction",
    "liquidity_binding", "liquidity_infeasible", "cost_of_liquidity", "liquid_return", "lam_base", "lam_used",
    "bounds_hit", "explanation",
]
RENAMES = {
    "action_plan": {"Asset class": "asset_class", "Current share": "current_share", "Recommended share": "recommended_share",
                    "Current (INR cr)": "current_cr", "Recommended (INR cr)": "recommended_cr", "Change (INR cr)": "change_cr"},
    "scenarios": {"Scenario": "scenario", "Portfolio value change": "value_change", "Value change (INR cr)": "value_change_cr",
                  "Within drawdown limit": "within_drawdown_limit", "Liquidity cover (x required)": "cover_ratio",
                  "Cover held": "cover_held", "Real corpus at horizon (x today)": "real_corpus_multiple"},
    "ladder": {"Year": "year", "Outflows (INR cr)": "outflows_cr", "Liquid sleeve value (INR cr)": "liquid_value_cr",
               "Months of spending covered": "months_covered"},
    "projection": {"Year": "year", "Nominal (INR cr)": "nominal_cr", "In today's rupees (INR cr)": "real_cr"},
    "outflows": {"Year": "year", "Spending (INR cr)": "spending_cr", "One-off (INR cr)": "one_off_cr", "Total (INR cr)": "total_cr"},
    "compare": {"Option": "option", "Value change": "value_change", "Value change (INR cr)": "value_change_cr",
                "Within drawdown limit": "within_drawdown_limit", "Liquidity cover after (x required)": "cover_ratio_after",
                "Cover held": "cover_held", "Real corpus at horizon (x today)": "real_corpus_multiple",
                "Expected return": "exp_return", "Expected real return": "exp_real", "Worst drawdown in history": "max_dd"},
}


def rename(rows, mapping):
    return [{mapping[k]: v for k, v in row.items()} for row in rows]


def expected_for(golden_case: dict) -> dict:
    """The golden entry for one family and basis, reshaped into the API's field names."""
    pick = lambda pf: {k: pf[k] for k in PORTFOLIO_FIELDS}  # noqa: E731
    options = []
    for portfolio in golden_case["portfolios"]:
        detail = golden_case["per_portfolio"][portfolio["label"]]
        options.append({
            "portfolio": pick(portfolio),
            "action_plan": rename(detail["action_plan"], RENAMES["action_plan"]),
            "scenarios": rename(detail["scenarios"], RENAMES["scenarios"]),
            "insights": detail["insights"],
            "ladder": rename(detail["ladder"], RENAMES["ladder"]),
            "projection": rename(detail["projection"], RENAMES["projection"]),
        })
    return {
        "current": pick(golden_case["current"]),
        "current_projection": rename(golden_case["current_projection"], RENAMES["projection"]),
        "current_ladder": rename(golden_case["current_ladder"], RENAMES["ladder"]),
        "current_scenarios": rename(golden_case["current_scenarios"], RENAMES["scenarios"]),
        "options": options,
        "upcoming_outflows": rename(golden_case["upcoming_outflows"], RENAMES["outflows"]),
        "comparison": rename(golden_case["compare_equities_fall_25"], RENAMES["compare"]),
        "comparison_insights": golden_case["compare_insights"],
    }


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("family", list(FAMILY_FOR_DEMO))
@pytest.mark.parametrize("basis", ["all", "strict"])
def test_api_analysis_matches_the_golden_master(golden, client, family, basis):
    demo(client, family)
    pid = client.get("/api/profiles").json()[0]["id"]
    r = client.get(f"/api/profiles/{pid}/analysis", params={"basis": basis})
    assert r.status_code == 200, r.text
    actual = r.json()
    assert actual["basis"] == basis and actual["data_source"] == "sample"

    expected = expected_for(golden["families"][FAMILY_FOR_DEMO[family]][basis])
    found = list(differences(expected, actual))
    assert not found, f"{family}/{basis} differs from the golden master:\n" + "\n".join(found[:20])


def test_every_recommendation_reports_that_the_optimiser_converged(client):
    for family in FAMILY_FOR_DEMO:
        demo(client, family)
        pid = client.get("/api/profiles").json()[0]["id"]
        for basis in ("all", "strict"):
            data = client.get(f"/api/profiles/{pid}/analysis", params={"basis": basis}).json()
            assert data["current"]["optimiser_converged"] is True
            assert all(o["portfolio"]["optimiser_converged"] for o in data["options"]), (family, basis)


def test_the_slide_figures_come_through_the_api(client):
    demo(client, "gap")
    pid = client.get("/api/profiles").json()[0]["id"]
    data = client.get(f"/api/profiles/{pid}/analysis", params={"basis": "strict"}).json()
    assert data["current"]["required_cover_cr"] == pytest.approx(120.0)
    assert data["current"]["available_cover_cr"] == pytest.approx(50.0)
    rows = {r["option"]: r for r in data["comparison"]}
    assert rows["Current"]["value_change_cr"] == pytest.approx(-137.5)
    assert rows["Current"]["cover_held"] is False
    assert all(rows[o]["cover_held"] for o in ("Growth", "Balanced", "Defensive"))
    assert data["basis_label"].startswith("Cash, debt and gold only")


def test_the_cover_basis_must_be_explicit_and_valid(client):
    demo(client, "legacy")
    pid = client.get("/api/profiles").json()[0]["id"]
    assert client.get(f"/api/profiles/{pid}/analysis").json()["basis"] == "all"  # the documented default
    for bad in ("sloppy", "ALL", "", "strict;drop"):
        assert client.get(f"/api/profiles/{pid}/analysis", params={"basis": bad}).status_code == 422


def test_an_edited_profile_is_reanalysed_and_an_unchanged_one_is_served_from_the_cache(client):
    headers = demo(client, "business")
    pid = client.get("/api/profiles").json()[0]["id"]
    first = client.get(f"/api/profiles/{pid}/analysis").json()
    assert client.get(f"/api/profiles/{pid}/analysis").json() == first

    body = client.get(f"/api/profiles/{pid}").json()
    body.pop("id")
    body["annual_spending_cr"] = body["annual_spending_cr"] * 2
    assert client.put(f"/api/profiles/{pid}", json=body, headers=headers).status_code == 200
    changed = client.get(f"/api/profiles/{pid}/analysis").json()
    assert changed["current"]["required_cover_cr"] > first["current"]["required_cover_cr"]


def test_identical_profiles_share_one_computation_but_each_keeps_its_own_id(client):
    headers = demo(client, "nextgen")
    original = client.get("/api/profiles").json()[0]["id"]
    body = client.get(f"/api/profiles/{original}").json()
    body.pop("id")
    twin = client.post("/api/profiles", json=body, headers=headers).json()["id"]
    a = client.get(f"/api/profiles/{original}/analysis").json()
    b = client.get(f"/api/profiles/{twin}/analysis").json()
    assert a["profile_id"] == original and b["profile_id"] == twin
    assert {**a, "profile_id": 0} == {**b, "profile_id": 0}


def test_a_profile_the_engine_cannot_analyse_gives_a_clear_message_not_a_crash(client, db_path):
    import sqlite3

    headers = demo(client, "legacy")
    pid = client.get("/api/profiles").json()[0]["id"]
    with sqlite3.connect(db_path) as con:  # a stored profile whose class limits cannot add up to 100%
        data = json.loads(con.execute("SELECT data FROM profiles WHERE id = ?", (pid,)).fetchone()[0])
        for limit in data["limits"].values():
            limit[1] = 0.05
        con.execute("UPDATE profiles SET data = ? WHERE id = ?", (json.dumps(data), pid))
    r = client.get(f"/api/profiles/{pid}/analysis")
    assert r.status_code == 422 and "can't be analysed" in r.json()["detail"]
