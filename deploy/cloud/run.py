"""Start the shared demo on a hosting service (Render, or Azure App Service): the API, the built web app and the password gate, in one container.

    python deploy/cloud/run.py            (the start command; see deploy/cloud/README.md)

It does on the host what demo\\share-demo.cmd does on the laptop, with the same settings and the same gate (demo/gate.py), minus the tunnel:
  * the API on 127.0.0.1:8100, with a fresh demo database in /tmp (wiped whenever the app restarts, like the laptop demo's);
  * the built web app (web/dist) on 127.0.0.1:5181, by deploy/cloud/static_site.py, with the production security headers;
  * the gate on the port the host gives the container ($PORT), the only thing the host's front end can reach.

What differs from the laptop: the visitor's address. On the laptop the tunnel sets CF-Connecting-IP; here the host's front end appends the
visitor's address (on Azure with a port) to X-Forwarded-For. A visitor can send either header themselves, so before the gate sees a request,
`_proxy_client_address` drops CF-Connecting-IP and X-Real-IP and keeps only the LAST X-Forwarded-For entry, the one the host added. The API's
per-address limits then count visitors, not the host.

If the API or the web server stops, this exits, and the host restarts the container.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
API_PORT = int(os.environ.get("FO_CLOUD_API_PORT") or 8100)  # changeable only so a local test can run beside the laptop demo
WEB_PORT = int(os.environ.get("FO_CLOUD_WEB_PORT") or 5181)
STATE = Path(os.environ.get("FO_DEMO_STATE", "/tmp/fo-demo"))

# The laptop demo's shared settings (demo/start-demo.ps1 with -Shared). Anything set in the host's environment variables wins.
DEFAULTS = {
    "FO_API_COOKIE_SECURE": "1",
    "FO_API_DOCS": "0",
    "FO_MAX_ACCOUNTS": "20",
    "FO_API_CORS_ORIGINS": f"http://127.0.0.1:{WEB_PORT},http://localhost:{WEB_PORT}",
}


def _proxy_client_address(app):
    """ASGI wrapper: leave the gate exactly one trustworthy address header (see the module docstring)."""

    async def wrapped(scope, receive, send):
        if scope["type"] == "http":
            headers = [(k, v) for k, v in scope["headers"] if k not in (b"cf-connecting-ip", b"x-real-ip", b"x-forwarded-for")]
            chain = b",".join(v for k, v in scope["headers"] if k == b"x-forwarded-for").decode("latin-1")
            last = chain.split(",")[-1].strip() if chain else ""
            if last.startswith("["):  # [IPv6]:port
                last = last[1:].split("]", 1)[0]
            elif last.count(":") == 1:  # IPv4:port
                last = last.split(":", 1)[0]
            if last:
                headers.append((b"x-forwarded-for", last.encode("latin-1")))
            scope = dict(scope, headers=headers)
        await app(scope, receive, send)

    return wrapped


def _start(name: str, args: list[str], env: dict[str, str]) -> subprocess.Popen:
    log = open(STATE / f"{name}.log", "ab")  # noqa: SIM115 - stays open for the child's lifetime
    return subprocess.Popen([sys.executable, "-B", *args], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)


def _wait(url: str, seconds: float) -> bool:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5):
                return True
        except OSError:
            time.sleep(1)
    return False


def _watch(children: dict[str, subprocess.Popen]) -> None:
    while True:
        for name, child in children.items():
            if child.poll() is not None:
                print(f"The {name} stopped (exit code {child.returncode}); see {STATE / (name + '.log')}. Exiting so the host restarts it.", flush=True)
                os._exit(1)
        time.sleep(5)


def main() -> int:
    password = os.environ.get("FO_GATE_PASSWORD", "")
    if not password:
        print("FO_GATE_PASSWORD is not set (the host's environment variables); not starting.", flush=True)
        return 2

    shutil.rmtree(STATE, ignore_errors=True)  # a fresh demo database on every start
    STATE.mkdir(parents=True)
    env = {**DEFAULTS, **os.environ, "FO_DB_PATH": str(STATE / "demo.db")}
    env.pop("FO_GATE_PASSWORD")  # only the gate needs it

    children = {
        "api": _start("api", ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", str(API_PORT), "--no-server-header"], env),
        "web": _start("web", [str(Path(__file__).with_name("static_site.py")), str(WEB_PORT)], env),
    }
    threading.Thread(target=_watch, args=(children,), daemon=True).start()
    if not _wait(f"http://127.0.0.1:{API_PORT}/api/health", 300):
        print(f"The API did not answer within 5 minutes; see {STATE / 'api.log'}.", flush=True)
        return 1

    sys.path.insert(0, str(ROOT / "demo"))
    import uvicorn
    from gate import create_gate

    # Set by the host: Render (fo-demo.onrender.com) or Azure App Service (fo-demo.azurewebsites.net).
    host_name = os.environ.get("RENDER_EXTERNAL_HOSTNAME") or os.environ.get("WEBSITE_HOSTNAME") or ""
    public_origin = os.environ.get("FO_GATE_PUBLIC_ORIGIN") or (f"https://{host_name}" if host_name else None)
    gate = create_gate(password, f"http://127.0.0.1:{WEB_PORT}", f"http://127.0.0.1:{API_PORT}", public_origin)
    port = int(os.environ.get("PORT") or os.environ.get("WEBSITES_PORT") or 8000)
    print(f"Serving on port {port} for {public_origin or 'any host'}.", flush=True)
    uvicorn.run(_proxy_client_address(gate), host="0.0.0.0", port=port, server_header=False, proxy_headers=False, log_level="warning")
    return 0


if __name__ == "__main__":
    sys.exit(main())
