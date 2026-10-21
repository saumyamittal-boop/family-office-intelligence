"""Match a typed question to one of a fixed set of question types. Pure Python: no model, no network, no randomness.

This decides *what was asked*, never what is true. The caller owns the catalogue of question types and writes every answer
from engine results. The matcher answers three things about a question:

* is it one the explainer must not answer as asked (an instruction to the assistant, a request to act, a request for advice,
  a request to predict the market)? Those are recognised first and always get a fixed reply;
* otherwise, which question type is it closest to, and is that clear enough to answer (a threshold on the score and a margin
  over the runner-up)? If not, the caller asks which of the nearest ones was meant;
* which parameters did it name (a mix, a scenario, an asset class)? Parameters are only ever picked from lists the caller supplies.

Scoring is a plain TF-IDF cosine between the question and each question type's example phrasings, over words and word pairs,
after lower-casing, light stemming, a small synonym table and one-edit spelling repair against the known vocabulary.
"""
from __future__ import annotations

import difflib
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

MAX_QUESTION = 300

# What the matcher decided.
INTENT = "intent"  # clear enough to answer
CLARIFY = "clarify"  # close to a few question types, none clearly: ask which
ADVICE = "advice"  # "should I buy ...", "which fund ..."
PREDICTION = "prediction"  # "will the market ... next month"
ACTION = "action"  # "sell everything", "move my money"
INJECTION = "injection"  # "ignore your rules", "show every family's records"
OUT_OF_SCOPE = "out_of_scope"
EMPTY = "empty"

ACCEPT = 0.35  # the best score must reach this ...
MARGIN = 0.08  # ... and beat the runner-up by this much
FLOOR = 0.25  # below this nothing is close enough even to ask about
MAX_CANDIDATES = 3
STRONG = 0.75  # a score this high is trusted even when only one word is shared
COVERAGE = 0.5  # at least this share of the question's own words must be ones the catalogue knows
WEAK_FACTOR = 0.3  # how much the question words "what", "how", "why" count for
PROFILE_WEIGHT = 1.0  # a question type is also scored on all its phrasings pooled, not just the nearest one

_STOP = frozenset(
    "a an the is are am was were be been do does did i me my mine we our us you your it its of to in on at for and or so that this these "
    "those can could would please pls tell show give want know about there some any with from by as also just kindly sir madam should explain exactly really actually particular thing things let".split()
)

_WEAK = frozenset("what how why which when where who much many if whatif there get make need like look does more less most least".split())

# Folded onto one word after stemming (so "cash", "liquidity" and "liquid" are one feature). Kept small and boring on purpose.
_GROUPS = {  # each group is folded onto its first word (after light stemming); domain vocabulary only, kept boring on purpose
    "liquid": "liquid liquidity cash",
    "equity": "equity equities stock stocks share shares",
    "fall": "fall drop decline dip plunge slump decrease loss lose lost losing losses",
    "return": "return returns earn earning earnings profit gain gains yield",
    "risk": "risk risky riskier safe safer safest danger aggressive aggressively cautious conservative",
    "cr": "cr crore crores rupee rupees rs inr",
    "mix": "mix portfolio allocation split composition recommendation recommended recommend strategy strategies option options suggested proposed chosen picked",
    "outflow": "outflow outflows spending spend expense expenses expenditure payment payments commitment commitments withdrawal withdrawals bills bill outgo wedding",
    "warn": "warn warning warnings alert alerts flag flags flagged worry concern concerns issue issues problem problems trouble banner red",
    "mean": "mean means meaning define definition",
    "calc": "calc calculate calculated computed compute computing work works worked method methodology model derive derived produce produced arrive",
    "assume": "assume assumption assumptions assumed",
    "limit": "limit limits cap caps ceiling floor bound bounds constraint constraints restrict restricts restriction restricting maximum minimum max min binding binds capped",
    "enough": "enough sufficient adequate adequately sufficiently",
    "cover": "cover covered coverage cushion buffer",
    "count": "count counted counts consider considered treat treated include included includes",
    "year": "year years yearly annual annually calendar",
    "history": "history historical historically past sample",
    "wealth": "wealth corpus networth money",
    "projection": "projection projected project horizon future",
    "import": "import imported importing upload uploaded uploading statement statements file",
    "tax": "tax taxes charges costs fees brokerage",
    "peak": "peak top trough",
    "trade": "trade trades reallocation reallocations reallocate rebalance rebalancing transition shift move",
    "crash": "crash crashes meltdown collapse bear recession",
    "rate": "rate rates interest",
    "illiquid": "illiquid property land realty",
    "lock": "lock locked lockin",
    "worst": "worst biggest deepest largest",
    "tail": "tail",
    "optimise": "optimise optimiser optimize optimizer optimisation optimization",
    "trust": "trust trusted reliable reliability accurate accuracy dependable",
    "synthetic": "synthetic simulated fictional fake dummy",
    "compare": "compare compared comparison versus vs against contrast rank ranking ranked differ difference different",
    "meet": "meet meets meeting beat beating exceed exceeds achieve achievable reach reached",
}
_SYNONYMS = {word: canon for canon, words in _GROUPS.items() for word in words.split()}

_PHRASES = (  # multi-word spellings folded before tokenising
    (r"\bmid[ -]?cap\b", "midcap"), (r"\blarge[ -]?cap\b", "largecap"), (r"\breal estate\b", "illiquid"),
    (r"\bdraw[ -]?down\b", "drawdown"), (r"\bc\.?v\.?a\.?r\b", "cvar"), (r"\bexpected shortfall\b", "cvar"),
    (r"\bnet[ -]?worth\b", "networth"), (r"\bsafety[ -]?net\b", "cover"), (r"\bwhat[ -]?if\b", "whatif"),
    (r"\bper[ -]?cent\b", "percent"), (r"\bbuy and sell\b", "buysell"), (r"\bbuy or sell\b", "buysell"),
    (r"\bsell and buy\b", "buysell"), (r"\blong[ -]?term\b", "longterm"), (r"\b(2008|2020|covid)\b", "crash"), (r"\block[ -]?in\b", "lock"),
    (r"\bhow much\b", "howmuch"), (r"\bshould know\b", "know"),
    (r"\blimit(s|ations?)? of (this|the) (analysis|model|tool|results?|numbers)\b", "caveat"),
)

_INJECTION = re.compile(
    r"\b(ignore|disregard|forget|override|bypass)\b.{0,40}\b(rules?|instructions?|prompt|guidelines?|polic(y|ies)|above|previous|earlier)\b"
    r"|\b(system|developer|hidden|secret) (prompt|message|instructions?)\b|\bjailbreak\b|\bdeveloper mode\b|\bdan mode\b"
    r"|\b(reveal|show|list|dump|print|leak|export)\b.{0,40}\b(all|every|other|another|everyone'?s?)\b.{0,30}\b(records?|famil(y|ies)|users?|accounts?|profiles?|passwords?|data|holdings)\b"
    r"|\b(you are|you're) now\b|\bpretend (to be|you)\b|\bact as\b|\bpassword\b|\bapi key\b|\bsecret key\b"
    r"|\bobey\b|\b(drop|disable|turn off|remove|skip|ignore|lift) (all |the |your )?(safety|safeguards?|guardrails?|filters?|restrictions?|limits)\b"
)

_OBJECT = (  # what a person would be asking to have moved, bought or sold
    r"money|cash|funds?|equit(y|ies)|gold|debt|bonds?|stocks?|shares?|portfolio|holdings?|corpus|property|assets?|mid ?cap|midcap|large ?cap|largecap|illiquid|everything|all"
    r"|[0-9]+ ?(cr|crores?|lakhs?)"
)

_ACTION = re.compile(
    r"^(please |pls |just |kindly |now |go ahead and |can you |could you )?(move|transfer|shift|switch|put|invest|place|execute|rebalance|sell|buy|book|redeem|withdraw|liquidate|convert|exit|dump|purchase)\b(?=.*(" + _OBJECT + r"|mix|mixes|allocation|strategy|option))(?!.*\b(table|chart|list|graph|view|display|side by side)\b)"
    r"|\b(do it|go ahead|place (the|an|my) orders?|make the trades?|execute (the|this|it)|carry it out|apply it for me)\b|\b(do|buy|sell|move|place|execute|rebalance|apply|transfer|invest|switch|book|handle|manage|arrange|sort|fix)\b.{0,40}\bfor me\b"
)

_ADVICE = re.compile(
    r"(?<!why )\b(should|shall) (i|we) (buy|sell|invest|hold|switch|exit|add|reduce|move|put|choose|pick|go|take|select|stay|keep|redeem|withdraw|increase|decrease|rebalance|do|prefer|opt|avoid|trade|park|shift)\b|\bis it (a )?(good|wise|safe|smart|right|better) (idea |time |move )?to (buy|sell|invest|hold|switch|exit|add|reduce|stay)\b"
    r"|\b(which|what|best|top|good) (stocks?|shares?|funds?|mutual funds?|etfs?|scrips?|compan(y|ies)|sectors?|securit(y|ies)|bonds?|nfos?|ipos?|coins?|crypto)\b"
    r"|\bwhere (should|do|can) (i|we) (invest|put|park)\b|\bwhat should (i|we) do\b|\b(tips?|advice|advise|recommend\w*|suggest(ion)?s?)\b.{0,30}\b(stocks?|shares?|funds?|invest\w*|buy|sell)\b"
    r"|\bworth (buying|selling|investing)\b|\bmulti ?bagger\b"
    r"|\b(what|which|one) to (buy|sell|pick|choose|hold|invest|select|own)\b|\b(pick|choose|decide) between\b|\bwhich\b.{0,20}\b(is|are) (better|best)\b"
)

_MARKET = (
    r"nifty|sensex|markets?|bse|nse|index|rupee|inflation|interest rates?|rates|bitcoin|crypto|oil|crude|fed|rbi|economy|gdp"
    r"|gold price|silver price|share price|stock price|stock market|equity market"
)
_FUTURE = (
    r"\bwill\b|\bwon'?t\b|\bgoing to\b|\bnext (week|month|quarter|year|decade)\b|\btomorrow\b|\bby (march|june|december|diwali|20\d\d)\b"
    r"|\bforecast|\bpredict|\bprojection of the (market|nifty|sensex)\b|\bcrash (soon|next)\b|\bwhen will\b"
)
_PREDICTION = re.compile(rf"(?=.*\b({_MARKET})\b)(?=.*({_FUTURE}))", re.S)
# "will gold rise", "is nifty going to hit ...": a named market moving. Not applied when the question is about the person's own holdings.
_DIRECTION = re.compile(
    r"\b(will|going to|gonna)\b.{0,25}\b(gold|silver|equit(y|ies)|stocks?|shares?|nifty|sensex|market)\b.{0,25}"
    r"\b(go up|go down|rise|fall|crash|rally|drop|double|hit|reach|cross|beat|recover)\b"
)
_OWN = re.compile(r"\b(my|our|mine)\b")
_SELF = re.compile(r"\b(my|our|mine|portfolio|mix|mixes|plan|corpus|family|holdings|us|we)\b")
# "is a crash coming", "when will the next recession come": an event in the market asked about as something that will happen.
_EVENT = re.compile(
    r"\b(is|are|will|when|how soon)\b.{0,30}\b(crash|crashes|recession|bubble|correction|bull run|bear market)\b.{0,20}\b(coming|come|happen|hit|start|end|begin|soon|next)\b"
)


def normalise(text: str) -> str:
    """Lower-case ASCII words and digits separated by single spaces; accents and punctuation removed."""
    text = unicodedata.normalize("NFKD", str(text)).lower()
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("₹", " cr ").replace("%", " percent ").replace("&", " and ")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _fold_phrases(text: str) -> str:
    for pattern, repl in _PHRASES:
        text = re.sub(pattern, repl, text)
    return text


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("ss") or len(word) <= 3:
        return word
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _words(text: str, mend=None) -> list[str]:
    out = []
    for raw in _fold_phrases(normalise(text)).split():
        if raw in _STOP or raw.isdigit():
            continue
        if mend is not None:
            raw = mend(raw)
        word = _SYNONYMS.get(raw) or _SYNONYMS.get(_stem(raw)) or _stem(raw)
        out.append(_SYNONYMS.get(word, word))
    return out


def _features(words: Sequence[str]) -> Counter:
    counts: Counter = Counter(words)
    counts.update(f"{a}_{b}" for a, b in zip(words, words[1:]))
    return counts


@dataclass(frozen=True)
class Spec:
    """One question type: its id and the phrasings it should be recognised by."""

    id: str
    examples: tuple[str, ...]


@dataclass
class Match:
    kind: str
    intent: str | None = None
    score: float = 0.0
    margin: float = 0.0
    candidates: list[tuple[str, float]] = field(default_factory=list)


class Matcher:
    def __init__(self, specs: Sequence[Spec]):
        self._ids = [s.id for s in specs]
        surface: set[str] = set(_SYNONYMS)  # every spelling the table knows, so a typo of "recommendation" can be mended before it is folded
        for spec in specs:
            for example in spec.examples:
                surface.update(w for w in _fold_phrases(normalise(example)).split() if w not in _STOP and not w.isdigit())
        self._surface = sorted(surface)
        self._surface_set = surface

        per_example: list[tuple[str, Counter]] = []
        profile: dict[str, Counter] = {s.id: Counter() for s in specs}
        for spec in specs:
            for example in spec.examples:
                feats = _features(self._words(example))
                per_example.append((spec.id, feats))
                profile[spec.id].update(feats.keys())  # how many of the phrasings use each word
        df: Counter = Counter()  # in how many question types a word appears: a word in one type is a strong cue, in many a weak one
        for counts in profile.values():
            df.update(counts.keys())
        self._df = df
        n = len(self._ids)
        self._idf = {f: math.log((n + 1) / (c + 0.5)) + 1.0 for f, c in df.items()}
        self._examples: list[tuple[str, dict[str, float], float]] = []
        for intent, feats in per_example:
            vec = self._weigh(feats)
            self._examples.append((intent, vec, math.sqrt(sum(v * v for v in vec.values())) or 1.0))
        self._profiles: dict[str, tuple[dict[str, float], float]] = {}
        for intent, counts in profile.items():
            vec = self._weigh(counts)
            self._profiles[intent] = (vec, math.sqrt(sum(v * v for v in vec.values())) or 1.0)

    def _fix(self, raw: str) -> str:
        if raw in self._surface_set or len(raw) < 6:
            return raw
        near = difflib.get_close_matches(raw, self._surface, n=1, cutoff=0.86)
        return near[0] if near else raw

    def _coverage(self, text: str) -> float:
        raw = [self._fix(w) for w in _fold_phrases(normalise(text)).split() if w not in _STOP and w not in _WEAK and not w.isdigit()]
        return sum(w in self._surface_set for w in raw) / len(raw) if raw else 0.0

    def _words(self, text: str, mend: bool = False) -> list[str]:
        return _words(text, self._fix if mend else None)

    def _weigh(self, feats: Counter) -> dict[str, float]:
        out = {}
        for f, c in feats.items():
            weight = (1.0 + math.log(c)) * self._idf.get(f, 1.0)
            if all(p in _WEAK for p in f.split("_")):
                weight *= WEAK_FACTOR  # "what", "how", "why" tell little about which question it is
            out[f] = weight
        return out

    def detail(self, question: str) -> dict[str, tuple[float, int]]:
        """For each question type that shares anything with the question: (score, shared features)."""
        words = self._words(question, mend=True)
        if not any(w not in _WEAK for w in words):
            return {}  # nothing but "what" and "how": not a question about anything
        query = self._weigh(_features(words))
        norm = math.sqrt(sum(v * v for v in query.values()))
        if not norm:
            return {}
        best: dict[str, float] = {}
        for intent, vec, vnorm in self._examples:
            dot = sum(w * vec[f] for f, w in query.items() if f in vec)
            if dot:
                best[intent] = max(best.get(intent, 0.0), dot / (norm * vnorm))
        out: dict[str, tuple[float, int]] = {}
        for intent, (vec, vnorm) in self._profiles.items():
            dot = sum(w * vec[f] for f, w in query.items() if f in vec)
            score = max(best.get(intent, 0.0), PROFILE_WEIGHT * dot / (norm * vnorm) if dot else 0.0)
            if score:
                shared = [f for f in query if f in vec and not all(p in _WEAK for p in f.split("_"))]
                out[intent] = (score, len(shared))
        return out

    def scores(self, question: str) -> dict[str, float]:
        return {intent: s for intent, (s, _) in self.detail(question).items()}

    @staticmethod
    def precheck(question: str) -> Match | None:
        """The requests that are never answered as asked (advice, prediction, action, attacks), and the empty question. None for anything else.

        Shared by every matcher: the rules here are fixed patterns, not scores, so no model can talk its way round them."""
        text = normalise(str(question)[:MAX_QUESTION])
        if not text:
            return Match(EMPTY)
        folded = _fold_phrases(text)
        for kind, pattern in ((INJECTION, _INJECTION), (ACTION, _ACTION), (ADVICE, _ADVICE), (PREDICTION, _PREDICTION)):
            # "how will the portfolio behave in a market crash" asks about the person's own results, not about the market itself
            if pattern.search(folded) and not (kind == PREDICTION and _SELF.search(folded)):
                return Match(kind)
        if (_DIRECTION.search(folded) or _EVENT.search(folded)) and not _OWN.search(folded):
            return Match(PREDICTION)
        return None

    def classify(self, question: str) -> Match:
        early = self.precheck(question)
        if early is not None:
            return early
        text = normalise(str(question)[:MAX_QUESTION])
        info = self.detail(text)
        ranked = sorted(((i, v[0]) for i, v in info.items()), key=lambda kv: (-kv[1], kv[0]))
        if not ranked or ranked[0][1] < FLOOR:
            return Match(OUT_OF_SCOPE, score=ranked[0][1] if ranked else 0.0)
        top, runner = ranked[0], (ranked[1][1] if len(ranked) > 1 else 0.0)
        margin = top[1] - runner
        near = [(i, round(s, 4)) for i, s in ranked[:MAX_CANDIDATES] if s >= FLOOR]
        _, shared = info[top[0]]
        # One shared word is enough only if the match is near-exact ("what is cvar"); a lone "risk" or "match" is not a question.
        # And a question mostly made of words the catalogue has never seen ("who won the cricket match") is not one of ours.
        if top[1] >= ACCEPT and margin >= MARGIN and (shared >= 2 or top[1] >= STRONG) and self._coverage(text) >= COVERAGE:
            return Match(INTENT, top[0], round(top[1], 4), round(margin, 4), near)
        return Match(CLARIFY, None, round(top[1], 4), round(margin, 4), near)


def find_slots(question: str, vocab: Mapping[str, Mapping[str, Sequence[str]]]) -> dict[str, list[str]]:
    """Which of the allowed values for each slot the question names, in the order the vocabulary lists them.

    `vocab` is {slot: {value: (spelling, ...)}}. A value counts when one of its spellings appears as whole words. Nothing
    outside the vocabulary can come back, so a parameter can never be something the person typed.
    """
    text = f" {_fold_phrases(normalise(question[:MAX_QUESTION]))} "
    found: dict[str, list[str]] = {}
    for slot, values in vocab.items():
        hits = [value for value, spellings in values.items() if any(re.search(rf"(?<![a-z0-9]){re.escape(normalise(s))}(s|es|ed|ing)?(?![a-z0-9])", text) for s in spellings)]
        if hits:
            found[slot] = hits
    return found
