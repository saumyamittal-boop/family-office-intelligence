"""The recorded server verdicts the React profile editor is tested against must match the live server rules."""
import json

from tools.make_profile_vectors import VECTORS_PATH, build


def test_the_recorded_profile_verdicts_are_current():
    recorded = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert recorded == build(), (
        "The profile rules changed (api/schemas.py or fo/profile_form.py). "
        "Run: python tools/make_profile_vectors.py  and re-run the web tests."
    )


def test_the_vectors_cover_both_verdicts_and_the_edges():
    cases = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["cases"]
    assert len(cases) > 100
    assert sum(c["valid"] for c in cases) > 25 and sum(not c["valid"] for c in cases) > 50
    labels = {c["label"] for c in cases}
    for edge in ("holdings shift 0.5", "holdings shift -0.5", "limits min total 100", "limits max total 100", "one-offs last year", "horizon=60"):
        assert edge in labels
