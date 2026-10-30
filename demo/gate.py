"""A password gate and reverse proxy for sharing the demo through a tunnel.

    python demo/gate.py            (started for you by demo\\share-demo.cmd; settings come from environment variables)

Why it exists: the Streamlit version has an access code, the React version has none, so a public address would let anyone create accounts. This
puts HTTP Basic authentication (any user name, one shared password) in front of everything, then does what the reverse proxy in
docs/deployment-react.md does: it sends /api/* to the API and every other path to the web server, and tells the API the visitor's real address
(so the per-address rate limits count visitors, not the tunnel).

How a visitor gives the password: a browser opening a page gets a small password page (/__gate); the right password sets a signed cookie
for 12 hours. The browser's own sign-in popup (HTTP Basic) still works and is what scripts use, but some browsers never show that popup
(in-app browsers on phones, links opened from WhatsApp or e-mail apps), so a page is the reliable way. The cookie is signed with a key made
when the gate starts, so a restart or a new password signs everyone out; it is never passed on to the app.

What it enforces itself:
  * the password, with a global limit of 10 wrong tries a minute (popup and page together);
  * the Origin of every browser request must be this site's public address (the API's own cross-site check is then satisfied by rewriting the
    Origin to the address the API sees);
  * only GET and HEAD reach the web server; request bodies are capped at 512 KB.
It trusts exactly one thing: the tunnel in front of it, which is the only program that can reach it (it listens on 127.0.0.1 only).
It is a convenience for showing synthetic data, not protection for real data (docs/production-readiness.md).

Environment: FO_GATE_PASSWORD (required), FO_GATE_PUBLIC_ORIGIN (for example https://abc.trycloudflare.com; if empty, an Origin must match the
Host header), FO_GATE_WEB (default http://127.0.0.1:5181), FO_GATE_API (default http://127.0.0.1:8100), FO_GATE_PORT (default 8200).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import html
import os
import secrets
import sys
import time
from collections import deque
from urllib.parse import parse_qs, urlparse

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route

MAX_BODY = 512 * 1024
MAX_WRONG_PER_MINUTE = 10
REALM = 'Basic realm="Family Office Intelligence demo (synthetic data only)"'
LOGIN_PATH = "/__gate"
COOKIE = "fo_gate"
COOKIE_HOURS = 12
PAGE_HEADERS = {
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    # Not "no-referrer": with it a browser sends "Origin: null" on the form's POST, and the same-site check refuses the password.
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
}
PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Family Office Intelligence</title>
<style>
  :root {{ color-scheme: light dark; --bg: #f6f5f2; --card: #fff; --ink: #1c1c1a; --muted: #5d5c57; --line: #d9d7d0; --accent: #1f4f46; --bad: #a23b2a; }}
  @media (prefers-color-scheme: dark) {{ :root {{ --bg: #141413; --card: #1d1d1b; --ink: #ecebe6; --muted: #a8a69f; --line: #34332f; --accent: #7fb8a9; --bad: #f08a76; }} }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px; background: var(--bg); color: var(--ink);
         font: 16px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ width: 100%; max-width: 380px; background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 28px 24px; }}
  h1 {{ font-size: 1.25rem; margin: 0 0 6px; }}
  p {{ margin: 0 0 18px; color: var(--muted); }}
  label {{ display: block; font-weight: 600; margin-bottom: 6px; }}
  input {{ width: 100%; font: inherit; padding: 10px 12px; border: 1px solid var(--line); border-radius: 8px; background: var(--bg); color: var(--ink); }}
  input:focus {{ outline: 2px solid var(--accent); outline-offset: 1px; }}
  button {{ width: 100%; margin-top: 14px; font: inherit; font-weight: 600; padding: 10px 12px; border: 0; border-radius: 8px;
           background: var(--accent); color: var(--card); cursor: pointer; }}
  .error {{ color: var(--bad); margin: 10px 0 0; }}
  small {{ display: block; margin-top: 18px; color: var(--muted); }}
</style></head>
<body><main>
  <h1>Family Office Intelligence</h1>
  <p>A demonstration with made-up families. Enter the password you were given.</p>
  <form method="post" action="{action}">
    <input type="hidden" name="next" value="{next}">
    <label for="password">Password</label>
    <input id="password" name="password" type="password" autocomplete="current-password" required autofocus>
    {error}
    <button type="submit">Open the demo</button>
  </form>
  <small>Illustrative simulation, not investment advice.</small>
</main></body></html>
"""


def _safe_next(value: str) -> str:
    """Where to go after the password: a path on this site only (never another site, never the password page itself)."""
    if not value.startswith("/") or value.startswith(("//", "/\\")) or value.startswith(LOGIN_PATH) or any(ord(c) < 32 for c in value):
        return "/"
    return value


def _login_page(next_path: str, error: str = "", status: int = 200) -> HTMLResponse:
    body = PAGE.format(
        action=LOGIN_PATH, next=html.escape(_safe_next(next_path), quote=True),
        error=f'<p class="error" role="alert">{html.escape(error)}</p>' if error else "",
    )
    return HTMLResponse(body, status, PAGE_HEADERS)
# Connection-level headers never travel through a proxy; Authorization carries the gate's password, so it must not reach the API either.
NOT_FORWARDED = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade",
    "host", "content-length", "authorization", "accept-encoding", "origin", "referer", "forwarded",
}
NOT_RETURNED = NOT_FORWARDED | {"content-encoding"}


def _client_address(request: Request) -> str:
    """The visitor's address as the tunnel reports it (a header the tunnel sets itself), else the peer."""
    forwarded = request.headers.get("cf-connecting-ip") or (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    return forwarded or (request.client.host if request.client else "unknown")


def create_gate(password: str, web_url: str, api_url: str, public_origin: str | None = None, client: httpx.AsyncClient | None = None) -> Starlette:
    if not password:
        raise ValueError("A password is required.")
    web_url, api_url = web_url.rstrip("/"), api_url.rstrip("/")
    api_host = urlparse(api_url).netloc
    wrong: deque[float] = deque()
    upstream = client or httpx.AsyncClient(timeout=120)
    key = secrets.token_bytes(32)  # signs the cookie; new on every start, so a restart signs everyone out
    secure = (public_origin or "").startswith("https://")

    def sign(expires: int) -> str:
        return hmac.new(key, f"{expires}".encode(), hashlib.sha256).hexdigest()

    def cookie_ok(request: Request) -> bool:
        value = request.cookies.get(COOKIE, "")
        expires, _, signature = value.partition(".")
        return expires.isdigit() and int(expires) > time.time() and hmac.compare_digest(signature, sign(int(expires)))

    def locked(now: float) -> bool:
        while wrong and now - wrong[0] > 60:
            wrong.popleft()
        return len(wrong) >= MAX_WRONG_PER_MINUTE

    async def login(request: Request) -> Response:
        """The password page: GET shows it, POST checks the password and sets the cookie."""
        if request.method == "GET":
            next_path = request.query_params.get("next", "/")
            return RedirectResponse(_safe_next(next_path), 303) if cookie_ok(request) else _login_page(next_path)
        if request.method != "POST":
            return PlainTextResponse("Not allowed.", 405, {"Allow": "GET, POST"})
        if not origin_ok(request):
            return PlainTextResponse("This request did not come from this site.", 403)
        body = await request.body()
        if len(body) > 4096:
            return PlainTextResponse("Request too large.", 413)
        fields = parse_qs(body.decode("utf-8", "replace"))
        next_path = (fields.get("next") or ["/"])[0]
        now = time.monotonic()
        if locked(now):
            return _login_page(next_path, "Too many wrong passwords. Wait a minute, then try again.", 429)
        given = (fields.get("password") or [""])[0]
        if not hmac.compare_digest(given.encode("utf-8"), password.encode("utf-8")):
            wrong.append(now)
            return _login_page(next_path, "That password is not right. Try again.", 401)
        expires = int(time.time()) + COOKIE_HOURS * 3600
        response = RedirectResponse(_safe_next(next_path), 303)
        response.set_cookie(COOKIE, f"{expires}.{sign(expires)}", max_age=COOKIE_HOURS * 3600, path="/", secure=secure, httponly=True, samesite="lax")
        return response

    def password_ok(request: Request) -> bool:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("basic "):
            return False
        try:
            given = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8").split(":", 1)[1]
        except (ValueError, IndexError, UnicodeDecodeError):
            return False
        return hmac.compare_digest(given.encode("utf-8"), password.encode("utf-8"))

    def origin_ok(request: Request) -> bool:
        origin = request.headers.get("origin")
        if not origin:
            return True
        if public_origin:
            return origin == public_origin
        return urlparse(origin).netloc == request.headers.get("host", "")

    async def handle(request: Request) -> Response:
        if request.url.path == LOGIN_PATH:
            return await login(request)
        now = time.monotonic()
        if locked(now):
            return PlainTextResponse("Too many wrong passwords. Wait a minute.", 429, {"Retry-After": "60"})
        if not (password_ok(request) or cookie_ok(request)):
            if request.headers.get("authorization"):  # a guess counts; a browser's first request, which carries nothing, must not lock out the visitor behind it
                wrong.append(now)
            if request.method in ("GET", "HEAD") and "text/html" in request.headers.get("accept", ""):
                # A browser opening a page: the password page, with no WWW-Authenticate, so no popup competes with it.
                return _login_page(request.url.path + (f"?{request.url.query}" if request.url.query else ""), status=401)
            return PlainTextResponse("Password needed.", 401, {"WWW-Authenticate": REALM})
        if not origin_ok(request):
            return PlainTextResponse("This request did not come from this site.", 403)

        path = request.url.path
        is_api = path == "/api" or path.startswith("/api/")
        if not is_api and request.method not in ("GET", "HEAD"):
            return PlainTextResponse("Not allowed.", 405, {"Allow": "GET, HEAD"})
        declared = request.headers.get("content-length", "0")
        if declared.isdigit() and int(declared) > MAX_BODY:
            return PlainTextResponse("Request too large.", 413)
        body = await request.body()
        if len(body) > MAX_BODY:
            return PlainTextResponse("Request too large.", 413)

        headers = {k: v for k, v in request.headers.items() if k.lower() not in NOT_FORWARDED and not k.lower().startswith(("x-forwarded-", "cf-", "x-real-ip"))}
        if "cookie" in headers:  # the gate's own cookie stays here, like the password
            kept = "; ".join(p.strip() for p in headers.pop("cookie").split(";") if p.strip() and not p.strip().startswith(f"{COOKIE}="))
            if kept:
                headers["cookie"] = kept
        if is_api:
            headers["x-forwarded-for"] = _client_address(request)
            headers["x-forwarded-proto"] = "https"  # the visitor is on https; the API then marks its cookie Secure
            if request.headers.get("origin"):
                headers["origin"] = f"https://{api_host}"  # what the API's own cross-site check expects for a request it sees as https
        target = (api_url if is_api else web_url) + path + (f"?{request.url.query}" if request.url.query else "")
        try:
            reply = await upstream.request(request.method, target, headers=headers, content=body or None)
        except httpx.HTTPError:
            return PlainTextResponse("The demo is not answering. Run demo\\start-demo.cmd again.", 502)

        response = Response(content=reply.content, status_code=reply.status_code)
        for name, value in reply.headers.multi_items():
            if name.lower() not in NOT_RETURNED:
                response.raw_headers.append((name.lower().encode("latin-1"), value.encode("latin-1")))
        response.headers["x-robots-tag"] = "noindex, nofollow"
        return response

    methods = ["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]
    return Starlette(routes=[Route("/{path:path}", handle, methods=methods)])


def main() -> int:
    password = os.environ.get("FO_GATE_PASSWORD", "")
    if not password:
        print("FO_GATE_PASSWORD is not set; the gate will not start.")
        return 2
    import uvicorn

    app = create_gate(
        password, os.environ.get("FO_GATE_WEB", "http://127.0.0.1:5181"), os.environ.get("FO_GATE_API", "http://127.0.0.1:8100"),
        os.environ.get("FO_GATE_PUBLIC_ORIGIN") or None,
    )
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("FO_GATE_PORT", "8200")), server_header=False, proxy_headers=False, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
