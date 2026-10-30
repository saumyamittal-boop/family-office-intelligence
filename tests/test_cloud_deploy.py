"""The hosting package (deploy/cloud): the web server matches the laptop demo's, and the gate sees only the address the host adds."""
import importlib.util
import re
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"cloud_{name}", ROOT / "deploy" / "cloud" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


static_site = _load("static_site")
run = _load("run")


def test_headers_match_the_web_apps_own_list():
    source = (ROOT / "web" / "security-headers.ts").read_text(encoding="utf-8")
    csp = re.search(r"export const CSP = \[(.*?)\]\.join", source, re.S).group(1)
    assert static_site.CSP == "; ".join(re.findall(r'"([^"]+)"', csp))
    block = re.search(r"SECURITY_HEADERS[^{]*\{(.*?)\};", source, re.S).group(1)
    named = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', block))
    assert {k: v for k, v in static_site.SECURITY_HEADERS.items() if k != "Content-Security-Policy"} == named


@pytest.fixture
def site(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "app-abc123.js").write_text("console.log(1)")
    (tmp_path.parent / "secret.txt").write_text("not for visitors")
    return TestClient(static_site.create_site(tmp_path))


def test_files_and_page_addresses(site):
    asset = site.get("/assets/app-abc123.js")
    assert asset.text == "console.log(1)" and "immutable" in asset.headers["cache-control"]
    page = site.get("/profiles/3/plan")  # an address inside the app: index.html, not a 404
    assert page.text == "<html>app</html>" and page.headers["cache-control"] == "no-cache"
    assert page.headers["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in page.headers["content-security-policy"]


def test_nothing_outside_dist(site):
    for path in ("/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"):
        assert "not for visitors" not in site.get(path).text


def test_only_reads(site):
    assert site.post("/index.html").status_code == 405


def _seen_by_gate(headers: dict) -> dict:
    async def echo(request: Request):
        return JSONResponse({k: v for k, v in request.headers.items() if k in ("x-forwarded-for", "cf-connecting-ip", "x-real-ip")})

    client = TestClient(run._proxy_client_address(Starlette(routes=[Route("/", echo)])))
    return client.get("/", headers=headers).json()


def test_only_the_address_the_host_added_reaches_the_gate():
    spoofed = {"CF-Connecting-IP": "1.1.1.1", "X-Real-IP": "2.2.2.2", "X-Forwarded-For": "3.3.3.3, 203.0.113.9:51234"}
    assert _seen_by_gate(spoofed) == {"x-forwarded-for": "203.0.113.9"}
    assert _seen_by_gate({"X-Forwarded-For": "[2001:db8::7]:443"}) == {"x-forwarded-for": "2001:db8::7"}
    assert _seen_by_gate({}) == {}
