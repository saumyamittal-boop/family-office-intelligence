"""The question router with an embedding layer on top of the word matcher (ADR-0021).

The word matcher (`fo.question_match.Matcher`) stays: it supplies the fixed safety patterns and a lexical score. The embedding model supplies a
second opinion on *which question was asked* that does not depend on sharing words, and a way to decline requests the patterns did not recognise.

How a question is scored: its embedding is compared with the embeddings of every example phrasing; a softmax over those similarities gives each
question type a share of the probability ("soft nearest neighbour"), which is mixed with the word matcher's score. Separate similarity gates decide
whether a question is close enough to *ask about* and close enough to *answer*, and the same similarities against phrasings of what the assistant must
not do can turn a request into a refusal. Nothing here writes an answer: the embedding only chooses among the fixed question types.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from . import question_match as qm
from .question_embed import Embedder


@dataclass(frozen=True)
class Params:
    """Calibrated on `calib` and `confirm` (the splits least fitted by the training phrasings). `final` was never used to choose these."""

    temperature: float = 0.02  # softmax temperature over cosine similarities: lower is sharper
    weight: float = 0.8  # share of the embedding probability in the blend with the word matcher's score
    accept: float = 0.30  # blended score the best question type must reach to be answered ...
    margin: float = 0.05  # ... and its lead over the runner-up
    answer_sim: float = 0.80  # nearest example phrasing must be at least this similar for a question to be answered
    ask_sim: float = 0.60  # below this nothing is close enough even to ask "which did you mean?"
    refuse: float = 0.40  # share of the probability mass on phrasings of what the assistant must not do that turns a request into a refusal
    lone_sim: float = 0.90  # a question with a single content word is answered only if it is this close to a phrasing (or the word matcher is sure)


def soft_scores(sims: np.ndarray, rsims: np.ndarray, owner: np.ndarray, r_owner: np.ndarray, intents: Sequence[str], kinds: Sequence[str], temperature: float):
    """Probability share of each question type, of each kind of refused request, and the nearest answerable phrasing's similarity."""
    peak = max(sims.max(), rsims.max())
    answerable = np.exp((sims - peak) / temperature)
    refused = np.exp((rsims - peak) / temperature)
    total = answerable.sum() + refused.sum()
    inside = np.exp((sims - sims.max()) / temperature)  # shares among answerable phrasings only
    per = {intent: float(inside[owner == i].sum() / inside.sum()) for i, intent in enumerate(intents)}
    refusal = {kind: float(refused[r_owner == i].sum() / total) for i, kind in enumerate(kinds)}
    return per, refusal, float(sims.max())


def decide(per: Mapping[str, float], refusal: Mapping[str, float], best_sim: float, lexical: Mapping[str, float], p: Params, lone: bool = False) -> qm.Match:
    """From the scores to a decision. Pure arithmetic, so a parameter sweep can reuse cached similarities."""
    kind, mass = max(refusal.items(), key=lambda kv: kv[1])
    if mass >= p.refuse:
        return qm.Match(kind, score=round(mass, 4))
    score = {i: p.weight * per[i] + (1.0 - p.weight) * lexical.get(i, 0.0) for i in per}
    ranked = sorted(score.items(), key=lambda kv: (-kv[1], kv[0]))
    top, runner = ranked[0], ranked[1][1]
    margin = top[1] - runner
    near = [(i, round(s, 4)) for i, s in ranked[: qm.MAX_CANDIDATES] if s >= 0.1]
    if best_sim < p.ask_sim:
        return qm.Match(qm.OUT_OF_SCOPE, score=round(top[1], 4))
    sure = lexical.get(top[0], 0.0) >= qm.STRONG or best_sim >= p.lone_sim
    if best_sim >= p.answer_sim and top[1] >= p.accept and margin >= p.margin and (not lone or sure):
        return qm.Match(qm.INTENT, top[0], round(top[1], 4), round(margin, 4), near)
    return qm.Match(qm.CLARIFY, None, round(top[1], 4), round(margin, 4), near)


class HybridMatcher:
    def __init__(
        self, lexical: qm.Matcher, embedder: Embedder, specs: Sequence[qm.Spec], refusals: Mapping[str, Sequence[str]], params: Params | None = None,
    ) -> None:
        self.lexical, self.embedder, self.params = lexical, embedder, params or Params()
        self.intents = [s.id for s in specs]
        texts, owner = [], []
        for i, spec in enumerate(specs):
            texts += list(spec.examples)
            owner += [i] * len(spec.examples)
        self.owner = np.asarray(owner)
        self.E = embedder.embed(texts)
        self.kinds = list(refusals)
        r_texts, r_owner = [], []
        for i, kind in enumerate(self.kinds):
            r_texts += list(refusals[kind])
            r_owner += [i] * len(refusals[kind])
        self.r_owner = np.asarray(r_owner)
        self.R = embedder.embed(r_texts)

    def _content_words(self, text: str) -> int:
        return sum(1 for w in self.lexical._words(text, mend=True) if w not in qm._WEAK)

    def scored(self, text: str, vector: np.ndarray):
        per, refusal, best = soft_scores(self.E @ vector, self.R @ vector, self.owner, self.r_owner, self.intents, self.kinds, self.params.temperature)
        return per, refusal, best, self.lexical.scores(text), self._content_words(text) <= 1

    def scores(self, question: str) -> dict[str, float]:
        """The blended score of every question type (for evaluation and tuning)."""
        text = qm.normalise(question)
        per, _, _, lexical, _ = self.scored(text, self.embedder.embed([text])[0])
        return {i: self.params.weight * per[i] + (1.0 - self.params.weight) * lexical.get(i, 0.0) for i in per}

    def classify(self, question: str) -> qm.Match:
        early = self.lexical.precheck(question)
        if early is not None:
            return early
        text = qm.normalise(str(question)[: qm.MAX_QUESTION])
        per, refusal, best, lexical, lone = self.scored(text, self.embedder.embed([text])[0])
        return decide(per, refusal, best, lexical, self.params, lone)
