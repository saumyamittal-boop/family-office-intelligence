"""The analyst endpoints: the history curves and the stress scenarios (Phase 4).

The numbers are checked against the engine itself, called directly in this file with its own hand-built inputs, and
against the analysis endpoint that the golden master already covers.
"""
import math
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import history
from api import schemas as s
from api.config import Settings
from api.main import create_app
from fo import accounts, engine
from fo.data import ASSET_CLASSES
from tests.helpers import profile_body, sign_up

LARGE, MID, DEBT, GOLD, CASH = ASSET_CLASSES
DIALS = dict(equity_shock=-0.30, debt_shock=-0.04, gold_shock=0.10, illiquid_markdown=-0.15, one_off_expense=0.06, return_drag=0.01)


@pytest.fixture(scope="module")
def world(tmp_path_factory, sample_returns):
    """One app, one signed-in family and the engine's own answer for it, shared by the read-only tests below."""
    patch = pytest.MonkeyPatch()
    patch.setattr(accounts, "DB_PATH", tmp_path_factory.mktemp("analyst") / "analyst.db")
    patch.setattr("api.main.load_returns", lambda: (sample_returns, "sample"))
    app = create_app(Settings())
    client = TestClient(app)
    client.__enter__()
    headers = sign_up(client, "analyst_owner")
    user_id = client.get("/api/auth/me").json()["user"]["id"]
    profile_id = client.get("/api/profiles").json()[0]["id"]
    profile = accounts.get_profile(user_id, profile_id)
    inputs = engine.estimate_inputs(sample_returns)
    current = engine.analyse_current(profile, sample_returns, "all", inputs)
    options = engine.recommend(profile, sample_returns, "all", inputs)
    yield SimpleNamespace(
        client=client, anonymous=TestClient(app), headers=headers, pid=profile_id, profile=profile, current=current, options=options,
        portfolios=[current] + options,
    )
    client.__exit__(None, None, None)
    patch.undo()


def history_of(world, basis="all") -> dict:
    r = world.client.get(f"/api/profiles/{world.pid}/history", params={"basis": basis})
    assert r.status_code == 200, r.text
    return r.json()


def scenario(world, **body) -> dict:
    r = world.client.post(f"/api/profiles/{world.pid}/scenarios", json=body, headers=world.headers)
    assert r.status_code == 200, r.text
    return r.json()


def analysis_of(world) -> dict:
    return world.client.get(f"/api/profiles/{world.pid}/analysis").json()


# ---- History: who may see it --------------------------------------------------------------------------------------------
def test_history_needs_a_sign_in(world):
    assert world.anonymous.get("/api/profiles/1/history").status_code == 401


def test_someone_elses_history_is_not_found(make_client):
    owner = make_client()
    sign_up(owner, "history_owner")
    pid = owner.get("/api/profiles").json()[0]["id"]
    stranger = make_client()
    sign_up(stranger, "history_stranger")
    assert stranger.get(f"/api/profiles/{pid}/history").status_code == 404
    assert stranger.get("/api/profiles/999999/history").status_code == 404


def test_history_refuses_an_unknown_cover_basis(world):
    assert world.client.get(f"/api/profiles/{world.pid}/history", params={"basis": "loose"}).status_code == 422


# ---- History: what it says ----------------------------------------------------------------------------------------------
def test_history_covers_the_current_mix_and_the_three_options_over_the_same_dates(world):
    body = history_of(world)
    assert [p["label"] for p in body["portfolios"]] == [pf.label for pf in world.portfolios]
    assert body["step_days"] == history.STEP_DAYS and body["drawdown_limit"] == world.profile.max_drawdown
    assert body["data_source"] == "sample" and "illiquid" in body["note"].lower()
    for p in body["portfolios"]:
        assert len(p["value"]) == len(p["drawdown"]) == len(body["dates"])
    dates = pd.to_datetime(body["dates"])
    assert dates.is_monotonic_increasing and dates.is_unique


def test_the_curves_are_the_engines_replay_thinned_to_weekly_points(world):
    body = history_of(world)
    daily = world.current.replay_returns
    n = len(daily)
    ends = list(range(history.STEP_DAYS, n + 1, history.STEP_DAYS))
    ends += [] if ends[-1] == n else [n]
    assert len(body["dates"]) == len(ends) + 1
    assert body["dates"][-1] == daily.index[-1].date().isoformat()
    assert pd.Timestamp(body["dates"][0]) < daily.index[0] and pd.Timestamp(body["dates"][1]) <= daily.index[history.STEP_DAYS - 1]
    for api_pf, pf in zip(body["portfolios"], world.portfolios):
        full = 100.0 * np.cumprod(1.0 + pf.replay_returns.to_numpy())
        assert api_pf["value"][0] == 100.0
        assert api_pf["value"][1:] == pytest.approx([full[e - 1] for e in ends], abs=6e-5)


def test_thinning_never_hides_the_worst_fall(world):
    body = history_of(world)
    for api_pf, pf in zip(body["portfolios"], world.portfolios):
        assert api_pf["max_drawdown"] == pf.max_dd  # the engine's number, on every day
        assert -min(api_pf["drawdown"]) == pytest.approx(pf.max_dd, abs=2e-6)  # and the picture shows the same trough
        assert max(api_pf["drawdown"]) <= 0.0


def test_history_agrees_with_the_analysis_numbers(world):
    body, analysis = history_of(world), analysis_of(world)
    shown = [analysis["current"]] + [o["portfolio"] for o in analysis["options"]]
    for api_pf, pf in zip(body["portfolios"], shown):
        assert api_pf["label"] == pf["label"]
        assert api_pf["max_drawdown"] == pf["max_dd"] and api_pf["cvar21"] == pf["cvar21"]


def test_calendar_year_returns_compound_to_the_whole_period(world):
    body = history_of(world)
    for api_pf in body["portfolios"]:
        years = api_pf["annual"]
        assert [y["year"] for y in years] == list(range(2016, 2026))
        assert not any(y["partial"] for y in years)
        assert sum(y["trading_days"] for y in years) == len(world.current.replay_returns)
        compounded = math.prod(1 + y["portfolio_return"] for y in years)
        assert compounded == pytest.approx(api_pf["value"][-1] / 100.0, rel=1e-3)


def test_a_part_year_is_marked_partial():
    index = pd.bdate_range("2024-10-01", "2025-03-31")
    rows = history.annual(pd.Series(0.0004, index=index))
    assert [(r.year, r.partial) for r in rows] == [(2024, True), (2025, True)]


def test_the_thinned_curve_keeps_a_dip_that_recovers_inside_one_step():
    index = pd.bdate_range("2024-01-01", periods=7)
    returns = pd.Series([0.0, -0.5, 0.6, 0.0, 0.0, 0.1, 0.0], index=index)  # falls 50% on day 2, back by day 3
    dates, value, drawdown = history.curves(returns)
    assert len(dates) == len(value) == len(drawdown) == 3  # base day, first five days, the last two
    assert value[0] == 100.0 and value[1] == pytest.approx(80.0) and value[2] == pytest.approx(88.0)
    assert min(drawdown) == pytest.approx(-0.5)  # the dip survives although both ends of the step are near 80
    assert dates[0] == "2023-12-29" and dates[-1] == "2024-01-09"


def test_the_base_day_makes_a_first_day_loss_count():
    index = pd.bdate_range("2024-01-01", periods=5)
    _, value, drawdown = history.curves(pd.Series([-0.10, 0.0, 0.0, 0.0, 0.0], index=index))
    assert drawdown[1] == pytest.approx(-0.10) and value[1] == pytest.approx(90.0)
    assert -drawdown[1] == pytest.approx(engine.max_drawdown(pd.Series([-0.10, 0.0, 0.0, 0.0, 0.0])))


def test_history_reuses_the_analysis_instead_of_running_the_optimiser_again(world, monkeypatch):
    analysis_of(world)  # make sure it is cached
    calls = []
    monkeypatch.setattr(engine, "recommend", lambda *a, **k: calls.append(1))
    history_of(world)
    history_of(world, basis="all")
    scenario(world, preset="Market crash")
    scenario(world, custom=DIALS)
    assert calls == []


def test_a_profile_the_engine_cannot_analyse_gives_a_clear_message(make_client):
    client = make_client()
    headers = sign_up(client, "no_spending")
    pid = client.get("/api/profiles").json()[0]["id"]
    body = profile_body(client, pid)
    body.update(annual_spending_cr=0.0, one_offs=[])
    assert client.put(f"/api/profiles/{pid}", json=body, headers=headers).status_code == 200
    for r in (
        client.get(f"/api/profiles/{pid}/history"),
        client.post(f"/api/profiles/{pid}/scenarios", json={"preset": "Market crash"}, headers=headers),
    ):
        assert r.status_code == 422 and "can't be analysed" in r.json()["detail"]


# ---- Scenarios: who may run them ----------------------------------------------------------------------------------------
def test_scenarios_need_a_sign_in_and_the_csrf_token(world):
    assert world.anonymous.post("/api/profiles/1/scenarios", json={"preset": "Market crash"}).status_code == 401
    r = world.client.post(f"/api/profiles/{world.pid}/scenarios", json={"preset": "Market crash"})
    assert r.status_code == 403


def test_someone_elses_profile_cannot_be_stressed(make_client):
    owner = make_client()
    sign_up(owner, "scenario_owner")
    pid = owner.get("/api/profiles").json()[0]["id"]
    stranger = make_client()
    headers = sign_up(stranger, "scenario_stranger")
    r = stranger.post(f"/api/profiles/{pid}/scenarios", json={"preset": "Market crash"}, headers=headers)
    assert r.status_code == 404


# ---- Scenarios: the built-in ones ---------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(engine.SCENARIOS))
def test_each_builtin_scenario_matches_the_analysis_and_the_engine(world, name):
    out = scenario(world, preset=name)
    assert out["name"] == name and out["is_custom"] is False and out["description"]
    rows = {r["option"]: r for r in out["rows"]}
    assert list(rows) == [pf.label for pf in world.portfolios]  # the current mix first
    analysis = analysis_of(world)
    for option in analysis["options"]:  # the same numbers the analysis endpoint (and the golden master) holds
        want = next(x for x in option["scenarios"] if x["scenario"] == name)
        got = rows[option["portfolio"]["label"]]
        assert got["value_change"] == pytest.approx(want["value_change"], abs=1e-12)
        assert got["value_change_cr"] == pytest.approx(want["value_change_cr"], abs=1e-9)
        assert got["cover_ratio_after"] == pytest.approx(want["cover_ratio"], abs=1e-12)
        assert got["real_corpus_multiple"] == pytest.approx(want["real_corpus_multiple"], abs=1e-12)
        assert got["within_drawdown_limit"] == want["within_drawdown_limit"] and got["cover_held"] == want["cover_held"]
    direct = engine.scenario_row(world.profile, world.current, name, engine.SCENARIOS[name])  # and for the current mix
    assert rows["Current"]["value_change"] == pytest.approx(direct["Portfolio value change"], abs=1e-12)
    assert rows["Current"]["cover_ratio_after"] == pytest.approx(direct["Liquidity cover (x required)"], abs=1e-12)


def test_the_analysis_comparison_is_the_equities_fall_scenario(world):
    analysis = analysis_of(world)
    out = scenario(world, preset=analysis["comparison_scenario"])
    assert [r["option"] for r in out["rows"]] == [r["option"] for r in analysis["comparison"]]
    for got, want in zip(out["rows"], analysis["comparison"]):
        assert got == want
    assert [i["body"] for i in out["insights"]] == [i["body"] for i in analysis["comparison_insights"]]


def test_the_applied_shape_describes_exactly_what_was_run(world):
    out = scenario(world, preset="Market crash")
    assert out["applied"]["shocks"] == engine.SCENARIOS["Market crash"]["shocks"]
    assert out["applied"]["illiquid"] == -0.20 and out["applied"]["extra_outflow"] == 0.0 and out["applied"]["return_drag"] == 0.0


def test_the_cover_basis_is_respected_and_echoed(world):
    loose, strict = scenario(world, preset="Market crash", basis="all"), scenario(world, preset="Market crash", basis="strict")
    assert loose["basis"] == "all" and strict["basis"] == "strict"
    # Counting fewer assets as cover can only lower the cover that remains after the shock.
    assert all(s_["cover_ratio_after"] <= l_["cover_ratio_after"] + 1e-12 for s_, l_ in zip(strict["rows"], loose["rows"]))


# ---- Scenarios: build your own ------------------------------------------------------------------------------------------
def custom_by_hand() -> dict:
    """The six dials as the engine wants them, written out here on purpose rather than imported from the API."""
    return {
        "shocks": {LARGE: -0.30, MID: -0.375, DEBT: -0.04, GOLD: 0.10, CASH: 0.0},
        "illiquid": -0.15, "extra_outflow": 0.06, "return_drag": 0.01,
    }


def test_a_custom_scenario_matches_the_engine_and_hand_arithmetic(world):
    out = scenario(world, custom=DIALS)
    assert out["name"] == "Your scenario" and out["is_custom"] is True
    first = out["rows"][0]
    assert first["option"] == "Current"
    weights = analysis_of(world)["current"]["weights_total"]  # share of the whole corpus, illiquid included
    by_hand = (weights[LARGE] * -0.30 + weights[MID] * -0.375 + weights[DEBT] * -0.04 + weights[GOLD] * 0.10
               + weights["Illiquid"] * -0.15) - 0.06
    assert first["value_change"] == pytest.approx(by_hand, abs=1e-12)
    assert first["value_change_cr"] == pytest.approx(by_hand * world.profile.corpus_cr, abs=1e-9)
    for row, pf in zip(out["rows"], world.portfolios):
        want = engine.scenario_row(world.profile, pf, "x", custom_by_hand())
        assert row["value_change"] == pytest.approx(want["Portfolio value change"], abs=1e-12)
        assert row["cover_ratio_after"] == pytest.approx(want["Liquidity cover (x required)"], abs=1e-12)
        assert row["real_corpus_multiple"] == pytest.approx(want["Real corpus at horizon (x today)"], abs=1e-12)
        assert row["within_drawdown_limit"] == want["Within drawdown limit"] and row["cover_held"] == want["Cover held"]


def test_mid_caps_move_a_quarter_more_than_large_caps(world):
    applied = scenario(world, custom=DIALS)["applied"]
    assert applied["shocks"][MID] == pytest.approx(-0.375) and applied["shocks"][LARGE] == -0.30
    assert applied["shocks"][CASH] == 0.0 and applied["extra_outflow"] == 0.06 and applied["return_drag"] == 0.01
    assert scenario(world, custom={"equity_shock": 0.2})["applied"]["shocks"][MID] == pytest.approx(0.25)


def test_dials_at_zero_change_nothing_and_match_the_baseline_row(world):
    zero = dict(equity_shock=0.0, debt_shock=0.0, gold_shock=0.0, illiquid_markdown=0.0, one_off_expense=0.0, return_drag=0.0)
    out = scenario(world, custom=zero)
    rows = {r["option"]: r for r in out["rows"]}
    for option in analysis_of(world)["options"]:
        baseline = option["scenarios"][0]
        assert baseline["scenario"].startswith("Baseline")
        got = rows[option["portfolio"]["label"]]
        assert got["value_change"] == 0.0
        assert got["real_corpus_multiple"] == pytest.approx(baseline["real_corpus_multiple"], abs=1e-12)
        assert got["cover_ratio_after"] == pytest.approx(baseline["cover_ratio"], abs=1e-12)


def test_leaving_the_dials_out_uses_the_stated_defaults(world):
    out = scenario(world, custom={})
    assert out["applied"]["shocks"][LARGE] == -0.25 and out["applied"]["illiquid"] == -0.10 and out["applied"]["extra_outflow"] == 0.05
    assert out == scenario(world, custom={"equity_shock": -0.25, "debt_shock": -0.03, "gold_shock": 0.05,
                                          "illiquid_markdown": -0.10, "one_off_expense": 0.05, "return_drag": 0.0})


def test_a_harsher_scenario_never_hurts_less(world):
    mild = scenario(world, custom={"equity_shock": -0.10})["rows"][0]["value_change"]
    harsh = scenario(world, custom={"equity_shock": -0.50})["rows"][0]["value_change"]
    assert harsh < mild < 0.0


# ---- Scenarios: bad requests --------------------------------------------------------------------------------------------
def refused(world, body=None, content=None):
    kwargs = {"content": content, "headers": {**world.headers, "Content-Type": "application/json"}} if content else {"json": body, "headers": world.headers}
    r = world.client.post(f"/api/profiles/{world.pid}/scenarios", **kwargs)
    assert r.status_code == 422, r.text
    return r.json()


@pytest.mark.parametrize(
    "body",
    [
        {}, {"basis": "all"}, {"preset": "Market crash", "custom": {}}, {"preset": None, "custom": None},
        {"preset": "A scenario that does not exist"}, {"preset": ""}, {"preset": "x" * 61}, {"preset": 7},
        {"custom": {"equity_shock": -0.61}}, {"custom": {"equity_shock": 0.21}}, {"custom": {"debt_shock": -0.21}},
        {"custom": {"gold_shock": 0.41}}, {"custom": {"illiquid_markdown": -0.51}}, {"custom": {"one_off_expense": -0.01}},
        {"custom": {"one_off_expense": 0.41}}, {"custom": {"return_drag": -0.01}}, {"custom": {"return_drag": 0.09}},
        {"custom": {"equity_shock": "lots"}}, {"custom": {"equity_shock": None}}, {"custom": {"mid_cap_shock": -0.5}},
        {"custom": []}, {"basis": "loose", "preset": "Market crash"}, {"preset": "Market crash", "profile_id": 3},
    ],
)
def test_a_malformed_scenario_request_is_refused(world, body):
    refused(world, body)


def test_not_a_number_is_refused(world):
    refused(world, content='{"custom": {"equity_shock": NaN}}')
    refused(world, content='{"custom": {"equity_shock": Infinity}}')


def test_a_refusal_does_not_echo_the_input(world):
    body = refused(world, {"preset": "<script>alert(1)</script>"})
    assert "<script>" not in str(body)
    assert "Choose one of" in body["detail"]


# ---- What the app tells the screens -------------------------------------------------------------------------------------
def test_meta_describes_the_builtin_scenarios_from_the_engine(client):
    presets = client.get("/api/meta").json()["scenario_presets"]
    assert [p["name"] for p in presets] == list(engine.SCENARIOS)
    for p in presets:
        sc = engine.SCENARIOS[p["name"]]
        assert p["shocks"] == sc["shocks"] and p["illiquid"] == sc["illiquid"]
        assert p["extra_outflow"] == sc["extra_outflow"] and p["return_drag"] == sc["return_drag"] and p["description"]


def test_meta_gives_the_dial_limits_that_the_request_enforces(world):
    ranges = world.client.get("/api/meta").json()["custom_scenario_ranges"]
    assert set(ranges) == set(s.CustomScenario.model_fields)
    for key, r in ranges.items():
        assert r["min"] <= r["default"] <= r["max"]
        assert scenario(world, custom={key: r["min"]})["rows"]  # both ends are accepted ...
        assert scenario(world, custom={key: r["max"]})["rows"]
        refused(world, {"custom": {key: r["max"] + 0.01}})  # ... and just beyond them is not
        refused(world, {"custom": {key: r["min"] - 0.01}})
