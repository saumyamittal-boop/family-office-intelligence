"""Phase 7 security review, as tests (docs/migration/phase-7-report.md).

Each test is one claim about the API that is easy to state and easy to get wrong: who may call what, what a request must carry, what the server
keeps and what it must never keep, what it says when something fails. They walk the API's own OpenAPI document, so an endpoint added later is
covered automatically (and fails here until it is classified).
"""
import hashlib
import logging
import pathlib
import re
import sqlite3

import pytest

from fo import accounts
from tests.helpers import profile_body, sign_up

METHODS = ("get", "post", "put", "delete", "patch")
# Operations anyone may call without signing in: they hold no one's data, or they are how a person signs in.
PUBLIC = {
    ("GET", "/api/health"), ("GET", "/api/meta"), ("GET", "/api/plan/config"), ("GET", "/api/explain/catalog"), ("GET", "/api/holdings/template"),
    ("POST", "/api/auth/login"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/demo"),
}
SIGN_IN_POSTS = {("POST", "/api/auth/login"), ("POST", "/api/auth/signup"), ("POST", "/api/auth/demo")}  # no session yet, so no CSRF token to carry


def operations(client) -> list[tuple[str, str]]:
    spec = client.app.openapi()
    return sorted((m.upper(), p) for p, ms in spec["paths"].items() for m in ms if m in METHODS)


def concrete(path: str, profile_id: int = 1, import_id: int = 1) -> str:
    return path.replace("{profile_id}", str(profile_id)).replace("{import_id}", str(import_id))


# ---- authentication: who may call what ------------------------------------------------------------------------------------
def test_the_api_has_the_operations_this_review_covers(client):
    assert len(operations(client)) == 32  # a new endpoint changes this on purpose: classify it below before updating the number


def test_every_operation_but_the_public_ones_refuses_a_caller_who_is_not_signed_in(client):
    open_ones = set()
    for method, path in operations(client):
        r = client.request(method, concrete(path), json={} if method != "GET" else None)
        if r.status_code != 401:
            open_ones.add((method, path))
    assert open_ones == PUBLIC, f"unexpectedly open: {sorted(open_ones - PUBLIC)}; unexpectedly closed: {sorted(PUBLIC - open_ones)}"


def test_every_state_changing_operation_needs_the_csrf_token_even_when_signed_in(client):
    sign_up(client, "csrf_walker")
    missing = []
    for method, path in operations(client):
        if method == "GET" or (method, path) in SIGN_IN_POSTS:
            continue
        if client.request(method, concrete(path), json={}).status_code != 403:
            missing.append((method, path))
    assert not missing, f"state-changing operations that do not insist on the CSRF token: {missing}"


def test_nothing_that_only_reads_changes_anything(client):
    """GET is safe by convention only; check the database is byte-for-byte unchanged after calling every GET."""
    sign_up(client, "reader")
    before = _dump(accounts.DB_PATH)
    for method, path in operations(client):
        if method == "GET":
            client.get(concrete(path, profile_id=client.get("/api/profiles").json()[0]["id"]))
    assert _dump(accounts.DB_PATH) == before


def _dump(path) -> list[str]:
    con = sqlite3.connect(path)
    try:
        return [line for line in con.iterdump() if "sessions" not in line]  # opening a page may extend nothing, but sessions are written by sign-in itself
    finally:
        con.close()


def test_a_csrf_token_belongs_to_one_session(make_client):
    one, two = make_client(), make_client()
    h_one, h_two = sign_up(one, "csrf_one"), sign_up(two, "csrf_two")
    assert h_one != h_two
    assert one.post("/api/auth/logout", headers=h_two).status_code == 403  # another session's token is useless here
    assert one.post("/api/auth/logout", headers=h_one).status_code == 204


# ---- authorisation: one account never reaches another's data ------------------------------------------------------------
def _scoped_requests(owner_client, pid: int) -> list[tuple[str, str, dict | None]]:
    csv = "Name,Asset class,Account,Value (Cr)\nFund A,Large-cap equity,Demat 1,40\n"
    import base64

    file = {"filename": "s.csv", "content_base64": base64.b64encode(csv.encode()).decode()}
    base = f"/api/profiles/{pid}"
    return [
        ("GET", base, None), ("PUT", base, profile_body(owner_client, pid)), ("DELETE", base, None),
        ("GET", f"{base}/analysis", None), ("GET", f"{base}/history", None), ("POST", f"{base}/explain", {"intent": "help"}),
        ("POST", f"{base}/scenarios", {"preset": "Market crash"}),
        ("POST", f"{base}/holdings/preview", file), ("POST", f"{base}/holdings/imports", file), ("GET", f"{base}/holdings/imports", None),
        ("DELETE", f"{base}/holdings/imports/1", None), ("GET", f"{base}/holdings/consolidation", None),
        ("POST", f"{base}/holdings/apply/preview", {"set_corpus": False}), ("POST", f"{base}/holdings/apply", {"set_corpus": False}),
    ]


def test_another_accounts_profile_is_simply_not_found_on_every_route_that_names_a_profile(make_client):
    owner, stranger = make_client(), make_client()
    h_owner, h_stranger = sign_up(owner, "owner_iso"), sign_up(stranger, "stranger_iso")
    pid = owner.get("/api/profiles").json()[0]["id"]
    requests = _scoped_requests(owner, pid)

    covered = {(m, re.sub(r"/profiles/\d+", "/profiles/{profile_id}", re.sub(r"/imports/\d+", "/imports/{import_id}", p))) for m, p, _ in requests}
    named = {(m, p) for m, p in operations(owner) if "{profile_id}" in p}
    assert covered == named, f"routes that name a profile but are not in the isolation table: {sorted(named - covered)}"

    for method, path, body in requests:
        r = stranger.request(method, path, json=body, headers=h_stranger if method != "GET" else None)
        assert r.status_code == 404, (method, path, r.status_code, r.text[:120])
        assert r.json()["detail"] == "Profile not found."  # the same words as for a profile that does not exist
    # and the owner's data was not touched by any of it
    assert owner.get(f"/api/profiles/{pid}").status_code == 200
    assert owner.get("/api/profiles").json()[0]["id"] == pid


def test_a_missing_profile_and_somebody_elses_profile_look_identical(make_client):
    owner, stranger = make_client(), make_client()
    sign_up(owner, "twin_owner")
    sign_up(stranger, "twin_stranger")
    pid = owner.get("/api/profiles").json()[0]["id"]
    theirs = stranger.get(f"/api/profiles/{pid}")
    nothing = stranger.get("/api/profiles/999999")
    assert (theirs.status_code, theirs.json()) == (nothing.status_code, nothing.json())


def test_nothing_the_client_sends_can_name_the_user(client):
    """The user comes from the session alone: ids, usernames and headers in the request are ignored."""
    sign_up(client, "real_user")
    r = client.get("/api/auth/me", headers={"X-User-Id": "1", "X-Username": "gap", "X-Forwarded-User": "legacy"}, params={"user_id": 1, "username": "gap"})
    assert r.json()["user"]["username"] == "real_user"


def test_each_account_has_its_own_dashboard_choice(make_client):
    one, two = make_client(), make_client()
    h_one, _ = sign_up(one, "dash_one"), sign_up(two, "dash_two")
    chosen = ["why_this_recommendation"] if False else one.get("/api/dashboard").json()["modules"][::-1]
    assert one.put("/api/dashboard", json={"modules": chosen}, headers=h_one).status_code == 200
    assert two.get("/api/dashboard").json()["modules"] != chosen


# ---- sessions and cookies ----------------------------------------------------------------------------------------------
def _cookie(client) -> str:
    return client.cookies.get("fo_session")


def test_a_session_token_is_long_random_and_only_its_hash_is_stored(client):
    sign_up(client, "token_check")
    token = _cookie(client)
    assert len(token) >= 40 and re.fullmatch(r"[A-Za-z0-9_-]+", token)
    con = sqlite3.connect(accounts.DB_PATH)
    try:
        rows = con.execute("SELECT token_hash FROM sessions").fetchall()
        raw = b"".join(line.encode() for line in con.iterdump())
    finally:
        con.close()
    assert token.encode() not in raw  # the token itself is nowhere in the database
    assert hashlib.sha256(token.encode()).hexdigest() in {r[0] for r in rows}


def test_signing_in_again_issues_a_new_token_and_retires_the_old_one(make_client):
    a = make_client()
    sign_up(a, "fixation")
    first = _cookie(a)
    r = a.post("/api/auth/login", json={"username": "fixation", "password": "correct horse battery"})
    assert r.status_code == 200 and _cookie(a) != first  # a fresh token every time: nothing an attacker planted is kept
    b = make_client()
    b.cookies.set("fo_session", first)
    assert b.get("/api/auth/me").status_code == 401  # and the one this browser held before no longer works anywhere
    assert a.get("/api/auth/me").status_code == 200


def test_signing_in_clears_out_expired_sessions(make_client):
    a = make_client()
    sign_up(a, "tidy_one")
    con = sqlite3.connect(accounts.DB_PATH)
    con.execute("UPDATE sessions SET expires = '2000-01-01T00:00:00+00:00'")
    con.commit()
    con.close()
    make_client().post("/api/auth/login", json={"username": "tidy_one", "password": "correct horse battery"})
    con = sqlite3.connect(accounts.DB_PATH)
    try:
        assert con.execute("SELECT COUNT(*) FROM sessions WHERE expires < '2001-01-01'").fetchone()[0] == 0
    finally:
        con.close()


def test_logging_out_ends_the_session_on_the_server_not_just_in_the_browser(make_client):
    a = make_client()
    headers = sign_up(a, "logout_check")
    token = _cookie(a)
    assert a.post("/api/auth/logout", headers=headers).status_code == 204
    b = make_client()
    b.cookies.set("fo_session", token)  # somebody who copied the cookie earlier
    assert b.get("/api/auth/me").status_code == 401


def test_an_expired_session_is_refused(client):
    sign_up(client, "expiry")
    con = sqlite3.connect(accounts.DB_PATH)
    con.execute("UPDATE sessions SET expires = '2000-01-01T00:00:00+00:00'")
    con.commit()
    con.close()
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("junk", ["", "x", "a" * 500, "../../etc/passwd", "'; DROP TABLE sessions; --", "\x00", "null", "undefined"])
def test_garbage_in_the_session_cookie_is_just_not_signed_in(client, junk):
    client.cookies.set("fo_session", junk)
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/health").status_code == 200  # and the database is fine afterwards


def test_the_session_cookie_cannot_be_read_by_scripts_or_sent_cross_site(client):
    r = client.post("/api/auth/signup", json={"username": "cookie_flags", "password": "correct horse battery"})
    header = r.headers["set-cookie"].lower()
    assert "httponly" in header and "samesite=lax" in header and "path=/" in header and "max-age=" in header
    assert "secure" not in header  # off by default for plain-http local use


def test_the_cookie_is_marked_secure_when_configured(make_client):
    c = make_client(cookie_secure=True)
    r = c.post("/api/auth/signup", json={"username": "secure_flag", "password": "correct horse battery"})
    assert "secure" in r.headers["set-cookie"].lower()


def test_the_cookie_is_marked_secure_whenever_the_request_came_over_https(make_client):
    """Safe by default: a site served over HTTPS must not send its session cookie in the clear, even if nobody remembered to set the flag."""
    c = make_client()
    r = c.post("https://testserver/api/auth/signup", json={"username": "https_flag", "password": "correct horse battery"})
    assert "secure" in r.headers["set-cookie"].lower()
    assert "strict-transport-security" in r.headers  # and the browser is told to keep using https


def test_demo_sign_in_can_be_turned_off(make_client):
    c = make_client(demo_login=False)
    assert c.post("/api/auth/demo", json={"family": "gap"}).status_code == 404


def test_the_interactive_docs_can_be_hidden(make_client):
    c = make_client(docs=False)
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404


# ---- passwords ---------------------------------------------------------------------------------------------------------
def test_passwords_are_never_stored_returned_or_logged(client, caplog):
    secret = "tr0ub4dor-marker-9f3a"
    with caplog.at_level(logging.DEBUG):
        r = client.post("/api/auth/signup", json={"username": "pw_check", "password": secret})
        client.post("/api/auth/login", json={"username": "pw_check", "password": secret + "x"})
    assert secret not in r.text and secret not in caplog.text
    con = sqlite3.connect(accounts.DB_PATH)
    try:
        raw = b"".join(line.encode() for line in con.iterdump())
        row = con.execute("SELECT salt, hash FROM users WHERE username = 'pw_check'").fetchone()
    finally:
        con.close()
    assert secret.encode() not in raw and len(row[0]) == 16 and len(row[1]) == 32  # a random salt and a 32-byte scrypt digest


def test_two_accounts_with_the_same_password_get_different_hashes(client):
    for name in ("same_pw_a", "same_pw_b"):
        client.post("/api/auth/signup", json={"username": name, "password": "correct horse battery"})
    con = sqlite3.connect(accounts.DB_PATH)
    try:
        a, b = [row[0] for row in con.execute("SELECT hash FROM users WHERE username IN ('same_pw_a', 'same_pw_b') ORDER BY username")]
    finally:
        con.close()
    assert a != b


def test_a_wrong_password_and_an_unknown_user_get_the_same_answer(client):
    sign_up(client, "known_user")
    wrong = client.post("/api/auth/login", json={"username": "known_user", "password": "not the password"})
    unknown = client.post("/api/auth/login", json={"username": "nobody_here", "password": "not the password"})
    assert (wrong.status_code, wrong.json()) == (unknown.status_code, unknown.json()) == (401, wrong.json())


def test_demo_accounts_cannot_be_signed_into_with_a_password(client):
    for name in ("legacy", "business", "nextgen", "gap"):
        for password in ("", "password", "legacy", name):
            r = client.post("/api/auth/login", json={"username": name, "password": password or "x"})
            assert r.status_code in (401, 422, 429)


def test_repeated_wrong_passwords_lock_that_username_for_a_while(client):
    sign_up(client, "lock_me")
    codes = [client.post("/api/auth/login", json={"username": "lock_me", "password": "wrong password"}).status_code for _ in range(7)]
    assert codes[:5] == [401] * 5 and codes[5:] == [429, 429]
    assert client.post("/api/auth/login", json={"username": "lock_me", "password": "correct horse battery"}).status_code == 429  # even the right one, while locked


def test_the_signup_cap_and_username_rules_hold(make_client):
    c = make_client(max_accounts=1)
    assert c.post("/api/auth/signup", json={"username": "first_user", "password": "correct horse battery"}).status_code == 201
    assert c.post("/api/auth/signup", json={"username": "second_user", "password": "correct horse battery"}).status_code == 422
    for bad in ("ab", "x" * 33, "has space", "semi;colon", "quote'", "\u00e9\u00e9\u00e9", "../up", "a\x00b"):
        assert make_client().post("/api/auth/signup", json={"username": bad, "password": "correct horse battery"}).status_code == 422


# ---- request guards ---------------------------------------------------------------------------------------------------
def test_response_headers_on_the_api(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["referrer-policy"] == "no-referrer"
    assert r.headers["cache-control"] == "no-store"
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'none'" in csp and "frame-ancestors 'none'" in csp  # an API response is never a page


def test_a_body_over_the_limit_is_refused_by_declared_length(make_client):
    c = make_client(max_body_bytes=1024)
    r = c.post("/api/auth/login", content=b'{"username":"a","password":"' + b"x" * 5000 + b'"}', headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_a_body_over_the_limit_is_refused_even_when_it_does_not_declare_its_length(make_client):
    """Chunked uploads carry no Content-Length. The limit has to be enforced on the bytes that actually arrive."""
    c = make_client(max_body_bytes=1024)

    def chunks():
        for _ in range(50):
            yield b'{"username":"a","password":"' + b"x" * 200 if _ == 0 else b"x" * 200
        yield b'"}'

    r = c.post("/api/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413, r.status_code


def test_a_body_that_is_not_json_is_refused_even_when_it_does_not_declare_its_length(client):
    def chunks():
        yield b"username=a&password=b"

    r = client.post("/api/auth/login", content=chunks(), headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415, r.status_code


def test_a_form_or_text_body_is_refused(client):
    for content_type in ("application/x-www-form-urlencoded", "text/plain", "multipart/form-data; boundary=x", ""):
        r = client.post("/api/auth/login", content=b"username=a&password=b", headers={"Content-Type": content_type})
        assert r.status_code == 415, content_type


def test_a_request_from_another_website_is_refused_before_it_does_anything(client):
    headers = sign_up(client, "origin_check")
    for origin in ("https://evil.example", "http://localhost:5174", "null", "http://localhost:5173.evil.example"):
        r = client.post("/api/profiles", json={}, headers={**headers, "Origin": origin})
        assert r.status_code == 403 and "origin" in r.json()["detail"].lower(), origin


def test_cross_origin_requests_get_no_cors_permission_for_other_sites(client):
    r = client.options("/api/profiles", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"})
    assert "access-control-allow-origin" not in r.headers
    ok = client.options("/api/profiles", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173" and ok.headers.get("access-control-allow-credentials") == "true"


# ---- error handling ---------------------------------------------------------------------------------------------------
def test_an_unexpected_failure_says_nothing_about_the_inside(make_client, monkeypatch):
    from fastapi.testclient import TestClient

    c = TestClient(make_client().app, raise_server_exceptions=False)  # answer like a real server instead of re-raising into the test
    headers = sign_up(c, "boom")

    def explode(*args, **kwargs):
        raise RuntimeError("secret internal detail: C:\\Users\\someone\\data\\app.db")

    monkeypatch.setattr("api.routers.profiles.accounts.list_profiles", explode)
    r = c.get("/api/profiles")
    assert r.status_code == 500 and r.json() == {"detail": "Something went wrong on our side.", "problems": None}
    assert "secret" not in r.text and "RuntimeError" not in r.text and "Traceback" not in r.text and headers


def test_validation_errors_name_the_field_but_never_echo_what_was_sent(client):
    r = client.post("/api/auth/login", json={"username": 12345, "password": ["marker-value-77"], "extra": "marker-extra-88"})
    assert r.status_code == 422 and "marker-value-77" not in r.text and "marker-extra-88" not in r.text


def test_unknown_paths_and_wrong_methods_use_the_one_error_shape(client):
    for method, path in (("GET", "/api/nope"), ("DELETE", "/api/health"), ("PATCH", "/api/profiles"), ("GET", "/api/profiles/abc"), ("GET", "/api/profiles/99999999999999999999")):
        r = client.request(method, path)
        assert r.status_code in (401, 404, 405, 422) and set(r.json()) == {"detail", "problems"}, (method, path, r.status_code)


def test_oversized_and_odd_numbers_in_a_path_do_not_crash_the_server(client):
    sign_up(client, "path_numbers")
    for pid in ("0", "-1", "2147483648", "1e5", "٣", "%00", "1;2", "1 OR 1=1"):
        r = client.get(f"/api/profiles/{pid}")
        assert r.status_code in (404, 422), (pid, r.status_code)


# ---- data handling ----------------------------------------------------------------------------------------------------
def test_hostile_text_is_stored_and_returned_as_plain_text(client):
    headers = sign_up(client, "text_check")
    body = profile_body(client)
    nasty = "Robert'); DROP TABLE users;-- <script>alert(1)</script> \u202e \u0000".replace("\u0000", "")
    body["name"] = nasty[:60]
    r = client.post("/api/profiles", json=body, headers=headers)
    assert r.status_code in (201, 422)
    if r.status_code == 201:
        assert client.get(f"/api/profiles/{r.json()['id']}").json()["name"] == nasty[:60].strip()  # stored as text, tidied only at the ends
    assert client.get("/api/profiles").status_code == 200  # the tables are still there
    assert sqlite3.connect(accounts.DB_PATH).execute("SELECT COUNT(*) FROM users").fetchone()[0] >= 5


def test_no_sql_is_built_by_gluing_text_together():
    root = pathlib.Path(__file__).resolve().parent.parent
    hits = []
    for folder in ("api", "fo"):
        for path in (root / folder).rglob("*.py"):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"\.execute(many|script)?\(\s*f[\"']", line) or re.search(r"\.execute(many|script)?\(.*[\"']\s*(%|\+)\s*\w", line) or re.search(r"\.execute(many|script)?\(.*\.format\(", line):
                    hits.append(f"{path.relative_to(root)}:{number}: {line.strip()[:100]}")
    assert not hits, hits


# ---- the throttles ---------------------------------------------------------------------------------------------------
def test_the_throttle_does_not_grow_without_limit():
    from fo.security import Throttle

    now = [0.0]
    t = Throttle(5, 10.0, clock=lambda: now[0])
    for i in range(20_000):
        t.record_failure(f"user-{i}")
    now[0] = 1000.0  # everything has expired
    t.record_failure("one-more")
    assert len(t._failures) < 1000, len(t._failures)  # expired keys are dropped, not kept forever


def test_the_throttle_still_blocks_and_then_releases():
    from fo.security import Throttle

    now = [0.0]
    t = Throttle(3, 60.0, clock=lambda: now[0])
    for _ in range(3):
        t.record_failure("k")
    assert t.blocked_for("k") > 0 and t.blocked_for("other") == 0
    now[0] = 61.0
    assert t.blocked_for("k") == 0


def test_the_expensive_endpoints_are_rate_limited_per_person(make_client):
    c = make_client()
    headers = sign_up(c, "heavy")
    pid = c.get("/api/profiles").json()[0]["id"]
    codes = [c.post(f"/api/profiles/{pid}/scenarios", json={"preset": "Market crash"}, headers=headers).status_code for _ in range(100)]
    assert 429 in codes and codes[0] == 200 and codes.count(200) >= 60  # generous enough for dragging a slider, not for a loop
    codes = [c.get(f"/api/profiles/{pid}/analysis").status_code for _ in range(260)]
    assert 429 in codes and codes[0] == 200


# ---- configuration and secrets ---------------------------------------------------------------------------------------
def test_garbage_in_the_environment_falls_back_to_safe_values(monkeypatch):
    from api.config import Settings

    for name in ("FO_API_SESSION_HOURS", "FO_API_DEMO_HOURS", "FO_API_MAX_PROFILES", "FO_API_MAX_BODY_KB", "FO_MAX_ACCOUNTS", "FO_API_ANALYSIS_TIMEOUT"):
        monkeypatch.setenv(name, "not-a-number")
    s = Settings.from_env()
    assert s.session_hours == 12.0 and s.max_body_bytes == 256 * 1024 and s.max_profiles == 25 and s.analysis_timeout == 90.0
    monkeypatch.setenv("FO_API_SESSION_HOURS", "-5")
    assert Settings.from_env().session_hours >= 0.1  # never a negative or zero-length session
    monkeypatch.setenv("FO_API_CORS_ORIGINS", " , ,")
    assert Settings.from_env().cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_nothing_that_looks_like_a_secret_is_in_the_repository_files():
    root = pathlib.Path(__file__).resolve().parent.parent
    skip = {".venv", "node_modules", "dist", ".git", "__pycache__", "models", ".pytest_cache"}
    this_file = pathlib.Path(__file__).resolve()
    patterns = {
        "private key": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
        "AWS key": re.compile(r"AKIA[0-9A-Z]{16}"),
        "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
        "API key": re.compile(r"\bsk-[A-Za-z0-9]{20,}"),
        "Slack token": re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
        "assigned secret": re.compile(r"(?i)\b(api[_-]?key|secret|passw(or)?d|token)\s*[:=]\s*[\"'][A-Za-z0-9/+_\-]{16,}[\"']"),
    }
    hits = []
    for path in root.rglob("*"):
        if not path.is_file() or path.resolve() == this_file or skip & set(path.relative_to(root).parts) or path.suffix in {".png", ".ico", ".db", ".onnx", ".xlsx", ".woff2", ".pyc"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for label, pattern in patterns.items():
            for match in pattern.finditer(text):
                hits.append(f"{path.relative_to(root)}: {label}: {match.group(0)[:30]}...")
    assert not hits, hits


def test_the_database_file_and_environment_files_are_never_committed():
    root = pathlib.Path(__file__).resolve().parent.parent
    ignore = (root / ".gitignore").read_text(encoding="utf-8")
    for needed in ("data/app.db", ".env", "data/models/", ".streamlit/secrets.toml"):
        assert needed in ignore, needed
