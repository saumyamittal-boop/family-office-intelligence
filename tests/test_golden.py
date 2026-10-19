"""The financial engine must keep producing exactly the numbers frozen in tests/golden/engine_golden.json.

New fields may appear in the live output (they are ignored); an existing number, text or assumption that
changes fails the test. If a model change has been explicitly approved, regenerate the file with
`python tools/make_golden.py` and record the approval in the changelog.
"""
import json
import math

import pytest

from tools.make_golden import GOLDEN_PATH, build_snapshot

TOLERANCE = 1e-9


def differences(expected, actual, path="$"):
    """Yield a readable line for every way `actual` departs from `expected` (extra keys in actual are fine)."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            yield f"{path}: expected an object, got {type(actual).__name__}"
            return
        for key, value in expected.items():
            if key not in actual:
                yield f"{path}.{key}: missing"
            else:
                yield from differences(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            yield f"{path}: expected a list of {len(expected)}, got {len(actual) if isinstance(actual, list) else type(actual).__name__}"
            return
        for i, (e, a) in enumerate(zip(expected, actual)):
            yield from differences(e, a, f"{path}[{i}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        if expected != actual:
            yield f"{path}: expected {expected!r}, got {actual!r}"
    elif isinstance(expected, (int, float)):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            yield f"{path}: expected a number, got {actual!r}"
        elif not math.isclose(expected, actual, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
            yield f"{path}: expected {expected!r}, got {actual!r}"


@pytest.fixture(scope="module")
def golden():
    return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def live():
    return build_snapshot()


def test_the_comparison_itself_catches_a_changed_number_and_ignores_new_fields():
    expected = {"a": [1.0, {"b": 2.0}], "c": "x"}
    assert list(differences(expected, {"a": [1.0, {"b": 2.0, "new": 9}], "c": "x", "d": 1})) == []
    assert any("$.a[1].b" in d for d in differences(expected, {"a": [1.0, {"b": 2.0000001}], "c": "x"}))
    assert any("missing" in d for d in differences(expected, {"a": [1.0, {"b": 2.0}]}))


def test_the_protected_assumptions_are_unchanged(golden, live):
    found = list(differences(golden["assumptions"], live["assumptions"]))
    assert not found, "A financial assumption changed without approval:\n" + "\n".join(found[:20])


def test_estimated_inputs_are_unchanged(golden, live):
    found = list(differences(golden["inputs"], live["inputs"]))
    assert not found, "\n".join(found[:20])


@pytest.mark.parametrize("family", ["A", "B", "C", "D"])
@pytest.mark.parametrize("basis", ["all", "strict"])
def test_every_family_analysis_is_unchanged(golden, live, family, basis):
    found = list(differences(golden["families"][family][basis], live["families"][family][basis]))
    assert not found, f"Family {family}, cover basis {basis} changed:\n" + "\n".join(found[:20])


@pytest.mark.parametrize("case", ["default_family", "family_with_commitments"])
def test_guided_strategies_are_unchanged(golden, live, case):
    found = list(differences(golden["guided"][case], live["guided"][case]))
    assert not found, f"Guided case {case} changed:\n" + "\n".join(found[:20])


def test_the_snapshot_covers_what_the_brief_says_must_be_protected(golden):
    a = golden["assumptions"]
    assert a["inflation"] == 0.045
    assert a["prior_returns"] == {
        "Large-cap equity": 0.11, "Mid-cap equity": 0.125, "Debt": 0.07, "Gold": 0.065, "Cash & liquid": 0.06,
    }
    assert a["haircuts"] == {
        "Cash & liquid": 0.0, "Debt": 0.08, "Gold": 0.15, "Large-cap equity": 0.3, "Mid-cap equity": 0.4,
    }
    assert {k: (v["max_dd"], v["target"]) for k, v in a["risk_choices"].items()} == {
        "Protect": (0.08, 0.02), "Balance": (0.15, 0.04), "Grow": (0.25, 0.06),
    }
