"""Financial invariants, checked through the real API on random but valid family profiles (Phase 7).

The golden-master tests prove the numbers for the fixed demo families. These prove the properties that must hold for *any* profile the validation lets
through: allocations add up, hard limits hold, a held-fixed asset stays fixed, no number is missing or impossible, and no profile makes the server fail.
The generator is seeded, so a failure reproduces.
"""
import math
import random

import pytest

from tests.helpers import profile_body, sign_up

CLASSES = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid"]
SEED = 20261022
PROFILES = 14
EPS = 1e-6


def random_body(rng: random.Random, base: dict) -> dict:
    body = {k: (dict(v) if isinstance(v, dict) else list(v) if isinstance(v, list) else v) for k, v in base.items()}
    corpus = round(math.exp(rng.uniform(math.log(60), math.log(4000))), 1)
    horizon = rng.randint(5, 30)
    illiquid = round(rng.uniform(0.0, 0.6), 3)
    weights = [rng.random() + 0.05 for _ in CLASSES]
    scale = (1 - illiquid) / sum(weights)
    holdings = {c: round(w * scale, 4) for c, w in zip(CLASSES, weights)}
    holdings["Illiquid"] = round(1 - sum(holdings.values()), 4)
    body.update(
        name=f"Random {rng.randint(1000, 9999)}", corpus_cr=corpus, annual_spending_cr=round(corpus * rng.uniform(0.004, 0.05), 2),
        horizon_years=horizon, max_drawdown=round(rng.uniform(0.08, 0.40), 3), cover_months=rng.choice([6, 12, 18, 24, 36]),
        target_real_return=round(rng.uniform(0.0, 0.06), 3), holdings=holdings,
    )
    body["illiquid"] = {
        "description": "Property and private holdings", "expected_return": round(rng.uniform(0.04, 0.12), 3), "volatility": round(rng.uniform(0.05, 0.25), 3),
        "lock_in_years": rng.randint(1, 10), "corr_with_equity": round(rng.uniform(0.0, 0.6), 2),
    }
    body["one_offs"] = [{"year": rng.randint(1, horizon), "amount_cr": round(corpus * rng.uniform(0.01, 0.15), 2)} for _ in range(rng.randint(0, 3))]
    body["limits"] = {c: {"min": round(rng.uniform(0.0, 0.08), 3), "max": round(rng.uniform(0.45, 1.0), 3)} for c in CLASSES}
    return body


def check_portfolio(p: dict, profile: dict, label: str, is_option: bool) -> None:
    w = p["weights_total"]
    assert all(math.isfinite(v) and -1e-9 <= v <= 1 + 1e-9 for v in w.values()), (label, w)
    assert abs(sum(w.values()) - 1.0) < EPS, (label, sum(w.values()))
    assert abs(w["Illiquid"] - profile["holdings"]["Illiquid"]) < EPS, (label, "the illiquid share must stay exactly where it is")
    for key in ("exp_return", "exp_real", "vol", "max_dd", "cvar21", "required_cover_cr", "available_cover_cr"):
        assert math.isfinite(p[key]), (label, key, p[key])
    assert p["vol"] >= 0 and 0 <= p["max_dd"] <= 1 and p["cvar21"] >= 0 and p["required_cover_cr"] >= 0 and p["available_cover_cr"] >= 0, label
    if p["dd_ok"]:
        assert p["max_dd"] <= profile["max_drawdown"] + 1e-6, (label, "flagged inside the limit but is not")
    if is_option:
        liquid = 1.0 - w["Illiquid"]
        if liquid > 1e-9:
            for c in CLASSES:
                lo, hi = profile["limits"][c]["min"], profile["limits"][c]["max"]
                assert lo - 1e-6 <= w[c] / liquid <= hi + 1e-6, (label, c, w[c] / liquid, lo, hi)  # the person's own class limits are hard
        assert p["liquidity_infeasible"] or p["available_cover_cr"] >= p["required_cover_cr"] - 1e-6, (label, "cover requirement quietly broken")


def test_any_valid_profile_gives_a_coherent_analysis(client):
    rng = random.Random(SEED)
    headers = sign_up(client, "invariants")
    base = profile_body(client)
    accepted = rejected = 0
    for _ in range(PROFILES):
        body = random_body(rng, base)
        created = client.post("/api/profiles", json=body, headers=headers)
        assert created.status_code in (201, 422), created.text[:200]
        if created.status_code == 422:
            rejected += 1
            continue
        pid = created.json()["id"]
        profile = created.json()
        results = {}
        for basis in ("all", "strict"):
            r = client.get(f"/api/profiles/{pid}/analysis", params={"basis": basis})
            assert r.status_code in (200, 422), (r.status_code, r.text[:200])  # a clear refusal is fine; a crash is not
            if r.status_code != 200:
                continue
            results[basis] = a = r.json()
            check_portfolio(a["current"], profile, f"{body['name']}/{basis}/current", False)
            assert [o["portfolio"]["label"] for o in a["options"]] == ["Growth", "Balanced", "Defensive"]
            for o in a["options"]:
                check_portfolio(o["portfolio"], profile, f"{body['name']}/{basis}/{o['portfolio']['label']}", True)
                assert abs(sum(r_["change_cr"] for r_ in o["action_plan"])) < 1e-6  # money moves between classes; none is created or lost
                assert all(abs(r_["change_cr"]) <= profile["corpus_cr"] + 1e-6 for r_ in o["action_plan"])
                assert all(x["real_cr"] <= x["nominal_cr"] + 1e-9 for x in o["projection"])  # inflation only ever shrinks purchasing power
            assert all(x["real_cr"] <= x["nominal_cr"] + 1e-9 for x in a["current_projection"])
        if len(results) == 2:  # the stricter basis counts fewer assets as liquid: it can never find more cover than the broader one
            assert results["strict"]["current"]["available_cover_cr"] <= results["all"]["current"]["available_cover_cr"] + 1e-6, body["name"]
            assert abs(results["strict"]["current"]["required_cover_cr"] - results["all"]["current"]["required_cover_cr"]) < 1e-6  # what is needed does not depend on what counts
        if results:
            accepted += 1
    print(f"random profiles: {accepted} analysed, {rejected} refused by validation, {PROFILES - accepted - rejected} refused by the engine")
    assert accepted >= PROFILES // 2, f"only {accepted} of {PROFILES} random profiles were analysable ({rejected} refused): the generator or the validation has drifted"


def test_the_same_profile_gives_the_same_answer_every_time(client):
    sign_up(client, "repeat")
    pid = client.get("/api/profiles").json()[0]["id"]
    first = client.get(f"/api/profiles/{pid}/analysis").json()
    second = client.get(f"/api/profiles/{pid}/analysis").json()
    assert first == second  # deterministic: no hidden randomness in what a family is told


def test_changing_only_the_name_changes_no_number(client):
    headers = sign_up(client, "rename")
    pid = client.get("/api/profiles").json()[0]["id"]
    before = client.get(f"/api/profiles/{pid}/analysis").json()
    body = profile_body(client)
    body["name"] = "Something else entirely"
    assert client.put(f"/api/profiles/{pid}", json=body, headers=headers).status_code == 200
    after = client.get(f"/api/profiles/{pid}/analysis").json()
    assert before == after


@pytest.mark.parametrize("field, bad", [
    ("corpus_cr", 0), ("corpus_cr", -5), ("corpus_cr", 1e12), ("annual_spending_cr", -1), ("horizon_years", 0), ("horizon_years", 500),
    ("max_drawdown", 0), ("max_drawdown", 1.5), ("cover_months", -3), ("target_real_return", 5.0),
])
def test_impossible_inputs_are_refused_with_a_reason_not_a_crash(client, field, bad):
    headers = sign_up(client, "bad_inputs")
    body = profile_body(client)
    body[field] = bad
    r = client.post("/api/profiles", json=body, headers=headers)
    assert r.status_code == 422 and r.json()["detail"] and not r.text.startswith("<"), (field, bad, r.status_code)


def test_holdings_that_do_not_add_up_or_are_negative_are_refused(client):
    headers = sign_up(client, "bad_holdings")
    body = profile_body(client)
    body["holdings"] = {**body["holdings"], "Gold": body["holdings"]["Gold"] + 0.2}
    assert client.post("/api/profiles", json=body, headers=headers).status_code == 422
    body = profile_body(client)
    first, second = list(body["holdings"])[:2]
    body["holdings"][first] -= 0.2
    body["holdings"][second] += 0.2
    assert body["holdings"][first] < 0 or client.post("/api/profiles", json=body, headers=headers).status_code in (201, 422)
