"""Serve the built web app (web/dist) on 127.0.0.1 with the production security headers. Started by deploy/cloud/run.py.

    python deploy/cloud/static_site.py 5181

On the laptop `vite preview` does this, but App Service's Python image has no Node, so this is the Python equivalent:
  * the same headers as web/security-headers.ts (tests/test_cloud_deploy.py checks they match);
  * any path that is not a file gets index.html, so the app's own page addresses work when typed or reloaded;
  * only GET and HEAD, and nothing outside web/dist.
"""
from __future__ import annotations

import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Route

DIST = Path(__file__).resolve().parents[2] / "web" / "dist"

CSP = "; ".join([
    "default-src 'self'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
])
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
}


def create_site(dist: Path = DIST) -> Starlette:
    root = dist.resolve()
    index = root / "index.html"

    async def serve(request: Request) -> Response:
        if request.method not in ("GET", "HEAD"):
            return PlainTextResponse("Not allowed.", 405, {"Allow": "GET, HEAD"})
        wanted = (root / request.path_params["path"]).resolve()
        if wanted.is_relative_to(root) and wanted.is_file():
            target, cache = wanted, ("public, max-age=31536000, immutable" if wanted.parent.name == "assets" else "no-cache")
        else:
            target, cache = index, "no-cache"
        return FileResponse(target, headers={**SECURITY_HEADERS, "Cache-Control": cache})

    return Starlette(routes=[Route("/{path:path}", serve, methods=["GET", "HEAD", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])])


app = create_site()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 5181, server_header=False, log_level="warning")
