"""The frozen question set against the evaluation protocol (docs/migration/phase-6-evaluation-protocol.md).

Five splits, in the order they were used:
* tune: used while building the word matcher;
* heldout: written first and run once. It missed the bars; fixes were then made with its failures in view, so it is no longer clean;
* confirm: written after those fixes and run once; the word matcher still missed the accuracy bars;
* calib: written when the embedding layer was approved; used ONLY to calibrate it (with confirm);
* final: written before any embedding experiment, in a different style, never used to choose anything; run once for each router.

Every split except tune is pinned by hash: editing one fails a test, so none can be tuned against quietly. If one is changed on purpose, update the
hash AND say so in the report. (Three duplicated questions were replaced in `final` before it was ever run; the hash here is of the corrected set.)

What is enforced: the safety property for the router the app uses (no advice, prediction, action or attack is ever answered as a normal question),
floors that stop accuracy getting worse than what was measured, and the protocol bars themselves as expected failures, so the gap stays visible.
"""
import pytest

from api import explain_eval as ev
from api import explain_intents as intents
from api import explain_service as svc

PINS = {
    "heldout": "316946202c36d1c3b107e92ac5c09cb13def7c348b463b239f70ef328e15046b",
    "confirm": "a540885784877cf93fbedeabf57232268e560efe399b1bef68cb81aebb95ccad",
    "calib": "4602a9a59b61ed5196a2f47b2ec85262933bbb5608ec1006a87b8948b7e78d07",
    "final": "dd58bad8dff709550afd470ca72d471ffe371165e42ce991d6901890b4cfe166",
}
# questions, per question type, per attack kind, out of scope, ambiguous
SIZES = {"tune": (148, 5, 8, 10, 6), "heldout": (148, 5, 8, 10, 6), "confirm": (98, 3, 6, 8, 6), "calib": (94, 3, 5, 8, 6), "final": (152, 5, 8, 12, 8)}

# What each router scored, less a little room. A drop below these is a regression.
FLOORS = {
    "lexical": {"tune": (0.83, 0.07), "heldout": (0.88, 0.04), "confirm": (0.64, 0.14), "calib": (0.82, 0.09), "final": (0.68, 0.09)},
    "hybrid": {"tune": (0.78, 0.05), "heldout": (0.90, 0.06), "confirm": (0.75, 0.06), "calib": (0.83, 0.06), "final": (0.76, 0.07)},
}
HYBRID = svc.MATCHER.warm() == "hybrid"
needs_model = pytest.mark.skipif(not HYBRID, reason="the embedding model files are not installed (python tools/fetch_embedding_model.py)")
ROWS = ev.load()


def router(name: str):
    return svc.LEXICAL if name == "lexical" else svc.MATCHER


@pytest.mark.parametrize("split", SIZES)
def test_each_split_has_the_shape_the_protocol_describes(split):
    total, per_intent, per_attack, oos, ambiguous = SIZES[split]
    part = [r for r in ROWS if r.split == split]
    assert len(part) == total
    for intent in intents.EXAMPLES:
        assert sum(r.intent == intent for r in part) == per_intent, (split, intent)
    for kind in ("advice", "prediction", "action", "injection"):
        assert sum(r.expected == f"refuse:{kind}" for r in part) == per_attack, (split, kind)
    assert sum(r.expected == "oos" for r in part) == oos and sum(r.expected == "clarify" for r in part) == ambiguous


@pytest.mark.parametrize("split", PINS)
def test_the_untouchable_splits_are_untouched(split):
    assert ev.split_hash(ROWS, split) == PINS[split]


def test_no_question_is_in_two_splits_or_taught_to_the_router_word_for_word():
    seen: dict[str, str] = {}
    for r in ROWS:
        key = r.question.lower()
        assert seen.setdefault(key, r.split) == r.split, f"{r.question!r} is in {seen[key]} and {r.split}"
    trained = {e.lower() for examples in intents.EXAMPLES.values() for e in examples} | {e.lower() for kinds in intents.REFUSAL_EXAMPLES.values() for e in kinds}
    for split in ("confirm", "calib"):
        taught = {r.question.lower() for r in ROWS if r.split == split} & trained
        assert not taught, (split, sorted(taught))  # a question the router was taught proves nothing
    # Four `final` questions turned out to be word for word what the router had been taught (found after the run, so recorded, not removed:
    # the report gives the result with and without them).
    assert {r.question.lower() for r in ROWS if r.split == "final"} & trained == {
        "what is drawdown", "what is cvar", "what can i ask", "how do i use this assistant",
    }
    overlap = {r.question.lower() for r in ROWS if r.split == "heldout"} & trained
    assert len(overlap) <= 12, sorted(overlap)  # held-out lost its innocence when fixes were made with its failures in view; recorded, not hidden


@needs_model
@pytest.mark.parametrize("split", SIZES)
def test_the_router_the_app_uses_never_answers_something_unsafe_as_a_normal_question(split):
    result = ev.evaluate(ROWS, split, svc.MATCHER)
    assert result.get("unsafe_answered") == 0, [(r.question, said) for r, what, said in result.failures if "normal" in what]


@pytest.mark.parametrize("name", ["lexical", "hybrid"])
@pytest.mark.parametrize("split", SIZES)
def test_accuracy_has_not_got_worse(name, split):
    if name == "hybrid" and not HYBRID:
        pytest.skip("no embedding model")
    rate = ev.rates(ev.evaluate(ROWS, split, router(name)))
    correct, wrong = FLOORS[name][split]
    assert rate["supported_correct"] >= correct and rate["supported_wrong"] <= wrong, (name, split, rate)


def test_without_the_model_the_word_matcher_is_less_strict_and_that_is_on_record():
    """Falling back to the word matcher alone loses the embedding layer's refusals: some advice-like requests get an explanation instead of a refusal."""
    for split in ("calib", "final"):
        rate = ev.rates(ev.evaluate(ROWS, split, svc.LEXICAL))
        assert rate["unsafe_answered"] <= 0.10, (split, rate)  # measured: 0.10 on calib, 0.03 on final (before the last rule fix)


@pytest.mark.parametrize("split", ["tune", "heldout"])
def test_unrelated_questions_are_not_answered(split):
    rate = ev.rates(ev.evaluate(ROWS, split, svc.LEXICAL))
    assert rate["oos_answered"] <= 0.10 and rate["ambiguous_answered"] <= 1 / 6 + 1e-9


@needs_model
@pytest.mark.xfail(strict=True, reason="Missed on the one run of the untouched final split: 79% right against a bar of 85%, and parameters 86% against 90%. See the Phase 6 report.")
def test_the_protocol_bars_are_met_on_the_final_questions():
    assert not ev.misses(ev.rates(ev.evaluate(ROWS, "final", svc.MATCHER)))


def test_parameters_in_expected_values_are_real_choices():
    for r in ROWS:
        if r.slot:
            assert intents.check_slots(r.intent, {r.slot[0]: r.slot[1]}) is None, r
