"""Check that every number quoted in docs/demo-script-react.md is what the running application shows.

Run against a running API (the launcher does this for you):   python tools/demo_check.py
Another address:                                             python tools/demo_check.py --api http://127.0.0.1:8100
Just print the figures:                                       python tools/demo_check.py --print

It signs in as private, throwaway copies of the demo families (so nothing a visitor sees is touched), repeats the steps of the demo
script through the API, formats each figure exactly as the web app does, and reports any figure that the script does not contain.
tests/test_demo_script.py runs the same check on every test run, so the script cannot drift from the engine.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fo.formatting import cr, half_up, pct, signed_cr, signed_pct  # noqa: E402

SCRIPT = ROOT / "docs" / "demo-script-react.md"
STATEMENT = ROOT / "demo" / "family-statement.csv"
STATEMENT_NAME = "family-statement.csv"
AMBIGUOUS_LABEL = "Equity"


def times(value: float) -> str:
    return f"{half_up(value, 1)}x"


class _Session:
    """One private demo copy, signed in."""

    def __init__(self, client, family: str):
        reply = client.post("/api/auth/demo", json={"family": family})
        reply.raise_for_status()
        body = reply.json()
        self.client = client
        self.csrf = {"X-CSRF-Token": body["csrf_token"]}
        self.basis = body["default_basis"]
        profiles = client.get("/api/profiles")
        profiles.raise_for_status()
        self.profile_id = profiles.json()[0]["id"]

    def get(self, path: str, **params):
        reply = self.client.get(path, params=params or None)
        reply.raise_for_status()
        return reply.json()

    def post(self, path: str, body: dict):
        reply = self.client.post(path, json=body, headers=self.csrf)
        reply.raise_for_status()
        return reply.json()

    def analysis(self):
        return self.get(f"/api/profiles/{self.profile_id}/analysis", basis=self.basis)


def figures(make_client) -> list[tuple[str, str]]:
    """Every figure the demo script quotes, as (what it is, how the screen writes it). `make_client()` returns a fresh client (a fresh browser)."""
    out: list[tuple[str, str]] = []
    add = lambda label, text: out.append((label, text))  # noqa: E731

    # ---- Story 1: a family with no idea what to do (the guided plan, on its starting answers) ----
    s1 = _Session(make_client(), "legacy")
    config = s1.client.get("/api/plan/config").json()
    d = config["defaults"]
    answers = {"name": d["name"], "wealth": d["wealth"], "spending": d["spending"], "risk": d["risk"], "months": d["months"], "commitments": [], "amounts": None}
    add("story 1: wealth", cr(d["wealth"], 0))
    add("story 1: spending", cr(d["spending"], 0))
    goal = {c["key"]: c["target_real_return"] for c in config["comfort"]}
    plan = s1.post("/api/plan/strategies", answers)
    by = {x["letter"]: x for x in plan["strategies"]}
    a, b, c = by["A"], by["B"], by["C"]
    add("A worst year", signed_pct(a["year_range"]["worst"]))
    add("B typical year", f"{signed_pct(b['year_range']['low'])} to {signed_pct(b['year_range']['high'])}")
    add("B worst year", signed_pct(b["year_range"]["worst"]))
    add("B severe crash", signed_cr(b["crash"]["value_change_cr"]))
    add("B real return", f"{pct(b['portfolio']['exp_real'])} after inflation")
    add("B return goal", "Meets your return goal: " + ("Yes" if b["meets_goal_of"][b["key"]] else "Not quite"))
    add("B goal", f"{pct(goal[b['key']], 0)}")
    add("C expected return", pct(c["portfolio"]["exp_return"]))
    add("C worst year", signed_pct(c["year_range"]["worst"]))
    add("C comfort", "Within your comfort" if c["within_comfort_of"][b["key"]] else "Beyond your comfort")
    rows = {r["asset_class"]: r["change_cr"] for r in b["action_plan"]}
    trade = lambda change: f"{'Buy' if change >= 0 else 'Sell'} {cr(abs(change), 1)}"  # noqa: E731  (the screen says "Sell ₹15.6 Cr", not "−₹15.6 Cr")
    add("B large-cap", trade(rows["Large-cap equity"]))
    add("B mid-cap", trade(rows["Mid-cap equity"]))
    add("B debt", trade(rows["Debt"]))
    add("severe crash label", plan["crash"]["label"])

    # ---- Story 2: the 1,000 crore family with a liquidity gap ----
    s2 = _Session(make_client(), "gap")
    profile = s2.get(f"/api/profiles/{s2.profile_id}")
    analysis = s2.analysis()
    cur = analysis["current"]
    add("gap: corpus", cr(profile["corpus_cr"], 0))
    add("gap: counted liquid assets", cr(cur["available_cover_cr"], 0))
    add("gap: needed", cr(cur["required_cover_cr"], 0))
    add("gap: cover", times(cur["available_cover_cr"] / cur["required_cover_cr"]))
    add("gap: worst drawdown in the history", pct(cur["max_dd"]))
    add("gap: drawdown limit", pct(profile["max_drawdown"], 0))
    table = {row["option"]: row for row in analysis["comparison"]}
    add("scenario", analysis["comparison_scenario"])
    add("current loses", f"{signed_cr(table['Current']['value_change_cr'])}, {signed_pct(table['Current']['value_change'])}")
    for name in ("Growth", "Balanced", "Defensive"):
        add(f"{name} loses", signed_cr(table[name]["value_change_cr"]))
    add("current cover after", times(table["Current"]["cover_ratio_after"]))
    add("warning in the comparison", next(n["body"] for n in analysis["comparison_insights"] if n["tone"] == "warn"))
    reply = s2.post(f"/api/profiles/{s2.profile_id}/explain", {"intent": "liquidity_enough", "slots": {}, "basis": s2.basis})
    add("assistant: Is my liquidity enough?", reply["answer"]["lead"])

    # ---- Story 3 (React only): import a statement ----
    s3 = _Session(make_client(), "gap")
    data = base64.b64encode(STATEMENT.read_bytes()).decode()
    file = {"filename": STATEMENT_NAME, "content_base64": data}
    preview = s3.post(f"/api/profiles/{s3.profile_id}/holdings/preview", file)
    add("statement: rows read", f"{preview['rows_read']} rows")
    add("statement: problems", f"{len([p for p in preview['problems'] if p['severity'] == 'error'])} problem to fix")
    add("statement: unknown label", preview["unrecognised"][0]["label"])
    s3.post(f"/api/profiles/{s3.profile_id}/holdings/imports", {**file, "class_overrides": {AMBIGUOUS_LABEL: "Large-cap equity"}})
    cons = s3.get(f"/api/profiles/{s3.profile_id}/holdings/consolidation")
    add("statement: total", cr(cons["total_cr"], 1))
    share = {row["asset_class"]: row["share"] for row in cons["by_class"]}
    add("statement: large-cap share", pct(share["Large-cap equity"]))
    add("statement: illiquid share", pct(share["Illiquid"]))
    apply = s3.post(f"/api/profiles/{s3.profile_id}/holdings/apply/preview", {"set_corpus": False})
    add("profile before: large-cap", pct(apply["before"]["shares"]["Large-cap equity"]))
    add("profile after: large-cap", pct(apply["after"]["shares"]["Large-cap equity"]))
    s3.post(f"/api/profiles/{s3.profile_id}/holdings/apply", {"set_corpus": False})
    after = s3.analysis()["current"]
    add("after applying: counted liquid assets", cr(after["available_cover_cr"], 0))
    add("after applying: cover", times(after["available_cover_cr"] / after["required_cover_cr"]))
    add("after applying: worst drawdown in the history", pct(after["max_dd"]))
    return out


def missing(found: list[tuple[str, str]], script_text: str) -> list[tuple[str, str]]:
    return [(label, text) for label, text in found if text not in script_text]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://127.0.0.1:8100", help="address of the running API")
    parser.add_argument("--print", action="store_true", help="print the figures and stop")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except (AttributeError, ValueError):
        pass
    import httpx

    try:
        found = figures(lambda: httpx.Client(base_url=args.api, timeout=60))
    except (httpx.HTTPError, KeyError) as err:
        print(f"Could not read the figures from {args.api}: {type(err).__name__}. Is the API running (demo\\start-demo.cmd)?")
        return 2
    if args.print:
        for label, text in found:
            print(f"{label:46s} {text}")
        return 0
    script = SCRIPT.read_text(encoding="utf-8")
    absent = missing(found, script)
    for label, text in found:
        print(f"  {'MISSING' if (label, text) in absent else 'ok     '}  {label:46s} {text}")
    print(f"\n{len(found) - len(absent)} of {len(found)} figures in docs/demo-script-react.md match the running application.")
    return 1 if absent else 0


if __name__ == "__main__":
    raise SystemExit(main())
