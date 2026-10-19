"""Record which profile forms the SERVER accepts, so the React editor's own checks can be tested against it.

Run from the project root:  python tools/make_profile_vectors.py

Each case is a form in the editor's units (percent, years, rupees crore). `valid` is what the real API model and the shared
Python rules (fo.profile_form) decide for it. web/src/profile/vectors.test.ts requires the editor to reach the same verdict
on every case, including the edges (99.5% and 100.5% of holdings, a limit of exactly 100%, a one-off in the last year).
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pydantic import ValidationError  # noqa: E402

from api import convert  # noqa: E402
from api import schemas as s  # noqa: E402

VECTORS_PATH = ROOT / "web" / "src" / "test" / "profile_vectors.json"

CLASSES = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid"]

BASE = {
    "name": "Vector family", "constraint": "", "corpus": 100, "spending": 3, "horizon": 15, "maxDrawdown": 15, "coverMonths": 24,
    "target": 4,
    "holdings": {"Large-cap equity": 20, "Mid-cap equity": 10, "Debt": 30, "Gold": 5, "Cash & liquid": 10, "Illiquid": 25},
    "illiquid": {"description": "Real estate", "expectedReturn": 8, "volatility": 12, "lockIn": 2, "corr": 0.2},
    "oneOffs": [{"year": 3, "amount": 5}],
    "limits": {
        "Large-cap equity": {"min": 5, "max": 40}, "Mid-cap equity": {"min": 0, "max": 20}, "Debt": {"min": 10, "max": 60},
        "Gold": {"min": 0, "max": 15}, "Cash & liquid": {"min": 5, "max": 30},
    },
}


def frac(percent: float) -> float:
    return round(percent / 100, 10)  # the editor does Number((p / 100).toFixed(10))


def to_body(case: dict) -> dict:
    ill = case["illiquid"]
    return {
        "name": case["name"], "deciding_constraint": case["constraint"], "corpus_cr": case["corpus"],
        "annual_spending_cr": case["spending"], "horizon_years": case["horizon"], "max_drawdown": frac(case["maxDrawdown"]),
        "cover_months": case["coverMonths"], "target_real_return": frac(case["target"]),
        "holdings": {k: frac(v) for k, v in case["holdings"].items()},
        "illiquid": {"description": ill["description"], "expected_return": frac(ill["expectedReturn"]), "volatility": frac(ill["volatility"]),
                     "lock_in_years": ill["lockIn"], "corr_with_equity": ill["corr"]},
        "one_offs": [{"year": o["year"], "amount_cr": o["amount"]} for o in case["oneOffs"]],
        "limits": {k: {"min": frac(v["min"]), "max": frac(v["max"])} for k, v in case["limits"].items()},
    }


def server_accepts(case: dict) -> bool:
    try:
        model = s.ProfileIn(**to_body(case))
    except ValidationError:
        return False
    _, problems = convert.to_domain(model, key="vector")
    return not problems


def variant(**changes) -> dict:
    out = copy.deepcopy(BASE)
    for path, value in changes.items():
        target = out
        *parents, last = path.split("__")
        for p in parents:
            target = target[p]
        target[last] = value
    return out


def holdings(**shares) -> dict:
    out = copy.deepcopy(BASE)
    out["holdings"] = {**BASE["holdings"], **{k.replace("_", " ").replace(" and ", " & "): v for k, v in shares.items()}}
    return out


def cases() -> list[tuple[str, dict]]:
    c: list[tuple[str, dict]] = [("base", copy.deepcopy(BASE))]
    scalars = {
        "corpus": [0.99, 1, 1_000_000, 1_000_001, 0, -5], "spending": [-0.1, 0, 100_000, 100_001], "horizon": [0, 1, 60, 61, 1.5, 15.0],
        "maxDrawdown": [0.9, 1, 80, 80.1], "coverMonths": [0, 1, 240, 241, 2.5], "target": [-5.1, -5, 25, 25.1, 0],
    }
    for key, values in scalars.items():
        for v in values:
            case = variant(**{key: v})
            if key == "horizon" and isinstance(v, (int, float)) and v < 3:
                case["oneOffs"] = []  # keep the base one-off from being the reason
            c.append((f"{key}={v}", case))
    c += [
        ("name empty", variant(name="")), ("name spaces", variant(name="   ")), ("name 60", variant(name="x" * 60)), ("name 61", variant(name="x" * 61)),
        ("ill description empty", variant(illiquid__description="")),
    ]
    for k, vs in {"expectedReturn": [-10.1, -10, 40, 40.1], "volatility": [-0.1, 0, 80, 80.1], "lockIn": [-1, 0, 30, 31, 1.5], "corr": [-0.01, 0, 1, 1.01]}.items():
        for v in vs:
            ill = copy.deepcopy(BASE["illiquid"])
            ill[k] = v
            c.append((f"illiquid.{k}={v}", variant(illiquid=ill)))

    # Holdings that need to add up to 100% (within half a point), the illiquid ceiling, and negative or oversized shares.
    for debt in (29, 29.4, 29.5, 29.6, 30, 30.4, 30.5, 30.6, 31, 20, 40):
        c.append((f"holdings debt={debt}", holdings(Debt=debt)))
    for total_shift in (0.49, 0.5, 0.51, -0.49, -0.5, -0.51):
        c.append((f"holdings shift {total_shift}", holdings(Gold=5 + total_shift)))
    c.append(("holdings illiquid 95", holdings(Large_cap_equity=0, Mid_cap_equity=0, Debt=0, Gold=0, Cash_and_liquid=5, Illiquid=95)))
    c.append(("holdings illiquid 95.5", holdings(Large_cap_equity=0, Mid_cap_equity=0, Debt=0, Gold=0, Cash_and_liquid=4.5, Illiquid=95.5)))
    c.append(("holdings illiquid 100", holdings(Large_cap_equity=0, Mid_cap_equity=0, Debt=0, Gold=0, Cash_and_liquid=0, Illiquid=100)))
    c.append(("holdings negative", holdings(Gold=-5, Debt=40)))
    c.append(("holdings over 100", holdings(Gold=101)))

    # Limits
    for name in CLASSES:
        for lo, hi in ((0, 100), (30, 20), (-1, 20), (0, 101), (10, 10)):
            lim = copy.deepcopy(BASE["limits"])
            lim[name] = {"min": lo, "max": hi}
            c.append((f"limit {name} {lo}-{hi}", variant(limits=lim)))
    all_zero_max = {n: {"min": 0, "max": 10} for n in CLASSES}  # maximums total 50%: cannot reach 100%
    all_big_min = {n: {"min": 25, "max": 100} for n in CLASSES}  # minimums total 125%
    exact_min = {n: {"min": 20, "max": 100} for n in CLASSES}  # minimums total exactly 100%
    exact_max = {n: {"min": 0, "max": 20} for n in CLASSES}  # maximums total exactly 100%
    for label, lim in (("max total 50", all_zero_max), ("min total 125", all_big_min), ("min total 100", exact_min), ("max total 100", exact_max)):
        c.append((f"limits {label}", variant(limits=lim)))

    # One-off outflows
    for label, rows in {
        "none": [], "year 0": [{"year": 0, "amount": 5}], "last year": [{"year": 15, "amount": 5}], "past horizon": [{"year": 16, "amount": 5}],
        "amount 0": [{"year": 3, "amount": 0}], "amount negative": [{"year": 3, "amount": -1}], "tiny amount": [{"year": 3, "amount": 0.01}],
        "three": [{"year": 1, "amount": 1}, {"year": 2, "amount": 2}, {"year": 3, "amount": 3}],
        "four": [{"year": 1, "amount": 1}, {"year": 2, "amount": 2}, {"year": 3, "amount": 3}, {"year": 4, "amount": 4}],
        "fractional year": [{"year": 2.5, "amount": 5}], "same year twice": [{"year": 3, "amount": 5}, {"year": 3, "amount": 6}],
    }.items():
        c.append((f"one-offs {label}", variant(oneOffs=rows)))
    return c


def build() -> dict:
    out = []
    for label, form in cases():
        out.append({"label": label, "form": form, "valid": server_accepts(form)})
    return {"cases": out}


def main() -> None:
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    data = build()["cases"]
    print(f"Wrote {VECTORS_PATH}: {len(data)} cases, {sum(c['valid'] for c in data)} accepted by the server")


if __name__ == "__main__":
    main()
