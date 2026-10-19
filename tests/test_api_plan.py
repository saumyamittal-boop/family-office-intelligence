"""The guided plan API: the questions, the live preview, the three strategies, and saving one."""
import json
import time

import pytest

from fo import engine
from fo import plan as fo_plan
from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID
from tests.helpers import demo, profile_body, sign_up
from tests.test_api_parity import PORTFOLIO_FIELDS, RENAMES, rename
from tests.test_golden import differences
from tools.make_golden import GOLDEN_PATH, GUIDED_CASES

ANSWERS = {
    "name": "Test family", "wealth": 200.0, "spending": 6.0, "risk": "Balance", "months": 18,
    "commitments": [{"kind": "Education", "year": 5, "amount_cr": 12.0}, {"kind": "Wedding", "year": 2, "amount_cr": 8.0}],
}


def with_(**changes) -> dict:
    return {**ANSWERS, **changes}


def as_dict(body: dict) -> dict:
    """The same answers in the shape fo.plan works with."""
    return {**body, "commitments": [(c["kind"], c["year"], c["amount_cr"]) for c in body["commitments"]],
            "amounts": body.get("amounts") or fo_plan.typical_split(body["wealth"])}


@pytest.fixture()
def me(client):
    return client, sign_up(client, "plan_owner")


# ---- The questions ----------------------------------------------------------------------------------------------------
def test_the_config_is_public_and_describes_the_form_from_the_model_itself(client):
    r = client.get("/api/plan/config")
    assert r.status_code == 200
    cfg = r.json()
    assert len(cfg["steps"]) == 6 and cfg["steps"][-1] == "Your strategies"
    assert [c["key"] for c in cfg["comfort"]] == ["Protect", "Balance", "Grow"]
    assert {c["key"]: (c["max_drawdown"], c["target_real_return"], c["letter"]) for c in cfg["comfort"]} == {
        k: (v["max_dd"], v["target"], v["strategy"]) for k, v in fo_plan.RISK_CHOICES.items()
    }
    assert [c["name"] for c in cfg["classes"]] == ASSET_CLASSES + [ILLIQUID]
    assert cfg["commitment_kinds"] == fo_plan.COMMITMENT_KINDS and cfg["max_commitments"] == 3 and cfg["horizon_years"] == 25
    assert cfg["defaults"]["risk"] == "Balance" and cfg["months"] == {"min": 3, "max": 36}


def test_the_crash_wording_is_honest_and_built_from_the_scenario_itself(client):
    crash = client.get("/api/plan/config").json()["crash"]
    assert crash["label"] == "In a severe market crash" and "2020" not in crash["label"]
    assert "not a replay" in crash["description"]
    for fragment in ("large-cap equity −35%", "mid-cap equity −45%", "debt −2%", "gold +5%", "illiquid holdings −20%"):
        assert fragment in crash["description"], fragment
    assert engine.SCENARIOS["Market crash"]["shocks"]["Large-cap equity"] == -0.35  # if the preset changes, so does this wording


# ---- Who may call ----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("path", ["/api/plan/preview", "/api/plan/strategies"])
def test_the_plan_endpoints_need_a_signed_in_user_and_the_csrf_token(client, path):
    assert client.post(path, json=ANSWERS).status_code == 401
    headers = sign_up(client, "csrf_planner")
    assert client.post(path, json=ANSWERS).status_code == 403
    assert client.post(path, json=ANSWERS, headers={"X-CSRF-Token": "guess"}).status_code == 403
    assert client.post(path, json=ANSWERS, headers=headers).status_code == 200


def test_saving_needs_a_signed_in_user_and_the_csrf_token(client):
    body = {"answers": ANSWERS, "strategy": "Balance"}
    assert client.post("/api/plan/save", json=body).status_code == 401
    headers = sign_up(client, "csrf_saver")
    assert client.post("/api/plan/save", json=body).status_code == 403
    assert client.post("/api/plan/save", json=body, headers=headers).status_code == 201


# ---- Validation -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("changes", [
    {"wealth": 0}, {"wealth": -5}, {"wealth": 10**9}, {"spending": -1}, {"months": 2}, {"months": 37}, {"risk": "Reckless"},
    {"name": ""}, {"name": "x" * 61}, {"wealth": "a lot"}, {"months": 12.5},
    {"commitments": [{"kind": "Yacht", "year": 2, "amount_cr": 1.0}]},
    {"commitments": [{"kind": "Wedding", "year": 26, "amount_cr": 1.0}]},
    {"commitments": [{"kind": "Wedding", "year": 0, "amount_cr": 1.0}]},
    {"commitments": [{"kind": "Wedding", "year": 2, "amount_cr": 0}]},
    {"commitments": [{"kind": "Wedding", "year": 2, "amount_cr": 1.0, "extra": 1}]},
    {"amounts": {"Crypto": 5.0}}, {"amounts": {"Debt": -1.0}}, {"amounts": {"Debt": "much"}},
    {"user_id": 1}, {"profile_id": 3},
])
def test_malformed_answers_are_rejected_before_any_calculation(me, changes):
    client, headers = me
    for path in ("/api/plan/preview", "/api/plan/strategies"):
        r = client.post(path, json=with_(**changes), headers=headers)
        assert r.status_code == 422, (path, changes, r.status_code)
        assert "Traceback" not in r.text


def test_error_bodies_do_not_echo_the_answers(me):
    client, headers = me
    r = client.post("/api/plan/preview", json=with_(name="SECRET-MARKER", wealth="SECRET-NOT-A-NUMBER"), headers=headers)
    assert r.status_code == 422 and "SECRET" not in r.text


def test_answers_that_pass_the_schema_but_break_a_rule_come_back_as_plain_problems(me):
    client, headers = me
    four = [{"kind": "Other", "year": 1, "amount_cr": 1.0}] * 4
    p = client.post("/api/plan/preview", json=with_(commitments=four), headers=headers).json()
    assert any("at most" in m for m in p["problems"]) and p["safety_net"] is None

    mostly_illiquid = {**{c: 1.0 for c in ASSET_CLASSES}, ILLIQUID: 1000.0}
    p = client.post("/api/plan/preview", json=with_(amounts=mostly_illiquid), headers=headers).json()
    assert any("5%" in m for m in p["problems"])

    nothing = {c: 0.0 for c in ASSET_CLASSES + [ILLIQUID]}
    p = client.post("/api/plan/preview", json=with_(amounts=nothing), headers=headers).json()
    assert any("owns" in m for m in p["problems"])

    r = client.post("/api/plan/strategies", json=with_(commitments=four), headers=headers)
    assert r.status_code == 422 and "at most" in r.json()["problems"][0]


def test_no_spending_and_no_commitment_in_the_window_is_explained_not_a_crash(me):
    client, headers = me
    body = with_(spending=0.0, commitments=[])
    p = client.post("/api/plan/preview", json=body, headers=headers).json()
    assert len(p["problems"]) == 1 and "spends in a typical year" in p["problems"][0]
    r = client.post("/api/plan/strategies", json=body, headers=headers)
    assert r.status_code == 422 and "spends in a typical year" in r.json()["problems"][0]
    # ...but a commitment inside the safety-net window is enough to size it
    ok = with_(spending=0.0, months=24, commitments=[{"kind": "Wedding", "year": 1, "amount_cr": 5.0}])
    assert client.post("/api/plan/preview", json=ok, headers=headers).json()["problems"] == []


def test_a_stored_profile_with_no_spending_gets_a_clear_message_from_the_analysis(client):
    headers = demo(client, "legacy")
    body = profile_body(client)
    body.update(annual_spending_cr=0.0, one_offs=[])
    created = client.post("/api/profiles", json=body, headers=headers).json()
    r = client.get(f"/api/profiles/{created['id']}/analysis")
    assert r.status_code == 422 and "needs some yearly spending" in r.json()["detail"]


# ---- The live preview ----------------------------------------------------------------------------------------------------
def test_preview_sizes_the_safety_net_exactly_as_the_engine_does(me):
    client, headers = me
    p = client.post("/api/plan/preview", json=ANSWERS, headers=headers).json()
    profile = fo_plan.profile_from_answers(as_dict(ANSWERS))
    assert p["safety_net"]["required_cr"] == pytest.approx(engine.required_cover_cr(profile), abs=1e-12)
    assert p["safety_net"]["months"] == 18
    assert p["safety_net"]["commitments_cr"] == 0.0  # 12 x year must be within 18 months: year 2 (24) and year 5 are outside
    assert p["safety_net"]["spending_cr"] == pytest.approx(p["safety_net"]["required_cr"])
    assert p["corpus_cr"] == pytest.approx(profile.corpus_cr)
    assert p["illiquid_cr"] + p["liquid_cr"] == pytest.approx(p["corpus_cr"])
    assert p["illiquid_share"] == pytest.approx(0.30, abs=0.01)


@pytest.mark.parametrize("months, inside", [(6, 0.0), (12, 5.0), (24, 5.0)])
def test_a_commitment_counts_in_the_safety_net_only_when_it_falls_inside_the_window(me, months, inside):
    client, headers = me
    body = with_(months=months, commitments=[{"kind": "Education", "year": 1, "amount_cr": 5.0}])
    p = client.post("/api/plan/preview", json=body, headers=headers).json()
    assert p["safety_net"]["commitments_cr"] == inside  # engine rule: 12 x year <= months
    profile = fo_plan.profile_from_answers(as_dict(body))
    assert p["safety_net"]["required_cr"] == pytest.approx(engine.required_cover_cr(profile))


def test_preview_lists_outflows_and_the_comfort_levels_in_rupees(me):
    client, headers = me
    p = client.post("/api/plan/preview", json=ANSWERS, headers=headers).json()
    assert [o["year"] for o in p["outflows"]] == [1, 2, 3, 4, 5]
    assert p["outflows"][1]["one_off_cr"] == 8.0 and p["outflows"][4]["one_off_cr"] == 12.0
    assert {c["key"]: c["loss_cr"] for c in p["comfort"]} == {
        k: pytest.approx(p["corpus_cr"] * v["max_dd"]) for k, v in fo_plan.RISK_CHOICES.items()
    }
    assert p["near_outflows_cr"] == pytest.approx(sum(o["total_cr"] for o in p["outflows"][:3]))


def test_preview_starts_from_a_typical_split_and_notices_when_the_entered_amounts_differ(me):
    client, headers = me
    p = client.post("/api/plan/preview", json=ANSWERS, headers=headers).json()
    assert p["typical_amounts"] == fo_plan.typical_split(200.0)
    assert p["amounts_differ_from_wealth"] is False and p["amounts_total_cr"] == pytest.approx(200.0, abs=0.1)

    bigger = {k: v * 2 for k, v in fo_plan.typical_split(200.0).items()}
    p = client.post("/api/plan/preview", json=with_(amounts=bigger), headers=headers).json()
    assert p["amounts_differ_from_wealth"] is True and p["corpus_cr"] == pytest.approx(sum(bigger.values()))


def test_preview_effects_state_numbers_that_match_the_rest_of_the_response(me):
    client, headers = me
    p = client.post("/api/plan/preview", json=ANSWERS, headers=headers).json()
    text = " ".join(p["effects"])
    assert "15% of wealth (₹30.0 Cr)" in text  # Balance: 15% of 200 Cr, rounded half up
    assert f"₹{p['safety_net']['required_cr']:.1f} Cr within easy reach" in text
    assert "does not count towards the safety net" in text  # honest about the illiquid holdings
    assert "recommended mix itself is worked out for the" in text  # what the family owns changes the buy/sell, not the mix


def test_preview_never_runs_the_optimiser(me):
    client, headers = me

    def forbidden(*_a, **_k):
        raise AssertionError("the preview must not use the analysis service")

    client.app.state.analysis.analyse = forbidden
    assert client.post("/api/plan/preview", json=ANSWERS, headers=headers).status_code == 200


# ---- The strategies ---------------------------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


def api_body(case: str) -> dict:
    a = GUIDED_CASES[case]()
    return {**a, "commitments": [{"kind": k, "year": y, "amount_cr": amt} for k, y, amt in a["commitments"]]}


@pytest.mark.parametrize("case", ["default_family", "family_with_commitments"])
def test_strategies_match_the_golden_master_field_by_field(golden, me, case):
    client, headers = me
    r = client.post("/api/plan/strategies", json=api_body(case), headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["basis_label"].startswith("Cash, debt and gold only") and data["data_source"] == "sample"

    for strategy in data["strategies"]:
        frozen = golden["guided"][case]["strategies"][strategy["key"]]
        expected = {
            "portfolio": {k: frozen["portfolio"][k] for k in PORTFOLIO_FIELDS},
            "year_range": frozen["rolling_year"],
            "description": frozen["description"],
            "action_plan": rename(frozen["action_plan"], RENAMES["action_plan"]),
        }
        found = list(differences(expected, strategy))
        assert not found, f"{case}/{strategy['key']} differs from the golden master:\n" + "\n".join(found[:15])
        crash = next(row for row in frozen["scenarios"] if row["Scenario"] == "Market crash")
        assert strategy["crash"]["value_change"] == pytest.approx(crash["Portfolio value change"], abs=1e-9)
        assert strategy["crash"]["value_change_cr"] == pytest.approx(crash["Value change (INR cr)"], abs=1e-9)


def test_the_three_strategies_genuinely_differ_and_each_fits_its_own_comfort_level(me):
    client, headers = me
    a, b, c = client.post("/api/plan/strategies", json=ANSWERS, headers=headers).json()["strategies"]
    assert [s["letter"] for s in (a, b, c)] == ["A", "B", "C"]
    pa, pb, pc = (s["portfolio"] for s in (a, b, c))
    assert pa["vol"] < pb["vol"] < pc["vol"] and pa["max_dd"] < pb["max_dd"] < pc["max_dd"]
    assert pa["exp_return"] < pb["exp_return"] < pc["exp_return"] and pc["max_dd"] - pa["max_dd"] > 0.05
    for s in (a, b, c):
        assert s["within_comfort_of"][s["key"]] is True
        assert set(s["within_comfort_of"]) == set(s["meets_goal_of"]) == {"Protect", "Balance", "Grow"}
        assert s["year_range"]["worst"] <= s["year_range"]["low"] <= s["year_range"]["median"] <= s["year_range"]["high"]
        assert s["crash"]["value_change"] < 0 and s["crash"]["value_change_cr"] < 0
        assert s["cover_ratio"] > 0


def test_strategy_c_does_not_fit_a_protective_family_and_a_protective_one_does(me):
    client, headers = me
    _, _, c = client.post("/api/plan/strategies", json=with_(risk="Protect"), headers=headers).json()["strategies"]
    assert c["within_comfort_of"]["Protect"] is False and c["within_comfort_of"]["Grow"] is True


def test_changing_the_comfort_level_returns_the_same_strategies_without_recalculating(me):
    client, headers = me
    service = client.app.state.analysis
    real = service._compute
    calls = []
    service._compute = lambda *a, **k: (calls.append(1), real(*a, **k))[1]

    first = client.post("/api/plan/strategies", json=with_(risk="Protect"), headers=headers).json()
    assert len(calls) == 3  # one analysis per strategy
    for risk in ("Balance", "Grow", "Protect"):
        again = client.post("/api/plan/strategies", json=with_(risk=risk), headers=headers).json()
        assert again == first  # the page can switch comfort level instantly
    assert len(calls) == 3  # and nothing was recomputed


def test_changing_spending_does_recalculate_and_raises_the_safety_net_need(me):
    client, headers = me
    a = client.post("/api/plan/strategies", json=with_(spending=6.0), headers=headers).json()
    b = client.post("/api/plan/strategies", json=with_(spending=12.0), headers=headers).json()
    assert b["strategies"][1]["portfolio"]["required_cover_cr"] > a["strategies"][1]["portfolio"]["required_cover_cr"]


def test_the_action_plan_names_instruments_nets_to_zero_and_keeps_the_illiquid_bucket(me):
    client, headers = me
    data = client.post("/api/plan/strategies", json=ANSWERS, headers=headers).json()
    for s in data["strategies"]:
        rows = s["action_plan"]
        assert [r["asset_class"] for r in rows] == ASSET_CLASSES
        assert sum(r["change_cr"] for r in rows) == pytest.approx(0.0, abs=1e-6)
        for r in rows:
            assert (r["instrument_name"], r["instrument_note"]) == fo_plan.INSTRUMENTS[r["asset_class"]]
        assert (s["illiquid_name"], s["illiquid_note"]) == fo_plan.INSTRUMENTS[ILLIQUID]
        assert s["illiquid_cr"] == pytest.approx(0.30 * data["corpus_cr"], abs=1.0)
    assert [c["kind"] for c in data["commitments"]] == ["Education", "Wedding"]


def test_the_plain_language_description_has_no_jargon(me):
    client, headers = me
    text = " ".join(" ".join(s["description"]) for s in client.post("/api/plan/strategies", json=ANSWERS, headers=headers).json()["strategies"])
    assert "₹" in text and "shares" in text and "after inflation" in text
    for jargon in ("volatility", "CVaR", "risk aversion", "Sharpe", "covariance"):
        assert jargon.lower() not in text.lower()


def test_recalculating_too_quickly_is_slowed_down_with_a_clear_message(me):
    client, headers = me
    for _ in range(40):
        assert client.post("/api/plan/strategies", json=ANSWERS, headers=headers).status_code == 200
    r = client.post("/api/plan/strategies", json=ANSWERS, headers=headers)
    assert r.status_code == 429 and int(r.headers["retry-after"]) > 0 and "very quickly" in r.json()["detail"]


def test_a_slow_model_gives_a_busy_answer_not_a_hang(make_client):
    c = make_client(analysis_timeout=0.2)
    headers = sign_up(c, "slow_planner")
    real = c.app.state.analysis._compute
    c.app.state.analysis._compute = lambda *a, **k: (time.sleep(1.0), real(*a, **k))[1]
    r = c.post("/api/plan/strategies", json=ANSWERS, headers=headers)
    assert r.status_code == 503 and "busy" in r.json()["detail"]


# ---- Saving --------------------------------------------------------------------------------------------------------------------
def test_saving_creates_a_profile_built_for_that_strategy_that_analyses_to_the_same_numbers(me):
    client, headers = me
    before = len(client.get("/api/profiles").json())
    saved = client.post("/api/plan/save", json={"answers": ANSWERS, "strategy": "Grow"}, headers=headers)
    assert saved.status_code == 201 and saved.json()["created"] is True
    profile = saved.json()["profile"]
    assert profile["name"] == "Test family · Strategy C"
    assert profile["max_drawdown"] == fo_plan.RISK_CHOICES["Grow"]["max_dd"]
    assert profile["target_real_return"] == fo_plan.RISK_CHOICES["Grow"]["target"]
    assert len(client.get("/api/profiles").json()) == before + 1

    strategy_c = client.post("/api/plan/strategies", json=ANSWERS, headers=headers).json()["strategies"][2]["portfolio"]
    analysed = client.get(f"/api/profiles/{profile['id']}/analysis", params={"basis": "strict"}).json()
    growth = next(o["portfolio"] for o in analysed["options"] if o["portfolio"]["label"] == "Growth")
    assert growth["exp_return"] == pytest.approx(strategy_c["exp_return"], abs=1e-12)
    assert growth["weights_total"] == pytest.approx(strategy_c["weights_total"], abs=1e-12)


def test_saving_the_same_plan_twice_does_not_make_a_second_copy(me):
    client, headers = me
    body = {"answers": ANSWERS, "strategy": "Balance"}
    first = client.post("/api/plan/save", json=body, headers=headers)
    second = client.post("/api/plan/save", json=body, headers=headers)
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["created"] is False and second.json()["profile"]["id"] == first.json()["profile"]["id"]
    assert len(client.get("/api/profiles").json()) == 2  # the starter profile plus one saved strategy


def test_a_different_strategy_of_the_same_answers_is_a_new_profile(me):
    client, headers = me
    ids = {client.post("/api/plan/save", json={"answers": ANSWERS, "strategy": s}, headers=headers).json()["profile"]["id"] for s in ("Protect", "Balance", "Grow")}
    assert len(ids) == 3


def test_saved_plans_belong_to_their_owner_alone(make_client):
    alice, bob = make_client(), make_client()
    a_headers, _ = sign_up(alice, "alice_plans"), sign_up(bob, "bob_plans")
    saved = alice.post("/api/plan/save", json={"answers": ANSWERS, "strategy": "Balance"}, headers=a_headers).json()["profile"]["id"]
    assert saved not in {p["id"] for p in bob.get("/api/profiles").json()}
    assert bob.get(f"/api/profiles/{saved}").status_code == 404


def test_saving_respects_the_profile_cap_but_still_returns_an_existing_copy(make_client):
    c = make_client(max_profiles=2)
    headers = sign_up(c, "capped_planner")
    assert c.post("/api/plan/save", json={"answers": ANSWERS, "strategy": "Balance"}, headers=headers).status_code == 201
    over = c.post("/api/plan/save", json={"answers": ANSWERS, "strategy": "Grow"}, headers=headers)
    assert over.status_code == 409 and "at most 2" in over.json()["detail"]
    again = c.post("/api/plan/save", json={"answers": ANSWERS, "strategy": "Balance"}, headers=headers)
    assert again.status_code == 200 and again.json()["created"] is False


@pytest.mark.parametrize("body", [
    {"answers": ANSWERS, "strategy": "Reckless"}, {"answers": ANSWERS}, {"strategy": "Grow"},
    {"answers": {**ANSWERS, "wealth": 0}, "strategy": "Grow"}, {"answers": ANSWERS, "strategy": "Grow", "user_id": 1},
])
def test_saving_malformed_requests_is_refused(me, body):
    client, headers = me
    assert client.post("/api/plan/save", json=body, headers=headers).status_code == 422
    assert len(client.get("/api/profiles").json()) == 1  # nothing was saved


def test_saving_answers_that_break_a_rule_says_why(me):
    client, headers = me
    four = [{"kind": "Other", "year": 1, "amount_cr": 1.0}] * 4
    r = client.post("/api/plan/save", json={"answers": with_(commitments=four), "strategy": "Grow"}, headers=headers)
    assert r.status_code == 422 and "at most" in r.json()["problems"][0]


def test_the_analysis_now_carries_the_historical_year_range_for_every_option(client):
    demo(client, "business")
    pid = client.get("/api/profiles").json()[0]["id"]
    for option in client.get(f"/api/profiles/{pid}/analysis").json()["options"]:
        yr = option["year_range"]
        assert yr["worst"] <= yr["low"] <= yr["median"] <= yr["high"] <= yr["best"]
