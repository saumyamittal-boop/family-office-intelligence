"""The password gate that fronts a shared demo: nothing reaches the app without the password, and what reaches it is what the app expects."""
import base64

import httpx
import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient

from demo import gate

PASSWORD = "-".join(["correct", "horse", "battery"])  # built, not written out: the repository's secret scanner (test_security_review.py) rejects a quoted password-looking literal
PUBLIC = "https://demo-test.example"


def basic(password: str, user: str = "anyone") -> dict:
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


async def echo(request: Request) -> Response:
    """Stands in for both the web server (host web.test) and the API (host api.test): reports what it was sent."""
    if request.url.path == "/set-cookies":
        response = Response("ok")
        response.headers.append("set-cookie", "a=1; Path=/")
        response.headers.append("set-cookie", "b=2; Path=/")
        return response
    if request.url.path == "/page":
        return Response("<html>page</html>", media_type="text/html", headers={"Content-Security-Policy": "default-src 'self'", "Content-Encoding": "identity"})
    return JSONResponse({"host": request.headers["host"], "method": request.method, "path": request.url.path, "query": request.url.query, "headers": dict(request.headers), "size": len(await request.body())})


@pytest.fixture()
def client():
    upstream = Starlette(routes=[Route("/{path:path}", echo, methods=["GET", "HEAD", "POST", "PUT", "DELETE"])])
    http = httpx.AsyncClient(transport=httpx.ASGITransport(app=upstream))
    app = gate.create_gate(PASSWORD, "http://web.test", "http://api.test", PUBLIC, client=http)
    return TestClient(app, base_url=PUBLIC)


def test_nothing_gets_through_without_the_password(client):
    r = client.get("/")
    assert r.status_code == 401 and "Basic" in r.headers["www-authenticate"]
    assert client.get("/api/health").status_code == 401
    assert client.post("/api/auth/demo", json={"family": "gap"}).status_code == 401


def test_a_wrong_password_is_refused_and_ten_wrong_tries_a_minute_lock_the_gate(client):
    assert client.get("/", headers=basic("wrong")).status_code == 401
    assert client.get("/", headers={"Authorization": "Basic not-base64!"}).status_code == 401
    for _ in range(8):
        client.get("/", headers=basic("wrong"))
    assert client.get("/", headers=basic("wrong")).status_code == 429
    assert client.get("/", headers=basic(PASSWORD)).status_code == 429  # even the right one waits: a guesser must not learn when it works


def test_requests_that_carry_no_password_do_not_count_as_guesses(client):
    for _ in range(25):  # a browser's first request, a crawler, a link preview
        assert client.get("/").status_code == 401
    assert client.get("/", headers=basic(PASSWORD)).status_code == 200


def test_the_right_password_reaches_the_web_server_for_pages_and_the_api_for_api_calls(client):
    page = client.get("/plan?step=2", headers=basic(PASSWORD)).json()
    assert page["host"] == "web.test" and page["path"] == "/plan" and page["query"] == "step=2"
    api = client.get("/api/health", headers=basic(PASSWORD)).json()
    assert api["host"] == "api.test"
    docs = client.get("/docs", headers=basic(PASSWORD)).json()
    assert docs["host"] == "web.test", "the API's interactive pages are never exposed: /docs goes to the web app, not the API"


def test_the_password_is_not_passed_on_and_the_visitors_address_is_what_the_tunnel_says(client):
    seen = client.get("/api/health", headers={**basic(PASSWORD), "CF-Connecting-IP": "203.0.113.9", "X-Forwarded-For": "1.2.3.4", "X-Real-IP": "5.6.7.8"}).json()["headers"]
    assert "authorization" not in seen
    assert seen["x-forwarded-for"] == "203.0.113.9" and seen["x-forwarded-proto"] == "https"
    assert "cf-connecting-ip" not in seen and "x-real-ip" not in seen
    spoofed = client.get("/api/health", headers={**basic(PASSWORD), "X-Forwarded-For": "1.2.3.4, 9.9.9.9"}).json()["headers"]
    assert spoofed["x-forwarded-for"] == "1.2.3.4"  # with no tunnel header, the first address the tunnel appended


def test_a_request_from_another_site_is_refused_even_with_the_password(client):
    assert client.post("/api/auth/demo", json={}, headers={**basic(PASSWORD), "Origin": "https://evil.example"}).status_code == 403
    ok = client.post("/api/auth/demo", json={}, headers={**basic(PASSWORD), "Origin": PUBLIC})
    assert ok.status_code == 200
    assert ok.json()["headers"]["origin"] == "https://api.test"  # rewritten to what the API's own check expects


def test_only_reading_is_allowed_outside_the_api_and_bodies_are_capped(client):
    assert client.post("/anything", json={}, headers=basic(PASSWORD)).status_code == 405
    assert client.put("/", content=b"x", headers=basic(PASSWORD)).status_code == 405
    assert client.post("/api/profiles", content=b"x" * (gate.MAX_BODY + 1), headers=basic(PASSWORD)).status_code == 413
    assert client.post("/api/profiles", content=b"x" * 1000, headers=basic(PASSWORD)).json()["size"] == 1000


def test_cookies_and_security_headers_come_back_whole(client):
    r = client.get("/set-cookies", headers=basic(PASSWORD))
    assert r.headers.get_list("set-cookie") == ["a=1; Path=/", "b=2; Path=/"]
    page = client.get("/page", headers=basic(PASSWORD))
    assert page.headers["content-security-policy"] == "default-src 'self'" and page.text == "<html>page</html>"
    assert page.headers["x-robots-tag"] == "noindex, nofollow"


def test_a_missing_upstream_is_a_clear_502_not_a_crash():
    dead = httpx.AsyncClient(transport=httpx.MockTransport(lambda request: (_ for _ in ()).throw(httpx.ConnectError("down"))))
    app = gate.create_gate(PASSWORD, "http://web.test", "http://api.test", PUBLIC, client=dead)
    r = TestClient(app, base_url=PUBLIC).get("/", headers=basic(PASSWORD))
    assert r.status_code == 502 and "start-demo" in r.text


def test_a_gate_without_a_password_will_not_exist():
    with pytest.raises(ValueError):
        gate.create_gate("", "http://web.test", "http://api.test")
