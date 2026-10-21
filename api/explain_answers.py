"""The answers. Each handler reads engine results that are already computed and writes a layered answer from a reviewed template:
the result in one sentence, the reasons, a comparison, the limits, and where to look next (ADR-0021).

Rules for anything written here:
* a number reaches a sentence only through `Builder` (so it has a label and a source); a test fails the build if a digit appears otherwise;
* the model's own wording (`explanation`, `insights`) is passed through unchanged, in a section marked as such, and never paraphrased;
* nothing here tells a person what to buy, sell or choose; it says what the model shows and what it assumes.
"""
from __future__ import annotations

from collections.abc import Callable

from fo import engine
from fo.personas import Profile

from . import explain_schemas as es
from . import holdings_schemas as hs
from . import schemas as s
from .explain_figures import HOLDINGS, OVERVIEW, PATHS, PROFILE, RECOMMENDATION, RISK, SCENARIOS, Builder

OPTIONS = ("Current", "Growth", "Balanced", "Defensive")
DEFAULT_OPTION = "Balanced"

STANDARD_CAVEAT = "This is an illustrative simulation on synthetic data. It is not investment advice."
SAMPLE_CAVEAT = "Market history here is sample data replayed over past years. A past fall is not a forecast of a future one."
NOT_A_PROMISE = "Expected returns are the model's assumptions about an average year. They are not a promise, and real years vary."


class Ctx:
    """What a handler may read. The analysis, history and holdings are fetched the first time a handler asks (a question
    about the holdings needs no allocation run)."""

    def __init__(self, profile: Profile, analyse: Callable[[], s.AnalysisOut], history: Callable[[], s.HistoryOut], consolidation: Callable[[], hs.ConsolidationOut]):
        self.profile, self._analyse, self.history, self.consolidation, self._a = profile, analyse, history, consolidation, None

    @property
    def a(self) -> s.AnalysisOut:
        if self._a is None:
            self._a = self._analyse()
        return self._a


class Draft:
    def __init__(self, intent: str, title: str):
        self.intent, self.title, self.b = intent, title, Builder()
        self.lead = ""
        self.sections: list[es.SectionOut] = []
        self.tables: list[es.TableOut] = []
        self.caveats: list[str] = [STANDARD_CAVEAT]
        self.notes: list[str] = []
        self.links: list[es.LinkOut] = []
        self.follow_ups: list[es.ChipOut] = []

    def section(self, heading: str, lines: list[str], from_engine: bool = False) -> None:
        if lines:
            self.sections.append(es.SectionOut(heading=heading, lines=lines, from_engine=from_engine))

    def table(self, caption: str, columns: list[str], rows: list[list[str]]) -> None:
        self.tables.append(es.TableOut(caption=caption, columns=columns, rows=rows))

    def link(self, page: str) -> None:
        self.links.append(es.LinkOut(label=page, to=PATHS[page]))

    def follow(self, intent: str, label: str, **slots: str) -> None:
        self.follow_ups.append(es.ChipOut(intent=intent, label=label, slots=dict(slots)))

    def build(self) -> es.AnswerOut:
        return es.AnswerOut(
            intent=self.intent, title=self.title, lead=self.lead, sections=self.sections, tables=self.tables, figures=self.b.listing(),
            caveats=self.caveats, notes=self.notes, links=self.links, follow_ups=self.follow_ups,
        )


# ---- small helpers -------------------------------------------------------------------------------------------------
def class_name(name: str) -> str:
    return "Illiquid (held fixed)" if name == "Illiquid" else name


def _pf(a: s.AnalysisOut, label: str) -> tuple[s.PortfolioOut, str]:
    if label == "Current":
        return a.current, "current"
    for i, o in enumerate(a.options):
        if o.portfolio.label == label:
            return o.portfolio, f"options[{i}].portfolio"
    raise KeyError(label)


def _detail(a: s.AnalysisOut, label: str) -> tuple[s.PortfolioDetail, str]:
    for i, o in enumerate(a.options):
        if o.portfolio.label == label:
            return o, f"options[{i}]"
    raise KeyError(label)


def _choose(c: Ctx, slots: dict[str, str], d: Draft, allow_current: bool = True) -> str:
    """The mix the question is about; the default is named in a note so the person can see what was assumed."""
    label = slots.get("option")
    if label in OPTIONS and (allow_current or label != "Current"):
        return label
    d.notes.append(
        f"Showing the {DEFAULT_OPTION} mix because the question did not name one."
        if label is None else f"Showing the {DEFAULT_OPTION} mix, because the change from today needs a recommended mix to compare with."
    )
    return DEFAULT_OPTION


def _limit(c: Ctx, d: Draft) -> str:
    return d.b.pct("dd_limit", "Your drawdown limit", c.profile.max_drawdown, "profile.max_drawdown", PROFILE)


def _target(c: Ctx, d: Draft) -> str:
    return d.b.pct("target", "Your real-return target", c.profile.target_real_return, "profile.target_real_return", PROFILE)


def _inside(flag: bool) -> str:
    return "inside" if flag else "above"


def _yes(flag: bool) -> str:
    return "Yes" if flag else "No"


def _status(ratio: float) -> str:  # the same thresholds as the engine's insight (fo/engine.py build_insights)
    return "shortfall" if ratio < 1.0 else "thin" if ratio < 1.5 else "comfortable"


# ---- my mix --------------------------------------------------------------------------------------------------------
def why_mix(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("why_mix", "")
    label = _choose(c, slots, d)
    pf, base = _pf(c.a, label)
    b = d.b
    d.title = "What you hold today" if label == "Current" else f"Why the {label} mix?"
    ret = b.pct("exp_return", f"{label}: expected return a year", pf.exp_return, f"{base}.exp_return", RECOMMENDATION)
    real = b.pct("exp_real", f"{label}: expected return after inflation", pf.exp_real, f"{base}.exp_real", RECOMMENDATION)
    mdd = b.pct("max_dd", f"{label}: worst fall in the sample history", pf.max_dd, f"{base}.max_dd", RISK)
    subject = "Your current mix" if label == "Current" else f"The {label} mix"
    d.lead = f"{subject} is expected to return {ret} a year, {real} after inflation, and its worst fall in the sample history was {mdd}."

    now = c.a.current.weights_total
    mix = pf.weights_total
    rows = []
    with b.table():
        for cls in now:
            rows.append([class_name(cls), b.pct(f"w.now.{cls}", f"Today: {cls}", now[cls], f"current.weights_total.{cls}", RECOMMENDATION),
                         b.pct(f"w.{label}.{cls}", f"{label}: {cls}", mix.get(cls, 0.0), f"{base}.weights_total.{cls}", RECOMMENDATION)])
    d.table("Where the money goes, as a share of the whole corpus", ["Asset class", "Today", "This mix"], rows)

    d.section("How the model got here", list(pf.explanation), from_engine=True)
    limit, target = _limit(c, d), _target(c, d)
    lines = [f"Your drawdown limit is {limit}. This mix's worst fall was {mdd}, so it is {_inside(pf.dd_ok)} that limit."]
    if pf.meets_target:
        lines.append(f"Your real-return target is {target}. This mix is expected to return {real} after inflation, which meets it.")
    else:
        gap = b.pct("target_gap", f"{label}: shortfall against your target", -pf.target_gap, f"{base}.target_gap", RECOMMENDATION, 2, derived=True)
        lines.append(f"Your real-return target is {target}. This mix is expected to return {real} after inflation, short of it by {gap}.")
    d.section("Against your own limits", lines)
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RECOMMENDATION)
    if label != "Current":
        d.follow("buy_sell", "What would change from today?", option=label)
    d.follow("compare_mixes", "How do the mixes compare?")
    d.follow("why_not_riskier", "Why not a riskier mix?", option=label)
    return d


def compare_mixes(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("compare_mixes", "How the mixes compare")
    b = d.b
    ops = [o.portfolio for o in c.a.options]
    best_ret = max(range(len(ops)), key=lambda i: ops[i].exp_return)
    shallow = min(range(len(ops)), key=lambda i: ops[i].max_dd)
    ret = b.pct("best_return", f"{ops[best_ret].label}: expected return a year", ops[best_ret].exp_return, f"options[{best_ret}].portfolio.exp_return", RECOMMENDATION)
    fall = b.pct("shallow_fall", f"{ops[shallow].label}: worst fall", ops[shallow].max_dd, f"options[{shallow}].portfolio.max_dd", RISK)
    d.lead = (
        f"{ops[best_ret].label} has the highest expected return ({ret} a year) and {ops[shallow].label} the shallowest worst fall ({fall}). "
        "Which suits you depends on what matters more to you."
    )
    rows = []
    entries = [(c.a.current, "current")] + [(o.portfolio, f"options[{i}].portfolio") for i, o in enumerate(c.a.options)]
    with b.table():
        for pf, base in entries:
            rows.append([
                pf.label,
                b.pct(f"{pf.label}.ret", f"{pf.label}: expected return", pf.exp_return, f"{base}.exp_return", RECOMMENDATION),
                b.pct(f"{pf.label}.real", f"{pf.label}: after inflation", pf.exp_real, f"{base}.exp_real", RECOMMENDATION),
                b.pct(f"{pf.label}.vol", f"{pf.label}: volatility", pf.vol, f"{base}.vol", RISK),
                b.pct(f"{pf.label}.dd", f"{pf.label}: worst fall", pf.max_dd, f"{base}.max_dd", RISK),
                _yes(pf.dd_ok), _yes(pf.meets_target),
            ])
    d.table("Each mix against your limits", ["Mix", "Expected return", "After inflation", "Volatility", "Worst fall", "Inside drawdown limit", "Meets target"], rows)
    inside = [p.label for p in ops if p.dd_ok]
    meets = [p.label for p in ops if p.meets_target]
    limit, target = _limit(c, d), _target(c, d)
    d.section("Your own limits", [
        f"Your drawdown limit is {limit}. " + (f"Inside it: {', '.join(inside)}." if inside else "None of the recommended mixes is inside it."),
        f"Your real-return target is {target}. " + (f"Met by: {', '.join(meets)}." if meets else "None of the recommended mixes meets it."),
    ])
    d.caveats += [SAMPLE_CAVEAT, NOT_A_PROMISE]
    d.link(RECOMMENDATION)
    d.follow("why_mix", "Why the Balanced mix?", option=DEFAULT_OPTION)
    d.follow("scenario_loss", "How would they fare in a crash?")
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    return d


def buy_sell(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("buy_sell", "")
    label = _choose(c, slots, d, allow_current=False)
    detail, base = _detail(c.a, label)
    b = d.b
    d.title = f"What would change to reach the {label} mix"
    plan = detail.action_plan
    sells = sorted((r for r in plan if r.change_cr < -0.5), key=lambda r: r.change_cr)
    buys = sorted((r for r in plan if r.change_cr > 0.5), key=lambda r: -r.change_cr)
    if not sells and not buys:
        d.lead = f"Your current mix is already close to the {label} mix: no asset class moves by more than half a crore."
    else:
        parts = []
        if sells:
            i = plan.index(sells[0])
            parts.append(f"reduce {class_name(sells[0].asset_class)} by {b.cr('sell', 'Largest reduction', -sells[0].change_cr, f'minus {base}.action_plan[{i}].change_cr', RECOMMENDATION, derived=True)}")
        if buys:
            i = plan.index(buys[0])
            parts.append(f"add {b.cr('buy', 'Largest addition', buys[0].change_cr, f'{base}.action_plan[{i}].change_cr', RECOMMENDATION)} to {class_name(buys[0].asset_class)}")
        d.lead = f"To move from today's mix to the {label} mix, the model would " + " and ".join(parts) + "."
    rows = []
    with b.table():
        for i, r in enumerate(plan):
            f = f"{base}.action_plan[{i}]"
            rows.append([
                class_name(r.asset_class),
                b.pct(f"t.now.{r.asset_class}", f"Today: {r.asset_class}", r.current_share, f"{f}.current_share", RECOMMENDATION),
                b.pct(f"t.new.{r.asset_class}", f"{label}: {r.asset_class}", r.recommended_share, f"{f}.recommended_share", RECOMMENDATION),
                b.signed_cr(f"t.chg.{r.asset_class}", f"Change in {r.asset_class}", r.change_cr, f"{f}.change_cr", RECOMMENDATION),
            ])
    d.table("From today's mix to the recommended one", ["Asset class", "Today", "Recommended", "Change"], rows)
    d.section("Read this as", ["This shows what the model's mix implies for each asset class. It is not an instruction to trade, and the model does not include taxes or transaction costs."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RECOMMENDATION)
    d.follow("why_mix", f"Why the {label} mix?", option=label)
    d.follow("liquidity_enough", "Is my liquidity enough?")
    return d


def why_not_riskier(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("why_not_riskier", "")
    label = _choose(c, slots, d, allow_current=False)
    pf, base = _pf(c.a, label)
    b = d.b
    d.title = f"What holds the {label} mix back"
    limit = _limit(c, d)
    mdd = b.pct("max_dd", f"{label}: worst fall", pf.max_dd, f"{base}.max_dd", RISK)
    lines = []
    if not pf.dd_ok:
        d.lead = f"Even the safest mix the class limits allow has a worst fall of {mdd}, above your {limit} limit, so this is the closest the model could get."
    elif pf.lam_base is not None and pf.lam_used is not None and pf.lam_used > pf.lam_base * 1.0001:
        lo = b.number("lam_base", "Risk aversion before tightening", pf.lam_base, f"{base}.lam_base", RECOMMENDATION, 3)
        hi = b.number("lam_used", "Risk aversion used", pf.lam_used, f"{base}.lam_used", RECOMMENDATION, 3)
        d.lead = f"The model had to take less risk than it would have liked: your {limit} drawdown limit would otherwise have been broken, so risk aversion was raised from {lo} to {hi}."
        lines.append(f"With that, the worst fall in the sample history is {mdd}, which fits your limit.")
    else:
        d.lead = f"Your {limit} drawdown limit did not hold this mix back: its worst fall is {mdd}, inside the limit."
    if pf.bounds_hit:
        d.section("Asset class limits shaping it", list(pf.bounds_hit), from_engine=True)
    if pf.liquidity_infeasible or pf.liquidity_binding:
        need = b.cr("need", "Cash needed for the safety net", pf.required_cover_cr, f"{base}.required_cover_cr", RISK, 0)
        lines.append(
            f"The liquidity requirement ({need}) cannot be met within the class limits, so this is the most liquid mix they allow."
            if pf.liquidity_infeasible else f"The liquidity cover is binding: the mix holds only the {need} the safety net needs."
        )
    d.section("Where the limits bite", lines)
    d.section("How the model chooses", ["It balances expected return against risk, inside your drawdown limit, your class limits and the liquidity requirement. A mix is held back by whichever of these is tightest."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RECOMMENDATION)
    d.follow("class_limits", "Which class limits apply?", option=label)
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    return d


def class_limits(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("class_limits", "")
    label = _choose(c, slots, d, allow_current=False)
    pf, base = _pf(c.a, label)
    d.title = f"Asset class limits and the {label} mix"
    if pf.bounds_hit:
        d.lead = f"Some of your asset class limits are shaping the {label} mix."
        d.section("Limits at work", list(pf.bounds_hit), from_engine=True)
    else:
        d.lead = f"None of your asset class limits is shaping the {label} mix: every class sits strictly between its minimum and its maximum."
    d.section("What these limits are", ["Each asset class has a minimum and a maximum share of the liquid part of the corpus. You can change them in your family profile."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(PROFILE)
    d.follow("why_not_riskier", "What holds the mix back?", option=label)
    return d


def expected_return(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("expected_return", "Expected return and your target")
    b = d.b
    cur = c.a.current
    ret = b.pct("cur.ret", "Current mix: expected return", cur.exp_return, "current.exp_return", RECOMMENDATION)
    real = b.pct("cur.real", "Current mix: after inflation", cur.exp_real, "current.exp_real", RECOMMENDATION)
    target = _target(c, d)
    verdict = "meets it" if cur.meets_target else "does not meet it"
    d.lead = f"Your current mix is expected to return {ret} a year, {real} after inflation, against your target of {target} after inflation, so it {verdict}."
    rows = []
    entries = [(cur, "current")] + [(o.portfolio, f"options[{i}].portfolio") for i, o in enumerate(c.a.options)]
    with b.table():
        for pf, base in entries:
            rows.append([
                pf.label,
                b.pct(f"{pf.label}.ret", f"{pf.label}: expected return", pf.exp_return, f"{base}.exp_return", RECOMMENDATION),
                b.pct(f"{pf.label}.real", f"{pf.label}: after inflation", pf.exp_real, f"{base}.exp_real", RECOMMENDATION),
                _yes(pf.meets_target),
            ])
    d.table("Expected return by mix", ["Mix", "Expected return a year", "After inflation", "Meets your target"], rows)
    d.caveats += [NOT_A_PROMISE, SAMPLE_CAVEAT]
    d.link(RECOMMENDATION)
    d.follow("projection", "What could my corpus grow to?")
    d.follow("compare_mixes", "How do the mixes compare?")
    return d


# ---- liquidity -----------------------------------------------------------------------------------------------------
def liquidity_enough(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("liquidity_enough", "Is my liquidity enough?")
    b, cur = d.b, c.a.current
    need = b.cr("need", "Outflows to be covered", cur.required_cover_cr, "current.required_cover_cr", RISK, 0)
    have = b.cr("have", "Liquid assets counted", cur.available_cover_cr, "current.available_cover_cr", RISK, 0)
    ratio = cur.available_cover_cr / cur.required_cover_cr if cur.required_cover_cr else 0.0
    times = b.ratio("ratio", "Cover", ratio, "current.available_cover_cr / current.required_cover_cr", RISK, derived=True)
    months = b.months("cover_months", "Months of outflows to cover", c.profile.cover_months, "profile.cover_months", PROFILE)
    d.lead = f"Over the next {months} your planned outflows come to {need}. Your liquid assets count for {have}, which is {times} the amount needed."
    status = _status(ratio)
    if status == "shortfall":
        gap = b.cr("gap", "Shortfall", cur.required_cover_cr - cur.available_cover_cr, "current.required_cover_cr - current.available_cover_cr", RISK, 0, derived=True)
        meaning = [f"That is a shortfall of {gap}: the model flags it as a warning."]
    elif status == "thin":
        meaning = ["That is a thin margin: the model flags it as a warning, because a delayed sale or an extra outflow could use it up."]
    else:
        meaning = ["That is a comfortable margin: the liquid assets cover the planned outflows with room to spare."]
    d.section("What this means", meaning)
    d.section("What counts as liquid", ["The cover counts assets that can be turned into cash in time, after a haircut for each. Illiquid holdings, such as property, are not counted."])
    d.section("The basis used", [c.a.basis_label], from_engine=True)
    rows = []
    with b.table():
        for i, r in enumerate(c.a.current_ladder[:5]):
            f = f"current_ladder[{i}]"
            rows.append([
                b.year(f"lad.y{r.year}", "Year", r.year, f"{f}.year", RISK),
                b.cr(f"lad.out{r.year}", f"Year {r.year}: outflows", r.outflows_cr, f"{f}.outflows_cr", RISK),
                b.cr(f"lad.liq{r.year}", f"Year {r.year}: liquid assets", r.liquid_value_cr, f"{f}.liquid_value_cr", RISK),
                b.months(f"lad.m{r.year}", f"Year {r.year}: months covered", r.months_covered, f"{f}.months_covered", RISK),
            ])
    if rows:
        d.table("Liquidity ladder: the first years", ["Year", "Outflows", "Liquid assets", "Months covered"], rows)
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RISK)
    d.follow("cover_basis", "What counts towards the cover?")
    d.follow("upcoming_outflows", "What outflows are planned?")
    d.follow("scenario_loss", "What if markets fall?")
    return d


def cover_basis(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("cover_basis", "What counts towards the liquidity cover")
    b = d.b
    ops = [o.portfolio for o in c.a.options]
    d.lead = "The safety-net check counts the assets that can be turned into cash in time, after a haircut for how fully each can be sold. Cash and liquid funds count at full value."
    d.section("Which assets count", [
        "Large-cap equity, gold and debt count after a haircut, and mid-cap equity after a larger one.",
        "Illiquid holdings, such as property, do not count.",
    ])
    d.section("The basis used here", [c.a.basis_label], from_engine=True)
    held = [p for p in ops if p.liquidity_binding or p.liquidity_infeasible]
    n = b.count("n_held", "Recommended mixes held back by the liquidity requirement", len(held), "options[*].portfolio.liquidity_binding", RISK, derived=True)
    m = b.count("n_mixes", "Recommended mixes", len(ops), "options", RISK, derived=True)
    if held:
        d.section("Does it limit the mixes?", [f"The liquidity requirement holds back {n} of the {m} recommended mixes: {', '.join(p.label for p in held)}."])
    else:
        d.section("Does it limit the mixes?", [f"None of the {m} recommended mixes is held back by the liquidity requirement: it is met without changing what the model would otherwise choose. Your current mix is checked on the Risk and liquidity page."])
    d.link(RISK)
    d.link(PROFILE)
    d.follow("liquidity_enough", "Is my liquidity enough?")
    return d


def upcoming_outflows(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("upcoming_outflows", "What outflows are planned")
    b = d.b
    rows_in = c.a.upcoming_outflows
    first = rows_in[:3]
    total = sum(r.total_cr for r in first)
    one_off = sum(r.one_off_cr for r in first)
    span = b.years("span", "Years covered", len(first), "upcoming_outflows", RISK, derived=True)
    t = b.cr("total", "Planned outflows in that time", total, "sum of upcoming_outflows[0:3].total_cr", RISK, derived=True)
    o = b.cr("one_off", "Of which one-off commitments", one_off, "sum of upcoming_outflows[0:3].one_off_cr", RISK, derived=True)
    d.lead = f"Planned outflows over the next {span} come to {t}, of which {o} are one-off commitments."
    rows = []
    with b.table():
        for i, r in enumerate(rows_in[:6]):
            f = f"upcoming_outflows[{i}]"
            rows.append([
                b.year(f"out.y{r.year}", "Year", r.year, f"{f}.year", RISK),
                b.cr(f"out.s{r.year}", f"Year {r.year}: spending", r.spending_cr, f"{f}.spending_cr", RISK, 2),
                b.cr(f"out.o{r.year}", f"Year {r.year}: one-off", r.one_off_cr, f"{f}.one_off_cr", RISK, 2),
                b.cr(f"out.t{r.year}", f"Year {r.year}: total", r.total_cr, f"{f}.total_cr", RISK, 2),
            ])
    d.table("Planned outflows by year", ["Year", "Spending", "One-off", "Total"], rows)
    d.section("Where this comes from", ["Yearly spending grows with assumed inflation. One-off commitments are the ones you entered in your family profile."])
    d.link(PROFILE)
    d.link(RISK)
    d.follow("liquidity_enough", "Is my liquidity enough?")
    return d


# ---- risk ----------------------------------------------------------------------------------------------------------
def drawdown_meaning(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("drawdown_meaning", "What is a drawdown limit?")
    b, cur = d.b, c.a.current
    limit = _limit(c, d)
    mdd = b.pct("cur.dd", "Current mix: worst fall in the sample history", cur.max_dd, "current.max_dd", RISK)
    d.lead = f"Your drawdown limit is {limit}: the largest fall from a peak to a later low that you said you can accept."
    d.section("Where your current mix stands", [f"Your current mix lost at most {mdd} from peak to low in the sample history, which is {_inside(cur.dd_ok)} your limit."])
    ok = [o.portfolio.label for o in c.a.options if o.portfolio.dd_ok]
    d.section("The recommended mixes", [f"Inside the limit: {', '.join(ok)}." if ok else "None of the recommended mixes is inside the limit; the model shows the closest it could get."])
    d.section("How it is measured", [
        "The model replays the sample market history day by day with the mix held constant, and records the deepest fall from any earlier peak.",
        "If a recommended mix would break your limit, the model lowers risk until it fits, or tells you the limit cannot be met.",
    ])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RISK)
    d.link(PROFILE)
    d.follow("cvar_meaning", "What is CVaR?")
    d.follow("history_worst", "What was the worst year?")
    return d


def cvar_meaning(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("cvar_meaning", "What is CVaR?")
    b = d.b
    sig = engine.cvar_21d.__defaults__ or (0.95,)
    days = b.count("cvar_days", "Trading days in each stretch", 21, "engine: cvar_21d window", RISK, derived=True)
    tail = b.pct("cvar_tail", "Share of the worst stretches averaged", 1.0 - sig[0], "engine: cvar_21d level", RISK, 0, derived=True)
    cur = b.pct("cur.cvar", "Current mix: average loss in the worst stretches", c.a.current.cvar21, "current.cvar21", RISK)
    d.lead = f"CVaR is the average loss in the worst {tail} of {days}-day stretches in the sample history. For your current mix that is {cur}."
    rows = []
    entries = [(c.a.current, "current")] + [(o.portfolio, f"options[{i}].portfolio") for i, o in enumerate(c.a.options)]
    with b.table():
        for pf, base in entries:
            rows.append([pf.label, b.pct(f"{pf.label}.cvar", f"{pf.label}: CVaR", pf.cvar21, f"{base}.cvar21", RISK)])
    d.table("CVaR by mix", ["Mix", "Average loss in the worst stretches"], rows)
    d.section("Why it is shown", ["It looks further into bad outcomes than the single worst fall does. It is still based on past data, so a future bad stretch could be worse."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RISK)
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    return d


def scenario_loss(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("scenario_loss", "How would my mix fare in a scenario?")
    b = d.b
    rows_in = c.a.current_scenarios
    name = slots.get("scenario")
    idx = next((i for i, r in enumerate(rows_in) if r.scenario == name), None)
    limit = _limit(c, d)
    if idx is None:
        d.lead = "Here is how your current mix would fare in each built-in scenario. Name one for the full picture."
        rows = []
        with b.table():
            for i, r in enumerate(rows_in):
                f = f"current_scenarios[{i}]"
                rows.append([
                    b.text(f"sc.n{i}", "Scenario", r.scenario, f"{f}.scenario", SCENARIOS),
                    b.signed_pct(f"sc.v{i}", f"{r.scenario}: change in value", r.value_change, f"{f}.value_change", SCENARIOS),
                    b.signed_cr(f"sc.c{i}", f"{r.scenario}: change in value", r.value_change_cr, f"{f}.value_change_cr", SCENARIOS, 0),
                    _yes(r.within_drawdown_limit),
                ])
        d.table("Your current mix under each built-in scenario", ["Scenario", "Change in value", "Change", "Inside drawdown limit"], rows)
        d.notes.append("No built-in scenario was named, so all of them are shown. To try your own shocks, such as a different fall in equities, use the Scenarios page.")
    else:
        r, f = rows_in[idx], f"current_scenarios[{idx}]"
        sc = b.text("scenario", "Scenario", r.scenario, f"{f}.scenario", SCENARIOS)
        change = b.signed_pct("v", "Change in value", r.value_change, f"{f}.value_change", SCENARIOS)
        crs = b.signed_cr("cr", "Change in value", r.value_change_cr, f"{f}.value_change_cr", SCENARIOS, 0)
        d.title = "How would my mix fare in this scenario?"
        d.lead = f"In the scenario “{sc}” your current mix would change in value by {change} ({crs}), which is {_inside(r.within_drawdown_limit)} your {limit} drawdown limit."
        cover = b.ratio("cover", "Liquidity cover after the shock", r.cover_ratio, f"{f}.cover_ratio", SCENARIOS)
        d.section("Liquidity afterwards", [f"Afterwards your liquid assets would cover the planned outflows {cover} over, which is {'still enough' if r.cover_held else 'not enough'}."])
        rows = []
        with b.table():
            rows.append([
                "Current", b.signed_pct("cmp.cur", "Current: change in value", r.value_change, f"{f}.value_change", SCENARIOS), _yes(r.within_drawdown_limit),
            ])
            for i, o in enumerate(c.a.options):
                j = next((k for k, x in enumerate(o.scenarios) if x.scenario == r.scenario), None)
                if j is None:
                    continue
                x, g = o.scenarios[j], f"options[{i}].scenarios[{j}]"
                rows.append([o.portfolio.label, b.signed_pct(f"cmp.{o.portfolio.label}", f"{o.portfolio.label}: change in value", x.value_change, f"{g}.value_change", SCENARIOS), _yes(x.within_drawdown_limit)])
        d.table("The same scenario for each mix", ["Mix", "Change in value", "Inside drawdown limit"], rows)
    d.section("What a scenario is", ["A scenario applies one set of shocks to today's holdings. It is a stress test, not a forecast of what will happen."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(SCENARIOS)
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    d.follow("liquidity_enough", "Is my liquidity enough?")
    return d


def history_worst(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("history_worst", "What was the worst year?")
    b = d.b
    h = c.history()
    cur = h.portfolios[0]
    full = [r for r in cur.annual if not r.partial] or list(cur.annual)
    worst = min(full, key=lambda r: r.portfolio_return)
    wi = cur.annual.index(worst)
    yr = b.year("worst.year", "Worst calendar year", worst.year, f"portfolios[0].annual[{wi}].year", RISK)
    ret = b.signed_pct("worst.ret", "Return in that year", worst.portfolio_return, f"portfolios[0].annual[{wi}].portfolio_return", RISK)
    mdd = b.pct("hist.dd", "Deepest fall from a peak", cur.max_drawdown, "portfolios[0].max_drawdown", RISK)
    start = b.text("date.start", "Date: start of the sample", h.dates[0], "dates[0]", RISK)
    end = b.text("date.end", "Date: end of the sample", h.dates[-1], "dates[-1]", RISK)
    d.lead = f"Replaying the sample history from {start} to {end}, the worst full calendar year for your current mix was {yr} ({ret}), and the deepest fall from a peak was {mdd}."
    rows = []
    with b.table():
        for i, r in enumerate(cur.annual):
            rows.append([
                b.year(f"h.y{r.year}", "Year", r.year, f"portfolios[0].annual[{i}].year", RISK),
                b.signed_pct(f"h.r{r.year}", f"{r.year}: return", r.portfolio_return, f"portfolios[0].annual[{i}].portfolio_return", RISK),
                "Part year" if r.partial else "Full year",
            ])
    d.table("Calendar-year returns for your current mix", ["Year", "Return", "Coverage"], rows)
    d.section("How to read the replay", [h.note], from_engine=True)
    d.caveats += [SAMPLE_CAVEAT]
    d.link(RISK)
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    return d


def projection(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("projection", "What could my corpus grow to?")
    b = d.b
    rows_in = c.a.current_projection
    last = rows_in[-1]
    li = len(rows_in) - 1
    n = b.years("horizon", "Planning horizon", last.year, f"current_projection[{li}].year", RECOMMENDATION)
    nominal = b.cr("nominal", "Corpus at the end, in future rupees", last.nominal_cr, f"current_projection[{li}].nominal_cr", RECOMMENDATION, 0)
    real = b.cr("real", "Corpus at the end, in today's rupees", last.real_cr, f"current_projection[{li}].real_cr", RECOMMENDATION, 0)
    d.lead = f"If your current mix earns its expected return every year and you take the planned outflows, your corpus would be about {nominal} in {n}, which is {real} in today's rupees."
    pick = sorted({0, len(rows_in) // 4, len(rows_in) // 2, (3 * len(rows_in)) // 4, li})
    rows = []
    with b.table():
        for i in pick:
            r = rows_in[i]
            rows.append([
                b.year(f"p.y{r.year}", "Year", r.year, f"current_projection[{i}].year", RECOMMENDATION),
                b.cr(f"p.n{r.year}", f"Year {r.year}: future rupees", r.nominal_cr, f"current_projection[{i}].nominal_cr", RECOMMENDATION, 0),
                b.cr(f"p.r{r.year}", f"Year {r.year}: today's rupees", r.real_cr, f"current_projection[{i}].real_cr", RECOMMENDATION, 0),
            ])
    d.table("The corpus over time", ["Year", "In future rupees", "In today's rupees"], rows)
    infl = b.pct("inflation", "Assumed inflation", engine.INFLATION, "engine: INFLATION", RECOMMENDATION, derived=True)
    d.section("What it assumes", [
        "The same expected return every year, with no bad years, after yearly spending that grows with inflation and the one-off commitments you entered.",
        f"Inflation is assumed at {infl} a year, which is also used to convert to today's rupees.",
    ])
    d.caveats += [NOT_A_PROMISE]
    d.link(RECOMMENDATION)
    d.follow("expected_return", "What return is assumed?")
    return d


def illiquid_treatment(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("illiquid_treatment", "How are illiquid holdings treated?")
    b, p = d.b, c.profile
    share = b.pct("ill.share", "Share of the corpus that is illiquid", p.illiquid_share, "profile.holdings.Illiquid", PROFILE, 0)
    what = b.text("ill.what", "What the illiquid holdings are", p.illiquid.description.lower(), "profile.illiquid.description", PROFILE)
    lock = b.years("ill.lock", "Lock-in", p.illiquid.lock_in_years, "profile.illiquid.lock_in_years", PROFILE)
    ret = b.pct("ill.ret", "Expected return of the illiquid holdings", p.illiquid.expected_return, "profile.illiquid.expected_return", PROFILE)
    d.lead = f"{share} of your corpus is illiquid ({what}). The model holds it fixed until its lock-in of {lock} ends."
    d.section("How it is treated", [
        "It is not part of the optimisation: the model chooses only how to spread the liquid part of the corpus.",
        f"Its expected return is taken as {ret} a year, from your family profile.",
        "It does not count towards the liquidity cover.",
    ])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(PROFILE)
    d.follow("liquidity_enough", "Is my liquidity enough?")
    return d


# ---- holdings ------------------------------------------------------------------------------------------------------
def holdings_summary(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("holdings_summary", "What have I imported?")
    b, h = d.b, c.consolidation()
    d.link(HOLDINGS)
    if h.imports == 0:
        d.lead = "Nothing has been imported for this family yet."
        d.section("How to import", ["On the Holdings page you can choose a CSV or Excel statement, see exactly what was read, and import it. Use synthetic data only for now."])
        return d
    total = b.cr("tot", "Total imported", h.total_cr, "consolidation.total_cr", HOLDINGS)
    n = b.count("lines", "Holdings imported", h.lines, "consolidation.lines", HOLDINGS)
    k = b.count("imports", "Imports", h.imports, "consolidation.imports", HOLDINGS)
    d.lead = f"You have imported {n} holdings worth {total} in all, from {k} {'import' if h.imports == 1 else 'imports'}."
    rows = []
    with b.table():
        for i, r in enumerate(h.by_class):
            f = f"consolidation.by_class[{i}]"
            rows.append([class_name(r.asset_class), b.cr(f"hc.t{i}", f"{r.asset_class}: total", r.total_cr, f"{f}.total_cr", HOLDINGS),
                         b.pct(f"hc.s{i}", f"{r.asset_class}: share", r.share, f"{f}.share", HOLDINGS)])
    d.table("Imported holdings by asset class", ["Asset class", "Total", "Share"], rows)
    if h.top_positions:
        rows = []
        with b.table():
            for i, r in enumerate(h.top_positions):
                f = f"consolidation.top_positions[{i}]"
                rows.append([b.text(f"tp.n{i}", "Holding name", r.name, f"{f}.name", HOLDINGS), class_name(r.asset_class),
                             b.cr(f"tp.v{i}", f"{r.name}: value", r.value_cr, f"{f}.value_cr", HOLDINGS), b.pct(f"tp.s{i}", f"{r.name}: share", r.share, f"{f}.share", HOLDINGS)])
        d.table("The largest holdings across all accounts", ["Holding", "Asset class", "Value", "Share"], rows)
    d.caveats += ["Holding names come from your file and are shown as written."]
    d.follow("holdings_vs_profile", "How does it compare with my profile?")
    return d


def holdings_vs_profile(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("holdings_vs_profile", "How do my imported holdings compare with my profile?")
    b, h = d.b, c.consolidation()
    d.link(HOLDINGS)
    if h.imports == 0 or not h.compare:
        d.lead = "Nothing has been imported yet, so there is nothing to compare with your profile."
        return d
    biggest = max(h.compare, key=lambda r: abs(r.difference))
    i = h.compare.index(biggest)
    diff = b.signed_pct("big.diff", f"{biggest.asset_class}: imported minus profile", biggest.difference, f"consolidation.compare[{i}].difference", HOLDINGS)
    d.lead = (
        f"The largest difference is in {class_name(biggest.asset_class)}: the imported holdings are {diff} against your profile."
        if abs(biggest.difference) >= 0.0005 else "Your imported holdings match your profile's shares."
    )
    rows = []
    with b.table():
        for j, r in enumerate(h.compare):
            f = f"consolidation.compare[{j}]"
            rows.append([class_name(r.asset_class), b.pct(f"cp.i{j}", f"{r.asset_class}: imported", r.imported_share, f"{f}.imported_share", HOLDINGS),
                         b.pct(f"cp.p{j}", f"{r.asset_class}: profile", r.profile_share, f"{f}.profile_share", HOLDINGS)])
    d.table("Imported against the profile, as shares of the whole", ["Asset class", "Imported", "Profile"], rows)
    imported = b.cr("imp.tot", "Imported total", h.total_cr, "consolidation.total_cr", HOLDINGS)
    corpus = b.cr("prof.corpus", "Profile corpus", h.profile_corpus_cr, "consolidation.profile_corpus_cr", HOLDINGS)
    d.section("The totals", [f"The imported total is {imported} and your profile's corpus is {corpus}."])
    d.section("Using the import", ["Nothing in your profile changes until you choose “Use these holdings in my profile” on the Holdings page, which shows the change first."])
    d.follow("holdings_summary", "What have I imported?")
    return d


# ---- the model -----------------------------------------------------------------------------------------------------
def warnings(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("warnings", "What needs my attention?")
    detail, _ = _detail(c.a, DEFAULT_OPTION)
    flagged = [i for i in detail.insights if i.tone == "warn"]
    if flagged:
        d.lead = "The model's checks on your current mix raised these points."
        d.section("Points raised", [f"{i.title}: {i.body}" if i.title else i.body for i in flagged], from_engine=True)
    else:
        d.lead = "None of the model's checks on your current mix raised a warning."
    d.section("What the checks look at", ["Whether your liquid assets cover the planned outflows, whether the worst historical fall stays inside your limit, and whether the expected return meets your target."])
    d.caveats += [SAMPLE_CAVEAT]
    d.link(OVERVIEW)
    d.link(RISK)
    d.follow("liquidity_enough", "Is my liquidity enough?")
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    d.follow("expected_return", "Does my mix meet my target?")
    return d


def how_calculated(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("how_calculated", "How are these numbers produced?")
    d.lead = "Every number comes from one calculation engine, the same for every screen and every answer here. This assistant only explains its results; it never calculates."
    d.section("The method", [
        "The engine spreads the liquid part of the corpus over asset classes to balance expected return against risk, inside your drawdown limit, your class limits and the liquidity requirement.",
        "Illiquid holdings are held fixed and are not part of that choice.",
        "The worst fall is found by replaying sample market history day by day.",
        "Liquidity is checked with rule-based tiers: cash first, then assets that can be sold at a haircut.",
    ])
    d.section("The data", [f"Market history here is {c.a.data_source} data, and the families are fictional."])
    d.section("What it does not do", [
        "It does not forecast markets, and it cannot tell you what to buy or sell.",
        "It does not include taxes or transaction costs.",
    ])
    d.link(RECOMMENDATION)
    d.follow("drawdown_meaning", "What is a drawdown limit?")
    d.follow("cover_basis", "What counts towards the cover?")
    return d


def help_(c: Ctx, slots: dict[str, str]) -> Draft:
    d = Draft("help", "What can I ask?")
    d.lead = "I can explain the results the model has already produced for your family: your mix, your liquidity, your risk, the scenarios and your imported holdings."
    d.section("What I will not do", ["I do not predict markets, pick investments, tell you what to buy or sell, or act for you. I only explain what the model shows."])
    return d


HANDLERS: dict[str, Callable[[Ctx, dict[str, str]], Draft]] = {
    "why_mix": why_mix, "compare_mixes": compare_mixes, "buy_sell": buy_sell, "why_not_riskier": why_not_riskier, "class_limits": class_limits,
    "expected_return": expected_return, "liquidity_enough": liquidity_enough, "cover_basis": cover_basis, "upcoming_outflows": upcoming_outflows,
    "drawdown_meaning": drawdown_meaning, "cvar_meaning": cvar_meaning, "scenario_loss": scenario_loss, "history_worst": history_worst,
    "projection": projection, "illiquid_treatment": illiquid_treatment, "holdings_summary": holdings_summary,
    "holdings_vs_profile": holdings_vs_profile, "warnings": warnings, "how_calculated": how_calculated, "help": help_,
}
