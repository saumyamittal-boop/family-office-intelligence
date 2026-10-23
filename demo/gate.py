"""A password gate and reverse proxy for sharing the demo through a tunnel.

    python demo/gate.py            (started for you by demo\\share-demo.cmd; settings come from environment variables)

Why it exists: the Streamlit version has an access code, the React version has none, so a public address would let anyone create accounts. This
puts HTTP Basic authentication (any user name, one shared password) in front of everything, then does what the reverse proxy in
docs/deployment-react.md does: it sends /api/* to the API and every other path to the web server, and tells the API the visitor's real address
(so the per-address rate limits count visitors, not the tunnel).

What it enforces itself:
  * the password, with a global limit of 10 wrong tries a minute;
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
import hmac
import os
import sys
import time
from collections import deque
from urllib.parse import urlparse

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

MAX_BODY = 512 * 1024
MAX_WRONG_PER_MINUTE = 10
REALM = 'Basic realm="Family Office Intelligence demo (synthetic data only)"'
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
        now = time.monotonic()
        while wrong and now - wrong[0] > 60:
            wrong.popleft()
        if len(wrong) >= MAX_WRONG_PER_MINUTE:
            return PlainTextResponse("Too many wrong passwords. Wait a minute.", 429, {"Retry-After": "60"})
        if not password_ok(request):
            if request.headers.get("authorization"):  # a guess counts; a browser's first request, which carries nothing, must not lock out the visitor behind it
                wrong.append(now)
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
