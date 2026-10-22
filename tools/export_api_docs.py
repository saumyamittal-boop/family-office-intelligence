"""Write docs/api.md, the API reference, from the running application.

Run from the project root:  python tools/export_api_docs.py

The operations, their paths, request and response shapes and who may call them are read from the application itself (the same
source as web/src/api/openapi.json), so the page cannot drift from the code: tests/test_api_docs.py fails when the committed file
no longer matches. Two things the application does not declare are written below and checked by that test: a one-line purpose for
every operation, and which rate limit an operation counts against.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from api import deps, sessions  # noqa: E402
from api.config import Settings  # noqa: E402
from api.main import _throttles, create_app  # noqa: E402
from tools.export_openapi import current_contract  # noqa: E402

DOC_PATH = ROOT / "docs" / "api.md"

PURPOSE: dict[str, str] = {
    "GET /api/health": "Liveness check; also opens the database once, so it fails if the database cannot be reached.",
    "GET /api/meta": "Service facts: version, data source (sample or snapshot), disclaimer, asset classes, demo families, scenario presets and custom-scenario ranges.",
    "POST /api/auth/login": "Sign in with username and password. Starts a new server-side session and sets the session cookie.",
    "POST /api/auth/signup": "Create an account and sign it in.",
    "POST /api/auth/demo": "Start a private, throwaway copy of one demo family. Answers 404 when demo sign-in is switched off.",
    "GET /api/auth/me": "Who is signed in; returns a fresh CSRF token for the current session.",
    "POST /api/auth/logout": "End the session and clear the cookie.",
    "GET /api/profiles": "The signed-in account's family profiles (id, name, corpus).",
    "POST /api/profiles": "Create a profile. Validated with the same rules as the Streamlit form; 409 once the per-account limit is reached.",
    "GET /api/profiles/{profile_id}": "One profile in full.",
    "PUT /api/profiles/{profile_id}": "Replace a profile. Validated; 404 if it is not this account's.",
    "DELETE /api/profiles/{profile_id}": "Delete a profile and its holdings imports. 409 for the last profile: an account always keeps one.",
    "GET /api/profiles/{profile_id}/analysis": "Run the allocation model for this profile: current mix, three recommendations, risk and liquidity figures, action plan, insights.",
    "GET /api/profiles/{profile_id}/history": "Replay the sample years for the current mix and each recommendation (drawdown history).",
    "POST /api/profiles/{profile_id}/scenarios": "Stress the current mix and each recommendation with a built-in scenario or the six custom dials.",
    "GET /api/plan/config": "The guided plan's questions, choices and bounds. Holds nobody's data.",
    "POST /api/plan/preview": "Instant read-out of what the answers so far mean. No optimiser, so safe to call as someone types.",
    "POST /api/plan/strategies": "Run the allocation model on the guided-plan answers and return Strategy A, B and C.",
    "POST /api/plan/save": "Save the guided-plan answers as a new profile (answers 201) or into an existing one (answers 200).",
    "GET /api/dashboard": "The account's chosen dashboard modules, in order (default four if none chosen).",
    "PUT /api/dashboard": "Choose and order the dashboard modules.",
    "DELETE /api/dashboard": "Back to the default four modules.",
    "GET /api/holdings/template": "A small, valid example import file. Holds nobody's data.",
    "POST /api/profiles/{profile_id}/holdings/preview": "Read a CSV or Excel file and report what it holds and what is wrong. Stores nothing.",
    "POST /api/profiles/{profile_id}/holdings/imports": "Read the file again and, if nothing blocks it, store it as an import. 409 for a duplicate of an earlier import.",
    "GET /api/profiles/{profile_id}/holdings/imports": "The imports stored for this profile.",
    "DELETE /api/profiles/{profile_id}/holdings/imports/{import_id}": "Delete one stored import and its lines.",
    "GET /api/profiles/{profile_id}/holdings/consolidation": "All imported lines for the profile, totalled by asset class and by account.",
    "POST /api/profiles/{profile_id}/holdings/apply/preview": "What the profile would look like if the imported holdings were used. Changes nothing.",
    "POST /api/profiles/{profile_id}/holdings/apply": "Make the profile's holdings the imported ones. Only this call ever changes the profile from an import.",
    "GET /api/explain/catalog": "The questions the Assistant can answer, grouped, with the parameters each takes. Holds nobody's data.",
    "POST /api/profiles/{profile_id}/explain": "Answer a question about this family's results from the engine's own figures. The question is not stored or logged.",
}

# Operations that count against a rate limit, and the limit's name (limits themselves are read from api/main.py).
LIMITS: dict[str, tuple[str, ...]] = {
    "POST /api/auth/login": ("login_user", "login_ip"),
    "POST /api/auth/signup": ("signup_ip",),
    "POST /api/auth/demo": ("demo_ip",),
    "GET /api/profiles/{profile_id}/analysis": ("analysis_user",),
    "GET /api/profiles/{profile_id}/history": ("analysis_user",),
    "POST /api/profiles/{profile_id}/scenarios": ("scenarios_user",),
    "POST /api/plan/strategies": ("plan_user",),
    "POST /api/profiles/{profile_id}/holdings/preview": ("holdings_user",),
    "POST /api/profiles/{profile_id}/holdings/imports": ("holdings_user",),
    "POST /api/profiles/{profile_id}/explain": ("explain_user",),
}

LIMIT_APPLIES = {
    "login_user": "per username, counted on failed sign-ins",
    "login_ip": "per client address, counted on failed sign-ins",
    "signup_ip": "per client address, every attempt",
    "demo_ip": "per client address, every attempt",
    "plan_user": "per signed-in account",
    "holdings_user": "per signed-in account",
    "explain_user": "per signed-in account",
    "analysis_user": "per signed-in account",
    "scenarios_user": "per signed-in account",
}

TAG_ORDER = ["meta", "auth", "profiles", "plan", "dashboard", "holdings", "explain"]
TAG_TITLE = {
    "meta": "Service", "auth": "Sign-in", "profiles": "Profiles and results", "plan": "Guided plan",
    "dashboard": "Dashboard", "holdings": "Holdings import", "explain": "Assistant",
}
METHOD_ORDER = {"GET": 0, "POST": 1, "PUT": 2, "DELETE": 3}


def _calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _calls(dep)


def operations(app):
    """Every route that serves the API, whichever way this FastAPI release stores included routers (plain routes or lazy groups)."""
    for r in app.routes:
        if isinstance(r, APIRoute):
            yield r
        elif hasattr(r, "effective_route_contexts"):
            yield from r.effective_route_contexts()


def _access(route) -> str:
    calls = set(_calls(route.dependant))
    if deps.user_with_csrf in calls:
        return "Signed in + CSRF token"
    if deps.current_user in calls:
        return "Signed in"
    return "Public"


def _ref(schema: dict | None) -> str:
    if not schema:
        return ""
    if "$ref" in schema:
        return schema["$ref"].rsplit("/", 1)[-1]
    if schema.get("type") == "array" and "items" in schema:
        return f"list of {_ref(schema['items'])}"
    return schema.get("type", "")


def _body(op: dict) -> str:
    content = (op.get("requestBody") or {}).get("content", {}).get("application/json", {})
    return _ref(content.get("schema")) or "none"


def _success(op: dict) -> str:
    for code in sorted(op["responses"]):
        if code.startswith("2"):
            content = op["responses"][code].get("content", {}).get("application/json", {})
            shape = _ref(content.get("schema")) or ("no body" if code == "204" else "JSON object")
            return f"{code} {shape}"
    return ""


def _query(op: dict) -> str:
    found = []
    for p in op.get("parameters", []):
        if p["in"] == "query":
            allowed = p["schema"].get("enum")
            found.append(f"`{p['name']}`" + (f" ({' / '.join(allowed)})" if allowed else ""))
    return ", ".join(found) or "none"


def _fmt_window(seconds: float) -> str:
    if seconds % 3600 == 0:
        h = int(seconds // 3600)
        return "1 hour" if h == 1 else f"{h} hours"
    if seconds % 60 == 0:
        m = int(seconds // 60)
        return "1 minute" if m == 1 else f"{m} minutes"
    return f"{seconds:g} s"


def render() -> str:
    spec = json.loads(current_contract())
    app = create_app(Settings(docs=True))
    routes: dict = {}
    for r in operations(app):
        for m in r.methods - {"HEAD", "OPTIONS"}:
            routes[f"{m} {r.path}"] = r
    missing = sorted(set(routes) - set(PURPOSE))
    stale = sorted(set(PURPOSE) - set(routes))
    if missing or stale:
        raise SystemExit(f"tools/export_api_docs.py PURPOSE is out of step with the API. Add: {missing}  Remove: {stale}")

    throttles = _throttles()
    unknown = sorted({n for names in LIMITS.values() for n in names} - set(throttles))
    if unknown or set(LIMIT_APPLIES) != set(throttles):
        raise SystemExit(f"tools/export_api_docs.py LIMITS / LIMIT_APPLIES are out of step with api/main.py::_throttles: {unknown}")

    out: list[str] = []
    w = out.append
    w("# API reference")
    w("")
    w("<!-- Generated by tools/export_api_docs.py from the running application. Do not edit by hand: "
      "run `python tools/export_api_docs.py`. tests/test_api_docs.py fails when this file is stale. -->")
    w("")
    w(f"{len(routes)} operations. Everything is JSON over HTTP under `/api`. The machine-readable contract is "
      "[`web/src/api/openapi.json`](../web/src/api/openapi.json) (the web app's TypeScript types are generated from it). "
      "With the API running, `/docs` serves an interactive version while `FO_API_DOCS` is not `0`.")
    w("")
    w("All figures come from the synthetic-data engine. The API describes an illustrative simulation, not investment advice.")
    w("")
    w("## How to call it")
    w("")
    w(f"- **Sign-in.** `POST /api/auth/login` (or `signup`, or `demo`) sets an `HttpOnly`, `SameSite=Lax` cookie named `{sessions.COOKIE}`. "
      "Only a hash of its value is stored on the server. The cookie is also `Secure` over HTTPS or when `FO_API_COOKIE_SECURE=1`.")
    w(f"- **CSRF token.** The sign-in response and `GET /api/auth/me` return `csrf_token`. Send it as the `{sessions.CSRF_HEADER}` header on every "
      "operation marked *+ CSRF token* (all state-changing calls and the calls that run the model on posted data). A missing or wrong token gets 403.")
    w("- **Origin.** A `POST`, `PUT` or `DELETE` carrying an `Origin` header that is neither on the allowlist (`FO_API_CORS_ORIGINS`) nor the "
      "server's own origin gets 403.")
    w("- **Bodies.** Request bodies must be `application/json` (else 415) and at most `FO_API_MAX_BODY_KB` (default 256 KB, else 413). "
      "A holdings file travels inside that JSON body.")
    w("- **Errors.** Every error has the same shape, `{\"detail\": \"…\", \"problems\": [\"…\"] | null}`. The text never repeats what you submitted. "
      "Unexpected failures are a generic 500.")
    w("")
    w("| Status | Meaning |")
    w("|---|---|")
    for code, text in [
        ("401", "Not signed in, or wrong username or password."),
        ("403", "CSRF token missing or wrong, or the `Origin` is not allowed."),
        ("404", "Not found. A profile that belongs to another account answers exactly like one that does not exist."),
        ("409", "Conflict: profile limit reached, the last profile cannot be deleted, an identical import already exists, or holdings are applied before any are imported."),
        ("413 / 415", "Request body too large, or not JSON."),
        ("422", "The request was not valid; `problems` lists field names and rules, never the submitted values."),
        ("429", "Rate limit reached; the `Retry-After` header says how many seconds to wait."),
        ("503", "The allocation model is busy (it is one shared thread); retry after the `Retry-After` header."),
    ]:
        w(f"| {code} | {text} |")
    w("")
    w("## Operations")
    w("")
    w("Access: **Public** needs nothing; **Signed in** needs the session cookie; **Signed in + CSRF token** also needs the CSRF header.")
    w("")
    by_tag: dict[str, list[tuple[str, object]]] = {}
    for key, route in routes.items():
        by_tag.setdefault(route.tags[0], []).append((key, route))
    assert set(by_tag) <= set(TAG_ORDER), f"new tag: {sorted(set(by_tag) - set(TAG_ORDER))}"
    for tag in TAG_ORDER:
        rows = sorted(by_tag.get(tag, []), key=lambda kr: (kr[1].path, METHOD_ORDER[kr[0].split()[0]]))
        if not rows:
            continue
        w(f"### {TAG_TITLE[tag]}")
        w("")
        w("| Operation | Access | What it does | Request body | Query | Success | Rate limit |")
        w("|---|---|---|---|---|---|---|")
        for key, route in rows:
            method, path = key.split(" ", 1)
            op = spec["paths"][path][method.lower()]
            limit = ", ".join(f"`{n}`" for n in LIMITS.get(key, ())) or "none"
            w(f"| `{method} {path}` | {_access(route)} | {PURPOSE[key]} | {_body(op)} | {_query(op)} | {_success(op)} | {limit} |")
        w("")
    w("## Rate limits")
    w("")
    w("Counted in memory, per server process, so a restart clears them and several processes each keep their own count (see "
      "[the production checklist](production-readiness.md)). Behind a reverse proxy every visitor shares the proxy's address unless the proxy is configured "
      "to pass the real one on; the per-address limits are only meaningful when that is done.")
    w("")
    w("| Name | Limit | Applies |")
    w("|---|---|---|")
    for name, t in throttles.items():
        w(f"| `{name}` | {t.max_failures} per {_fmt_window(t.window)} | {LIMIT_APPLIES[name]} |")
    w("")
    w("## Response shapes")
    w("")
    w("The shape names above (for example `AnalysisOut`) are defined in `api/schemas.py`, `api/plan_schemas.py`, `api/holdings_schemas.py` and "
      "`api/explain_schemas.py`, and listed field by field in `web/src/api/openapi.json` under `components.schemas`.")
    w("")
    return "\n".join(out)


def main() -> None:
    DOC_PATH.write_text(render(), encoding="utf-8", newline="\n")
    print(f"Wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
