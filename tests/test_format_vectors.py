"""The TypeScript formatter is checked against numbers recorded from the Python one; keep that record honest."""
import json

from tools.make_format_vectors import VECTORS_PATH, build


def test_the_recorded_formatter_vectors_match_what_the_python_formatter_prints_today():
    recorded = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert recorded == json.loads(json.dumps(build())), (
        "fo/ui.py formatting changed. Run: python tools/make_format_vectors.py  and re-run the web tests."
    )


def test_the_vectors_include_the_awkward_ties_that_caused_real_bugs():
    recorded = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    pct = {(e["value"], e["digits"]): e["expected"] for e in recorded["pct"]}
    assert pct[(0.1375, 1)] == "13.8%" and pct[(0.0875, 1)] == "8.8%"
    cr = {(e["value"], e["digits"]): e["expected"] for e in recorded["cr"]}
    assert cr[(137.25, 1)] == "₹137.3 Cr"  # money rounds half up too, like percentages
