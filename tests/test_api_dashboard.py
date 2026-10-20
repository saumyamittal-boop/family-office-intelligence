"""The personalised dashboard: exactly four modules, in order, saved per account (decision D8)."""
import json
import sqlite3

import pytest

from api import dashboard, db
from api.dashboard import DEFAULT_MODULES
from fo import accounts
from tests.helpers import demo, sign_up

SEVEN = [
    "allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios",
    "net_worth_projection", "historical_performance", "recommendation_rationale",
]
PICK = ["historical_performance", "allocation_actions", "net_worth_projection", "recommendation_rationale"]


@pytest.fixture()
def me(client):
    return client, sign_up(client, "dash_owner")


# ---- Sign-in and request checks ---------------------------------------------------------------------------------------
def test_every_dashboard_request_needs_a_sign_in(client):
    assert client.get("/api/dashboard").status_code == 401
    assert client.put("/api/dashboard", json={"modules": PICK}).status_code == 401
    assert client.delete("/api/dashboard").status_code == 401


def test_changing_the_dashboard_needs_the_csrf_token(me):
    client, _ = me
    assert client.put("/api/dashboard", json={"modules": PICK}).status_code == 403
    assert client.delete("/api/dashboard").status_code == 403
    assert client.get("/api/dashboard").json()["is_default"] is True  # nothing was saved


def test_a_cross_origin_change_is_refused(me):
    client, headers = me
    r = client.put("/api/dashboard", json={"modules": PICK}, headers={**headers, "Origin": "https://evil.example"})
    assert r.status_code == 403


# ---- The default ------------------------------------------------------------------------------------------------------
def test_a_new_account_gets_the_default_four(me):
    client, _ = me
    body = client.get("/api/dashboard").json()
    assert body["modules"] == list(DEFAULT_MODULES) == ["allocation_actions", "liquidity_commitments", "risk_exposure", "stress_scenarios"]
    assert body["is_default"] is True and body["updated"] is None
    assert body["default_modules"] == body["modules"]


def test_the_catalog_lists_eight_modules_and_every_one_is_ready(me):
    client, _ = me
    catalog = client.get("/api/dashboard").json()["catalog"]
    assert [m["id"] for m in catalog] == SEVEN + ["holdings_consolidation"]
    assert all(m["available"] for m in catalog)


# ---- Saving, ordering, restoring --------------------------------------------------------------------------------------
def test_a_choice_is_saved_in_the_order_given(me):
    client, headers = me
    r = client.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    assert r.status_code == 200
    assert r.json()["modules"] == PICK and r.json()["is_default"] is False and r.json()["updated"]
    assert client.get("/api/dashboard").json()["modules"] == PICK


def test_reordering_the_same_four_is_a_change(me):
    client, headers = me
    client.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    flipped = list(reversed(PICK))
    assert client.put("/api/dashboard", json={"modules": flipped}, headers=headers).json()["modules"] == flipped
    assert client.get("/api/dashboard").json()["modules"] == flipped


def test_saving_twice_keeps_one_row(me, db_path):
    client, headers = me
    client.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    client.put("/api/dashboard", json={"modules": SEVEN[:4]}, headers=headers)
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM dashboard_preferences").fetchone()[0] == 1


def test_the_choice_is_still_there_after_signing_out_and_in_again(make_client):
    first = make_client()
    headers = sign_up(first, "returning_dash")
    first.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    first.post("/api/auth/logout", headers=headers)
    assert first.get("/api/dashboard").status_code == 401

    second = make_client()  # a different browser and a restarted app, same database
    assert second.post("/api/auth/login", json={"username": "returning_dash", "password": "correct horse battery"}).status_code == 200
    assert second.get("/api/dashboard").json()["modules"] == PICK


def test_restoring_the_default_removes_the_saved_choice(me, db_path):
    client, headers = me
    client.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    r = client.delete("/api/dashboard", headers=headers)
    assert r.status_code == 200 and r.json()["modules"] == list(DEFAULT_MODULES) and r.json()["is_default"] is True
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM dashboard_preferences").fetchone()[0] == 0
    assert client.delete("/api/dashboard", headers=headers).status_code == 200  # restoring twice is harmless


def test_a_demo_family_can_customise_its_private_copy(client):
    headers = demo(client, "legacy")
    assert client.put("/api/dashboard", json={"modules": PICK}, headers=headers).status_code == 200
    assert client.get("/api/dashboard").json()["modules"] == PICK


# ---- Validation -------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "modules",
    [
        [], PICK[:3], PICK + ["risk_exposure"], [PICK[0]] * 4, [PICK[0], PICK[0], PICK[1], PICK[2]],
        PICK[:3] + ["not_a_module"], PICK[:3] + [None], PICK[:3] + [7], "allocation_actions", None,
    ],
)
def test_anything_but_four_different_known_modules_is_refused(me, modules):
    client, headers = me
    r = client.put("/api/dashboard", json={"modules": modules}, headers=headers)
    assert r.status_code == 422 and r.json()["detail"]
    assert client.get("/api/dashboard").json()["is_default"] is True  # a refused request saves nothing


def test_holdings_consolidation_can_be_chosen_like_any_other_module(me):
    client, headers = me
    chosen = PICK[:3] + ["holdings_consolidation"]
    assert client.put("/api/dashboard", json={"modules": chosen}, headers=headers).json()["modules"] == chosen
    assert client.get("/api/dashboard").json()["modules"] == chosen


def test_a_module_that_is_not_ready_is_refused_with_a_reason(me, monkeypatch):
    client, headers = me
    monkeypatch.setattr(dashboard, "AVAILABLE", tuple(m for m in dashboard.MODULE_IDS if m != "net_worth_projection"))
    r = client.put("/api/dashboard", json={"modules": PICK}, headers=headers)  # PICK contains net_worth_projection
    assert r.status_code == 422 and "later phase" in r.json()["problems"][0]
    assert [m["available"] for m in client.get("/api/dashboard").json()["catalog"] if m["id"] == "net_worth_projection"] == [False]


def test_a_request_cannot_name_another_account_or_extra_fields(me):
    client, headers = me
    for extra in ({"user_id": 1}, {"owner": "someone"}, {"is_default": False}):
        assert client.put("/api/dashboard", json={"modules": PICK, **extra}, headers=headers).status_code == 422


def test_the_body_must_be_json(me):
    client, headers = me
    r = client.put("/api/dashboard", content="modules=a", headers={**headers, "Content-Type": "text/plain"})
    assert r.status_code == 415


def test_an_error_never_echoes_what_was_sent(me):
    client, headers = me
    r = client.put("/api/dashboard", json={"modules": PICK[:3] + ["<script>alert(1)</script>"]}, headers=headers)
    assert r.status_code == 422 and "<script>" not in r.text


# ---- Isolation --------------------------------------------------------------------------------------------------------
def test_one_persons_choice_never_reaches_another(make_client):
    alice, a_headers = make_client(), None
    a_headers = sign_up(alice, "alice_dash")
    bob = make_client()
    b_headers = sign_up(bob, "bob_dash")
    alice.put("/api/dashboard", json={"modules": PICK}, headers=a_headers)
    assert bob.get("/api/dashboard").json()["modules"] == list(DEFAULT_MODULES)
    bob.put("/api/dashboard", json={"modules": SEVEN[:4]}, headers=b_headers)
    assert alice.get("/api/dashboard").json()["modules"] == PICK
    bob.delete("/api/dashboard", headers=b_headers)  # bob's reset leaves alice's choice alone
    assert alice.get("/api/dashboard").json()["modules"] == PICK


def test_the_choice_follows_the_account_not_the_family_profile(me):
    client, headers = me
    client.put("/api/dashboard", json={"modules": PICK}, headers=headers)
    first_profile = client.get("/api/profiles").json()[0]["id"]
    body = client.get(f"/api/profiles/{first_profile}").json()
    body.pop("id")
    body["name"] = "A second family"
    client.post("/api/profiles", json=body, headers=headers)
    assert client.get("/api/dashboard").json()["modules"] == PICK  # still one choice, whichever family is open


# ---- Storage ----------------------------------------------------------------------------------------------------------
def test_a_damaged_stored_choice_falls_back_to_the_default(me, db_path):
    client, _ = me
    user_id = client.get("/api/auth/me").json()["user"]["id"]
    for damaged in ("not json", json.dumps(["allocation_actions"]), json.dumps(["x", "y", "z", "w"]),
                    json.dumps(["risk_exposure"] * 4), json.dumps({"a": 1}), json.dumps(PICK[:3] + ["retired_module"]),
                    json.dumps([[1], [2], [3], [4]]), json.dumps([{"a": 1}] * 4), json.dumps([1, 2, 3, 4]), json.dumps([None] * 4), "null", ""):
        with sqlite3.connect(db_path) as con:
            con.execute("DELETE FROM dashboard_preferences")
            con.execute("INSERT INTO dashboard_preferences (user_id, modules, updated) VALUES (?, ?, 'x')", (user_id, damaged))
        body = client.get("/api/dashboard").json()
        assert body["modules"] == list(DEFAULT_MODULES) and body["is_default"] is True, damaged


def test_deleting_an_account_deletes_its_choice(db_path):
    db.migrate(db_path)
    user = accounts.create_user("to_be_removed", "long enough pass", db_path)
    dashboard.save(user["id"], PICK, db_path)
    assert dashboard.load(user["id"], db_path).modules == PICK
    with accounts.connect(db_path) as con:
        con.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        assert con.execute("SELECT COUNT(*) FROM dashboard_preferences").fetchone()[0] == 0


def test_a_private_demo_copy_takes_its_choice_with_it_when_purged(db_path):
    db.migrate(db_path)
    copy = accounts.create_throwaway_demo("legacy", db_path)
    dashboard.save(copy["id"], PICK, db_path)
    assert accounts.purge_throwaways(older_than_hours=-1, path=db_path) == 1  # "older than the future"
    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM dashboard_preferences").fetchone()[0] == 0


def test_the_default_is_a_valid_choice():
    assert len(DEFAULT_MODULES) == 4 == len(set(DEFAULT_MODULES))
    assert set(DEFAULT_MODULES) <= set(dashboard.AVAILABLE)
    assert set(dashboard.AVAILABLE) | {"holdings_consolidation"} == set(dashboard.MODULE_IDS)
