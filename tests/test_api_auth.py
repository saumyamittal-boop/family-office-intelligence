"""Authentication, sessions, CSRF, throttling and the private demo families."""
import sqlite3

import pytest

from fo import accounts
from tests.helpers import demo, profile_body, sign_up

PROTECTED = [
    ("GET", "/api/auth/me"), ("POST", "/api/auth/logout"),
    ("GET", "/api/profiles"), ("POST", "/api/profiles"),
    ("GET", "/api/profiles/1"), ("PUT", "/api/profiles/1"), ("DELETE", "/api/profiles/1"),
    ("GET", "/api/profiles/1/analysis"),
]


@pytest.mark.parametrize("method, path", PROTECTED)
def test_every_protected_endpoint_rejects_anonymous_callers(client, method, path):
    r = client.request(method, path, json={} if method in {"POST", "PUT"} else None)
    assert r.status_code == 401, (method, path, r.status_code)
    assert r.json()["detail"] == "Please sign in."


def test_public_endpoints_need_no_sign_in_and_reveal_nothing_sensitive(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert meta["data_source"] == "sample" and "not investment advice" in meta["disclaimer"]
    assert set(meta["demo_families"]) == {"legacy", "business", "nextgen", "gap"}


def test_signup_then_login_and_the_cookie_is_locked_down(client):
    r = client.post("/api/auth/signup", json={"username": "asha", "password": "a long enough pass"})
    assert r.status_code == 201 and r.json()["user"]["username"] == "asha"
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie and "secure" not in cookie
    assert "password" not in r.text and "hash" not in r.text and "salt" not in r.text

    again = client.post("/api/auth/login", json={"username": "ASHA", "password": "a long enough pass"})
    assert again.status_code == 200 and again.json()["user"]["is_demo"] is False


def test_the_cookie_is_marked_secure_when_the_site_runs_over_https(make_client):
    c = make_client(cookie_secure=True)
    r = c.post("/api/auth/signup", json={"username": "secure_user", "password": "a long enough pass"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_wrong_password_and_unknown_user_look_identical(client):
    sign_up(client, "real_user")
    other = client.post("/api/auth/login", json={"username": "real_user", "password": "not the password"})
    unknown = client.post("/api/auth/login", json={"username": "nobody_here", "password": "not the password"})
    assert other.status_code == unknown.status_code == 401
    assert other.json() == unknown.json()
    assert "set-cookie" not in other.headers


def test_signup_rules_are_enforced(client):
    assert client.post("/api/auth/signup", json={"username": "x", "password": "long enough pass"}).status_code == 422
    assert client.post("/api/auth/signup", json={"username": "okname", "password": "short"}).status_code == 422
    sign_up(client, "taken_name")
    dup = client.post("/api/auth/signup", json={"username": "TAKEN_name", "password": "long enough pass"})
    assert dup.status_code == 422 and "already taken" in dup.json()["detail"]


def test_signup_cap_closes_registration_but_not_the_demos(make_client):
    c = make_client(max_accounts=1)
    sign_up(c, "first_user")
    r = make_client(max_accounts=1).post("/api/auth/signup", json={"username": "second", "password": "long enough pass"})
    assert r.status_code == 422 and "closed" in r.json()["detail"]
    assert make_client(max_accounts=1).post("/api/auth/demo", json={"family": "legacy"}).status_code == 200


def test_five_wrong_passwords_lock_the_account_even_for_the_right_password(client):
    sign_up(client, "target_user", "the real password")
    bad = {"username": "target_user", "password": "wrong wrong"}
    for _ in range(5):
        assert client.post("/api/auth/login", json=bad).status_code == 401
    locked = client.post("/api/auth/login", json={"username": "target_user", "password": "the real password"})
    assert locked.status_code == 429 and int(locked.headers["retry-after"]) > 0
    assert "minute" in locked.json()["detail"]


def test_a_correct_login_clears_earlier_failures(client):
    sign_up(client, "forgetful", "the real password")
    for _ in range(4):
        client.post("/api/auth/login", json={"username": "forgetful", "password": "wrong wrong"})
    assert client.post("/api/auth/login", json={"username": "forgetful", "password": "the real password"}).status_code == 200
    for _ in range(4):
        assert client.post("/api/auth/login", json={"username": "forgetful", "password": "wrong wrong"}).status_code == 401


def test_logout_ends_the_session_for_good(client, make_client):
    headers = sign_up(client, "leaving_user")
    stolen = client.cookies.get("fo_session")
    assert client.get("/api/auth/me").status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    replay = make_client()
    replay.cookies.set("fo_session", stolen)
    assert replay.get("/api/auth/me").status_code == 401


def test_expired_forged_and_oversized_cookies_are_rejected(client, db_path):
    sign_up(client, "short_session")
    assert client.get("/api/auth/me").status_code == 200
    with sqlite3.connect(db_path) as con:
        con.execute("UPDATE sessions SET expires = '2000-01-01T00:00:00+00:00'")
    assert client.get("/api/auth/me").status_code == 401
    for junk in ("forged-token", "", "x" * 5000, "'; DROP TABLE sessions;--"):
        client.cookies.set("fo_session", junk)
        assert client.get("/api/profiles").status_code == 401


def test_only_a_hash_of_the_session_token_is_stored(client, db_path):
    sign_up(client, "hash_check")
    token = client.cookies.get("fo_session")
    with sqlite3.connect(db_path) as con:
        stored = [row[0] for row in con.execute("SELECT token_hash FROM sessions")]
    assert stored and token not in stored and all(len(h) == 64 for h in stored)


# ---- CSRF ------------------------------------------------------------------------------------------------------------
def test_state_changing_requests_need_the_csrf_token(client):
    headers = sign_up(client, "csrf_user")
    body = profile_body(client)
    assert client.post("/api/profiles", json=body).status_code == 403
    assert client.post("/api/profiles", json=body, headers={"X-CSRF-Token": "guess"}).status_code == 403
    assert client.post("/api/profiles", json=body, headers=headers).status_code == 201


def test_a_csrf_token_from_another_session_does_not_work(client, make_client):
    sign_up(client, "victim_user")
    attacker_headers = sign_up(make_client(), "attacker_user")
    assert client.post("/api/profiles", json=profile_body(client), headers=attacker_headers).status_code == 403


def test_the_csrf_token_is_stable_for_a_session_and_returned_by_me(client):
    headers = sign_up(client, "stable_csrf")
    assert client.get("/api/auth/me").json()["csrf_token"] == headers["X-CSRF-Token"]


# ---- Private demo families (ADR-0017, decision D9) ---------------------------------------------------------------------
def test_every_demo_sign_in_gets_its_own_private_copy(client, make_client):
    first = demo(client, "business")
    second_browser = make_client()
    demo(second_browser, "business")
    a, b = client.get("/api/auth/me").json()["user"], second_browser.get("/api/auth/me").json()["user"]
    assert a["id"] != b["id"] and a["is_demo"] and b["is_demo"] and a["username"] != b["username"]

    body = profile_body(client)
    body["name"] = "Edited by the first visitor"
    pid = client.get("/api/profiles").json()[0]["id"]
    assert client.put(f"/api/profiles/{pid}", json=body, headers=first).status_code == 200
    assert second_browser.get("/api/profiles").json()[0]["name"] != "Edited by the first visitor"
    assert profile_body(second_browser)["name"] == accounts.PERSONAS["B"].name


def test_demo_users_cannot_sign_in_with_a_password(client):
    demo(client, "legacy")
    username = client.get("/api/auth/me").json()["user"]["username"]
    for guess in ("", "password", "demo"):
        r = client.post("/api/auth/login", json={"username": username, "password": guess or "x"})
        assert r.status_code == 401


def test_the_liquidity_gap_demo_opens_on_the_stricter_cover(client):
    r = client.post("/api/auth/demo", json={"family": "gap"})
    assert r.json()["default_basis"] == "strict" and client.get("/api/auth/me").json()["default_basis"] == "strict"
    other = client.post("/api/auth/demo", json={"family": "legacy"})
    assert other.json()["default_basis"] == "all"


def test_unknown_demo_families_are_refused(client):
    assert client.post("/api/auth/demo", json={"family": "nope"}).status_code == 422
    assert client.post("/api/auth/demo", json={"family": "../etc/passwd"}).status_code == 422


def test_demo_login_can_be_switched_off(make_client):
    c = make_client(demo_login=False)
    assert c.post("/api/auth/demo", json={"family": "legacy"}).status_code == 404
    assert c.get("/api/meta").json()["demo_families"] == []


def test_old_demo_copies_are_deleted_with_their_profiles_and_sessions(client, db_path):
    demo(client, "nextgen")
    user_id = client.get("/api/auth/me").json()["user"]["id"]
    with sqlite3.connect(db_path) as con:
        con.execute("UPDATE users SET created = '2000-01-01T00:00:00+00:00' WHERE id = ?", (user_id,))
    assert accounts.purge_throwaways(24) == 1
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys = ON")
        assert con.execute("SELECT COUNT(*) FROM profiles WHERE user_id = ?", (user_id,)).fetchone()[0] == 0
    assert client.get("/api/auth/me").status_code == 401  # the session went with the copy


def test_purging_never_touches_the_shared_demo_rows_or_real_accounts(client, make_client, db_path):
    sign_up(make_client(), "real_member")
    demo(client, "legacy")
    assert accounts.purge_throwaways(older_than_hours=-1) == 1  # the demo copy is "older than the future"
    with sqlite3.connect(db_path) as con:
        names = {row[0] for row in con.execute("SELECT username FROM users")}
    assert {"real_member", "legacy", "business", "nextgen", "gap"} <= names
    assert not any(n.startswith("demo-") for n in names)
