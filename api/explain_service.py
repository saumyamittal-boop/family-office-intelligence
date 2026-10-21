"""From a question (typed, or chosen as a chip or a "Why?" button) to a reply (ADR-0021).

Typed questions go through the matcher, which decides *what was asked*; the answer is then written by a reviewed template from engine
results. Nothing the person typed is used except to pick a question type and, from fixed lists, its parameters. The text is never stored;
only the question type and the match score are logged."""
from __future__ import annotations

import logging
import re
import threading

from fo import question_embed as qe
from fo import question_hybrid as qh
from fo import question_match as qm

from . import explain_answers as ans
from . import explain_intents as intents
from . import explain_schemas as es
from .errors import ApiError

log = logging.getLogger("api.explain")
LEXICAL = qm.Matcher(intents.specs())  # pure Python, no model: always available


class _Router:
    """The word matcher, with the embedding layer on top when the model files are present and intact. Built on first use, once."""

    def __init__(self) -> None:
        self._matcher = None
        self._lock = threading.Lock()
        self.kind = "lexical"

    def _get(self):
        if self._matcher is None:
            with self._lock:
                if self._matcher is None:
                    embedder = qe.load()
                    if embedder is None:
                        self._matcher = LEXICAL
                    else:
                        self._matcher = qh.HybridMatcher(LEXICAL, embedder, intents.specs(), intents.REFUSAL_EXAMPLES)
                        self.kind = "hybrid"
        return self._matcher

    def warm(self) -> str:
        self._get()
        return self.kind

    def classify(self, question: str) -> qm.Match:
        return self._get().classify(question)

    def scores(self, question: str) -> dict[str, float]:
        return self._get().scores(question)


MATCHER = _Router()

_REFUSALS = (qm.ADVICE, qm.PREDICTION, qm.ACTION, qm.INJECTION)


def _answer(intent: str, slots: dict[str, str], ctx: ans.Ctx) -> es.AnswerOut:
    return ans.HANDLERS[intent](ctx, slots).build()


def _suggest(ids: tuple[str, ...]) -> list[es.ChipOut]:
    return [intents.chip_for(i, _default_slots(i)) for i in ids]


def _default_slots(intent: str) -> dict[str, str]:
    chip = next((c for c in intents.ALL_CHIPS if c.intent == intent), None)
    return dict(chip.slots) if chip else {}


def _typed_slots(intent: str, question: str) -> dict[str, str]:
    """Parameters the question names, only from the allowed lists, and only when exactly one value matched."""
    wanted = intents.SLOTS_FOR.get(intent, ())
    found = qm.find_slots(question, {k: v for k, v in intents.SLOT_VOCAB.items() if k in wanted})
    picked = {k: v[0] for k, v in found.items() if len(v) == 1}
    scenario = picked.get("scenario")
    if scenario and set(re.findall(r"\d+", question)) - set(re.findall(r"\d+", scenario)) - {"2008", "2020"}:
        del picked["scenario"]  # "equities fall 40%" is not the built-in 25% case: show them all and point to the Scenarios page
    return picked


def ask(body: es.AskIn, ctx: ans.Ctx) -> es.ReplyOut:
    if body.intent is not None:
        if body.intent not in ans.HANDLERS:
            raise ApiError(422, "That is not a question I know.")
        why_not = intents.check_slots(body.intent, body.slots)
        if why_not:
            raise ApiError(422, why_not)
        log.info("explain intent=%s via=chip", body.intent)
        return es.ReplyOut(kind="answer", intent=body.intent, answer=_answer(body.intent, body.slots, ctx))

    if body.question is None:
        raise ApiError(422, "Ask a question or choose one.")
    match = MATCHER.classify(body.question)
    log.info("explain kind=%s intent=%s score=%.2f via=%s", match.kind, match.intent, match.score, MATCHER.kind)

    if match.kind == qm.INTENT and match.intent:
        slots = _typed_slots(match.intent, body.question)
        others = [intents.chip_for(i, _default_slots(i)) for i, _ in match.candidates if i != match.intent][:2]  # "not what you meant?"
        return es.ReplyOut(kind="answer", intent=match.intent, confidence=match.score, answer=_answer(match.intent, slots, ctx), suggestions=others)
    if match.kind == qm.CLARIFY:
        chips = [intents.chip_for(i, {**_default_slots(i), **_typed_slots(i, body.question)}) for i, _ in match.candidates]
        return es.ReplyOut(kind="clarify", confidence=match.score, message=intents.CLARIFY_MESSAGE, suggestions=chips)
    kind = "refusal" if match.kind in _REFUSALS else "empty" if match.kind == qm.EMPTY else "out_of_scope"
    return es.ReplyOut(kind=kind, confidence=match.score or None, message=intents.MESSAGES[match.kind], suggestions=_suggest(intents.SUGGEST_AFTER_REFUSAL[match.kind]))
