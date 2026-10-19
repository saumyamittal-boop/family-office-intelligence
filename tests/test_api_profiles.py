"""Profile CRUD, validation, cross-user isolation, identifier manipulation and request hardening."""
import copy

import pytest

from fo.personas import ILLIQUID
from tests.helpers import demo, profile_body, sign_up


def two_users(make_client):
    """Two separate browsers, each signed in as a different account that owns one profile."""
    alice, bob = make_client(), make_client()
    a_headers, b_headers = sign_up(alice, "alice_owner"), sign_up(bob, "bob_other")
    return alice, a_headers, bob, b_headers


# ---- CRUD ----------------------------------------------------------------------------------------------------------
def test_a_new_account_starts_with_one_profile(client):
    sign_up(client, "fresh_account")
    listing = client.get("/api/profiles").json()
    assert len(listing) == 1 and listing[0]["corpus_cr"] > 0


def test_create_read_update_delete_round_trip(client):
    headers = sign_up(client, "crud_user")
    body = profile_body(client)
    body["name"] = "Second family"
    body["corpus_cr"] = 500.0
    created = client.post("/api/profiles", json=body, headers=headers)
    assert created.status_code == 201
    pid = created.json()["id"]

    fetched = client.get(f"/api/profiles/{pid}").json()
    assert fetched["name"] == "Second family" and fetched["corpus_cr"] == 500.0
    assert fetched["holdings"] == pytest.approx(body["holdings"], abs=1e-12)

    body["annual_spending_cr"] = 7.5
    assert client.put(f"/api/profiles/{pid}", json=body, headers=headers).json()["annual_spending_cr"] == 7.5
    assert client.get(f"/api/profiles/{pid}").json()["annual_spending_cr"] == 7.5

    assert client.delete(f"/api/profiles/{pid}", headers=headers).status_code == 204
    assert client.get(f"/api/profiles/{pid}").status_code == 404


def test_the_last_profile_cannot_be_deleted(client):
    headers = sign_up(client, "only_one")
    pid = client.get("/api/profiles").json()[0]["id"]
    r = client.delete(f"/api/profiles/{pid}", headers=headers)
    assert r.status_code == 409 and client.get(f"/api/profiles/{pid}").status_code == 200


def test_profile_count_is_capped_per_account(make_client):
    c = make_client(max_profiles=2)
    headers = sign_up(c, "capped_user")
    body = profile_body(c)
    assert c.post("/api/profiles", json=body, headers=headers).status_code == 201
    r = c.post("/api/profiles", json=body, headers=headers)
    assert r.status_code == 409 and "at most 2" in r.json()["detail"]


# ---- Validation: same rules as the Streamlit form ---------------------------------------------------------------------------------
def post_problem(client, headers, mutate):
    body = copy.deepcopy(profile_body(client))
    mutate(body)
    r = client.post("/api/profiles", json=body, headers=headers)
    assert r.status_code == 422, r.text
    return r.json()


def test_holdings_must_add_up_to_100_percent(client):
    headers = sign_up(client, "val_holdings")
    out = post_problem(client, headers, lambda b: b["holdings"].update({"Debt": b["holdings"]["Debt"] + 0.2}))
    assert any("need to add up to 100%" in p for p in out["problems"])


def test_illiquid_share_is_capped_at_95_percent(client):
    headers = sign_up(client, "val_illiquid")

    def mutate(b):
        b["holdings"] = {c: 0.0 for c in b["holdings"]}
        b["holdings"][ILLIQUID] = 0.96
        b["holdings"]["Cash & liquid"] = 0.04

    assert any("at most 95%" in p for p in post_problem(client, headers, mutate)["problems"])


def test_class_limits_that_cannot_add_up_are_refused(client):
    headers = sign_up(client, "val_limits")
    out = post_problem(client, headers, lambda b: [b["limits"][c].update({"max": 0.1}) for c in b["limits"]])
    assert any("can't add up to 100%" in p for p in out["problems"])


def test_a_minimum_above_its_maximum_is_refused(client):
    headers = sign_up(client, "val_minmax")
    out = post_problem(client, headers, lambda b: b["limits"]["Debt"].update({"min": 0.9, "max": 0.2}))
    assert any(p.startswith("Debt:") for p in out["problems"])


def test_one_offs_must_fit_the_horizon_and_number_at_most_three(client):
    headers = sign_up(client, "val_oneoffs")
    out = post_problem(client, headers, lambda b: b.update(horizon_years=5, one_offs=[{"year": 9, "amount_cr": 1.0}]))
    assert any("outside the 5-year horizon" in p for p in out["problems"])
    out = post_problem(client, headers, lambda b: b.update(one_offs=[{"year": 1, "amount_cr": 1.0}] * 4))
    assert any("at most three" in p for p in out["problems"])


def test_a_blank_name_is_refused(client):
    headers = sign_up(client, "val_name")
    assert any("name" in p for p in post_problem(client, headers, lambda b: b.update(name="   "))["problems"])


@pytest.mark.parametrize("field, value", [
    ("corpus_cr", 0), ("corpus_cr", -5), ("corpus_cr", 10**9), ("annual_spending_cr", -1),
    ("horizon_years", 0), ("horizon_years", 61), ("max_drawdown", 0), ("max_drawdown", 0.95),
    ("cover_months", 0), ("cover_months", 500), ("target_real_return", 0.9), ("corpus_cr", "a lot"),
    ("horizon_years", 12.5), ("name", ""), ("name", "x" * 61),
])
def test_out_of_range_and_wrong_type_values_are_rejected(client, field, value):
    headers = sign_up(client, f"range_{abs(hash((field, str(value)))) % 10**8}")
    body = profile_body(client)
    body[field] = value
    assert client.post("/api/profiles", json=body, headers=headers).status_code == 422


def test_unknown_classes_missing_fields_and_extra_fields_are_rejected(client):
    headers = sign_up(client, "shape_user")
    body = profile_body(client)
    for broken in (
        {**body, "holdings": {**body["holdings"], "Crypto": 0.0}},
        {**body, "holdings": {k: v for k, v in body["holdings"].items() if k != "Gold"}},
        {**body, "limits": {k: v for k, v in body["limits"].items() if k != "Debt"}},
        {**body, "user_id": 1}, {**body, "id": 99}, {k: v for k, v in body.items() if k != "illiquid"},
    ):
        assert client.post("/api/profiles", json=broken, headers=headers).status_code == 422


def test_nan_and_infinity_are_rejected(client):
    headers = sign_up(client, "nan_user")
    for token in ("NaN", "Infinity", "-Infinity"):
        raw = '{"name":"x","corpus_cr":%s}' % token
        r = client.post("/api/profiles", content=raw, headers={**headers, "Content-Type": "application/json"})
        assert r.status_code == 422


def test_error_responses_never_echo_what_was_submitted(client):
    headers = sign_up(client, "echo_user")
    body = profile_body(client)
    body["name"] = "SUPER-SECRET-MARKER-" + "x" * 60
    body["corpus_cr"] = "SECRET-NOT-A-NUMBER"
    r = client.post("/api/profiles", json=body, headers=headers)
    assert r.status_code == 422 and "SECRET" not in r.text


# ---- Isolation and identifier manipulation ----------------------------------------------------------------------------------------
def test_one_account_cannot_read_change_delete_or_analyse_anothers_profile(make_client):
    alice, a_headers, bob, b_headers = two_users(make_client)
    alice_pid = alice.get("/api/profiles").json()[0]["id"]
    before = alice.get(f"/api/profiles/{alice_pid}").json()

    attack = profile_body(bob)
    attack["name"] = "Taken over by Bob"
    attack["corpus_cr"] = 1.0
    missing = bob.get("/api/profiles/999999")
    for response in (
        bob.get(f"/api/profiles/{alice_pid}"),
        bob.put(f"/api/profiles/{alice_pid}", json=attack, headers=b_headers),
        bob.delete(f"/api/profiles/{alice_pid}", headers=b_headers),
        bob.get(f"/api/profiles/{alice_pid}/analysis"),
    ):
        assert response.status_code == 404
        assert response.json() == missing.json()  # indistinguishable from a profile that does not exist

    assert alice.get(f"/api/profiles/{alice_pid}").json() == before
    assert [p["id"] for p in bob.get("/api/profiles").json()] != [alice_pid]


def test_listing_shows_only_your_own_profiles(make_client):
    alice, _, bob, _ = two_users(make_client)
    ids = {p["id"] for p in alice.get("/api/profiles").json()}, {p["id"] for p in bob.get("/api/profiles").json()}
    assert ids[0].isdisjoint(ids[1]) and len(ids[0]) == len(ids[1]) == 1


def test_a_visitor_with_a_demo_copy_cannot_reach_the_shared_demo_rows_or_real_users(client, make_client):
    real = make_client()
    sign_up(real, "real_owner")
    real_pid = real.get("/api/profiles").json()[0]["id"]
    demo(client, "legacy")
    for pid in range(1, real_pid + 3):
        if pid != client.get("/api/profiles").json()[0]["id"]:
            assert client.get(f"/api/profiles/{pid}").status_code == 404


@pytest.mark.parametrize("raw", ["0", "-1", "abc", "1.5", "1e3", "2147483648", "99999999999999999999", "1%20OR%201=1", "%27"])
def test_manipulated_identifiers_are_rejected_before_any_lookup(client, raw):
    sign_up(client, "idor_probe")
    for method in ("get", "delete"):
        r = getattr(client, method)(f"/api/profiles/{raw}", **({"headers": {"X-CSRF-Token": "x"}} if method == "delete" else {}))
        assert r.status_code in {403, 404, 422}


def test_the_user_id_comes_from_the_session_never_from_the_client(make_client):
    alice, a_headers, bob, b_headers = two_users(make_client)
    alice_pid = alice.get("/api/profiles").json()[0]["id"]
    body = profile_body(bob)
    spoofed = bob.post(f"/api/profiles?user_id=1&owner={alice_pid}", json=body, headers={**b_headers, "X-User-Id": "1"})
    assert spoofed.status_code == 201
    new_id = spoofed.json()["id"]
    assert new_id not in {p["id"] for p in alice.get("/api/profiles").json()}
    assert alice.get(f"/api/profiles/{new_id}").status_code == 404


# ---- Request hardening ----------------------------------------------------------------------------------------------------------
def test_oversized_bodies_are_refused(make_client):
    c = make_client(max_body_bytes=2000)
    headers = sign_up(c, "big_body")
    body = profile_body(c)
    body["deciding_constraint"] = "x" * 200
    body["name"] = "n"
    r = c.post("/api/profiles", content=("[" + "1," * 5000 + "1]"), headers={**headers, "Content-Type": "application/json"})
    assert r.status_code == 413


def test_only_json_is_accepted_for_writes(client):
    headers = sign_up(client, "json_only")
    r = client.post("/api/profiles", content="name=x", headers={**headers, "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    r = client.post("/api/profiles", content="plain", headers={**headers, "Content-Type": "text/plain"})
    assert r.status_code == 415


def test_requests_from_other_websites_are_refused_but_the_app_itself_is_fine(client):
    headers = sign_up(client, "origin_check")
    body = profile_body(client)
    assert client.post("/api/profiles", json=body, headers={**headers, "Origin": "https://evil.example"}).status_code == 403
    assert client.post("/api/profiles", json=body, headers={**headers, "Origin": "http://localhost:5173"}).status_code == 201


def test_cors_allows_the_dev_server_with_cookies_and_nobody_else(client):
    ok = client.options("/api/profiles", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
                                                   "Access-Control-Request-Headers": "x-csrf-token,content-type"})
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert ok.headers["access-control-allow-credentials"] == "true"
    bad = client.options("/api/profiles", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in bad.headers


def test_security_headers_and_no_caching_on_api_responses(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"


def test_the_docs_and_schema_pages_can_be_switched_off(make_client):
    c = make_client(docs=False)
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


def test_unexpected_failures_return_a_generic_message_not_internals(make_client):
    from fastapi.testclient import TestClient

    c = make_client()
    headers = sign_up(c, "boom_user")
    pid = c.get("/api/profiles").json()[0]["id"]

    def explode(*_a, **_k):
        raise RuntimeError("internal detail: C:\\secret\\path and SELECT * FROM users")

    c.app.state.analysis.analyse = explode
    quiet = TestClient(c.app, raise_server_exceptions=False, cookies=c.cookies)
    r = quiet.get(f"/api/profiles/{pid}/analysis")
    assert r.status_code == 500
    assert r.json()["detail"] == "Something went wrong on our side."
    assert "secret" not in r.text and "SELECT" not in r.text
