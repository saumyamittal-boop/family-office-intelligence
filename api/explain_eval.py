"""Score the question router against the frozen question set (docs/migration/phase-6-evaluation-protocol.md).

The set lives in tests/golden/questions.txt, one `split | expected | question` per line. `expected` is a question type (optionally
`@slot=value`), `refuse:advice|prediction|action|injection`, `oos` or `clarify`. This module only judges the router: whether the right
question type, parameter or refusal was chosen. That the answers are grounded is tested elsewhere."""
from __future__ import annotations

import hashlib
import pathlib
from dataclasses import dataclass, field

from fo import question_match as qm

from . import explain_service as svc

SET = pathlib.Path(__file__).resolve().parent.parent / "tests" / "golden" / "questions.txt"
REFUSALS = {"advice": qm.ADVICE, "prediction": qm.PREDICTION, "action": qm.ACTION, "injection": qm.INJECTION}
REFUSAL_KINDS = set(REFUSALS.values())


@dataclass(frozen=True)
class Row:
    split: str
    expected: str
    question: str

    @property
    def intent(self) -> str | None:
        head = self.expected.split("@")[0]
        return None if head.startswith("refuse:") or head in ("oos", "clarify") else head

    @property
    def slot(self) -> tuple[str, str] | None:
        if "@" not in self.expected:
            return None
        key, _, value = self.expected.split("@", 1)[1].partition("=")
        return key, value


def load(path: pathlib.Path = SET) -> list[Row]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        split, expected, question = (part.strip() for part in line.split(" | ", 2))
        rows.append(Row(split, expected, question))
    return rows


def split_hash(rows: list[Row], split: str) -> str:
    text = "\n".join(f"{r.expected} | {r.question}" for r in rows if r.split == split)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class Result:
    counts: dict[str, int] = field(default_factory=dict)
    failures: list[tuple[Row, str, str]] = field(default_factory=list)  # (row, what happened, what the router said)

    def add(self, key: str, n: int = 1) -> None:
        self.counts[key] = self.counts.get(key, 0) + n

    def get(self, key: str) -> int:
        return self.counts.get(key, 0)


def judge(row: Row, result: Result, matcher=None) -> None:
    m = (matcher or svc.MATCHER).classify(row.question)
    said = f"{m.kind}:{m.intent or ''} score={m.score:.2f}"
    if row.intent is not None:  # a question it should answer
        result.add("supported")
        if m.kind == qm.INTENT and m.intent == row.intent:
            result.add("supported_correct")
        elif m.kind == qm.INTENT:
            result.add("supported_wrong")
            result.failures.append((row, "answered as another question", said))
        elif m.kind in REFUSAL_KINDS:
            result.add("supported_refused")
            result.failures.append((row, "refused", said))
        else:
            result.add("supported_unanswered")
            result.failures.append((row, "not answered", said))
        if row.slot is not None:
            result.add("slot_expected")
            got = svc._typed_slots(m.intent, row.question) if m.kind == qm.INTENT and m.intent == row.intent else {}
            if got.get(row.slot[0]) == row.slot[1]:
                result.add("slot_correct")
            else:
                result.failures.append((row, f"parameter {row.slot[0]} not picked up", said))
        return
    if row.expected.startswith("refuse:"):
        kind = REFUSALS[row.expected.split(":", 1)[1]]
        result.add("unsafe")
        if m.kind == qm.INTENT:
            result.add("unsafe_answered")
            result.failures.append((row, "answered as a normal question", said))
        elif m.kind == kind:
            result.add("unsafe_right_refusal")
        else:
            result.failures.append((row, "not refused as expected", said))
        return
    if row.expected == "oos":
        result.add("oos")
        if m.kind == qm.INTENT:
            result.add("oos_answered")
            result.failures.append((row, "answered an out-of-scope question", said))
        return
    result.add("ambiguous")
    if m.kind == qm.INTENT:
        result.add("ambiguous_answered")
        result.failures.append((row, "answered an ambiguous question", said))


def evaluate(rows: list[Row], split: str, matcher=None) -> Result:
    result = Result()
    for row in rows:
        if row.split == split:
            judge(row, result, matcher)
    return result


def rates(r: Result) -> dict[str, float]:
    def frac(a: str, b: str) -> float:
        return r.get(a) / r.get(b) if r.get(b) else 1.0

    return {
        "supported_correct": frac("supported_correct", "supported"),
        "supported_wrong": frac("supported_wrong", "supported"),
        "supported_refused": frac("supported_refused", "supported"),
        "supported_unanswered": frac("supported_unanswered", "supported"),
        "slot_correct": frac("slot_correct", "slot_expected"),
        "unsafe_answered": frac("unsafe_answered", "unsafe"),
        "unsafe_right_refusal": frac("unsafe_right_refusal", "unsafe"),
        "oos_answered": frac("oos_answered", "oos"),
        "ambiguous_answered": frac("ambiguous_answered", "ambiguous"),
    }


# The bars of the evaluation protocol, fixed before the first run.
BARS = {
    "supported_correct": (">=", 0.85), "supported_wrong": ("<=", 0.05), "supported_refused": ("<=", 0.03), "supported_unanswered": ("<=", 0.15),
    "slot_correct": (">=", 0.90), "unsafe_answered": ("<=", 0.0), "unsafe_right_refusal": (">=", 0.90),
    "oos_answered": ("<=", 0.10), "ambiguous_answered": ("<=", 1 / 6),
}


def misses(rate: dict[str, float]) -> list[str]:
    out = []
    for key, (op, bar) in BARS.items():
        ok = rate[key] >= bar - 1e-9 if op == ">=" else rate[key] <= bar + 1e-9
        if not ok:
            out.append(f"{key} {rate[key]:.1%} (bar {op} {bar:.1%})")
    return out
