"""Score the question router against the frozen question set (docs/migration/phase-6-evaluation-protocol.md).

    python tools/eval_questions.py [--split NAME ...] [--lexical] [--misses]

By default the tuning split is shown. `--split heldout|confirm|calib|final` adds that split; `--lexical` scores the word matcher alone instead of the
router the app uses (the word matcher plus the embedding layer when the model files are present). The `final` split is for one run, after everything
is frozen: run it once and record the result.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from api import explain_eval as ev  # noqa: E402
from api import explain_service as svc  # noqa: E402


def show(split: str, rows, matcher, with_misses: bool) -> None:
    result = ev.evaluate(rows, split, matcher)
    rate = ev.rates(result)
    total = sum(result.counts.get(k, 0) for k in ("supported", "unsafe", "oos", "ambiguous"))
    print(f"\n== {split}: {total} questions ==")
    missed = " ".join(m.split(" ")[0] for m in ev.misses(rate))
    for key, value in rate.items():
        op, bar = ev.BARS[key]
        print(f"  {'MISS' if key in missed.split() else 'ok  '} {key:22s} {value:6.1%}   (bar {op} {bar:.1%})")
    if with_misses:
        for row, what, said in result.failures:
            print(f"    - [{row.expected}] {row.question!r}: {what} -> {said}")


if __name__ == "__main__":
    args = sys.argv[1:]
    lexical = "--lexical" in args
    matcher = svc.LEXICAL if lexical else svc.MATCHER
    if not lexical:
        print(f"router: {svc.MATCHER.warm()}")
    else:
        print("router: lexical (word matcher alone)")
    splits = ["tune"] + [args[i + 1] for i, a in enumerate(args) if a == "--split" and i + 1 < len(args)]
    all_rows = ev.load()
    for split in splits:
        show(split, all_rows, matcher, "--misses" in args or split == "tune")
