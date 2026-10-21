"""Every answer is written from engine results and nothing else (ADR-0021).

The guard that matters: after the figures an answer registered are taken out of its sentences, no digit may be left. A number can
only reach a person through the figure builder, so it always has a label and a source; and each figure's value must equal the
engine value at the path it names.
"""
from __future__ import annotations

import inspect
import re

import pytest

from fo import engine, personas
from fo import formatting as fmt
from fo.data import load_returns
from api import explain_answers as ans
from api import explain_intents as intents
from api import explain_schemas as es
from api import holdings_schemas as hs
from api.analysis import AnalysisService

PERSONA_KEYS = list(personas.PERSONAS)
BASES = ("all", "strict")


@pytest.fixture(scope="module")
def svc():
    daily, source = load_returns()
    service = AnalysisService(daily, source, 90.0)
    yield service
    service.close()


def consolidation(empty: bool) -> hs.ConsolidationOut:
    classes = ["Large-cap equity", "Mid-cap equity", "Debt", "Gold", "Cash & liquid", "Illiquid"]
    if empty:
        return hs.ConsolidationOut(
            profile_id=1, imports=0, lines=0, total_cr=0.0, by_class=[hs.ClassTotal(asset_class=c, total_cr=0.0, share=0.0, lines=0) for c in classes],
            by_account=[], top_positions=[], profile_corpus_cr=500.0, difference_cr=0.0, compare=[],
        )
    amounts = [150.0, 50.0, 100.0, 25.0, 25.0, 150.0]
    total = sum(amounts)
    return hs.ConsolidationOut(
        profile_id=1, imports=2, lines=9, total_cr=total,
        by_class=[hs.ClassTotal(asset_class=c, total_cr=v, share=v / total, lines=1) for c, v in zip(classes, amounts)],
        by_account=[hs.AccountTotal(account="Demat 1", total_cr=300.0, share=300 / total, lines=5), hs.AccountTotal(account="", total_cr=200.0, share=200 / total, lines=4)],
        top_positions=[hs.PositionOut(name="Nifty 50 index fund", asset_class="Large-cap equity", accounts=2, value_cr=150.0, share=150 / total)],
        profile_corpus_cr=500.0, difference_cr=0.0,
        compare=[hs.ClassCompare(asset_class=c, imported_share=v / total, profile_share=0.1 + 0.05 * i, difference=v / total - (0.1 + 0.05 * i)) for i, (c, v) in enumerate(zip(classes, amounts))],
    )


def context(svc, key: str, basis: str, empty_holdings: bool = False) -> ans.Ctx:
    profile = personas.PERSONAS[key]
    return ans.Ctx(
        profile,
        analyse=lambda: svc.analyse(7, profile, basis),
        history=lambda: svc.history(7, profile, basis),
        consolidation=lambda: consolidation(empty_holdings),
    )


def slot_choices(intent: str) -> list[dict[str, str]]:
    allowed = intents.SLOTS_FOR.get(intent, ())
    if not allowed:
        return [{}]
    key = allowed[0]
    return [{}] + [{key: value} for value in intents.SLOT_VOCAB[key]]


def every_answer(svc, empty_holdings: bool = False):
    for key in PERSONA_KEYS:
        for basis in BASES:
            ctx = context(svc, key, basis, empty_holdings)
            for intent in ans.HANDLERS:
                for slots in slot_choices(intent):
                    if intent == "buy_sell" and slots.get("option") == "Current":
                        pass  # asked for a change "from" the current mix: the handler defaults to Balanced, and says so
                    yield key, basis, intent, slots, ctx, ans.HANDLERS[intent](ctx, slots).build()


def text_of(answer: es.AnswerOut) -> list[str]:
    """Everything an answer writes itself (the model's own passed-through wording is not ours to police)."""
    parts = [answer.title, answer.lead, *answer.caveats, *answer.notes]
    for sec in answer.sections:
        if not sec.from_engine:
            parts += [sec.heading, *sec.lines]
    for t in answer.tables:
        parts += [t.caption, *t.columns, *[cell for row in t.rows for cell in row]]
    parts += [link.label for link in answer.links] + [chip.label for chip in answer.follow_ups]
    return parts


def strip_figures(text: str, answer: es.AnswerOut) -> str:
    for shown in sorted({f.shown for f in answer.figures}, key=len, reverse=True):
        text = text.replace(shown, " ")
    return text


# ---- the guard ------------------------------------------------------------------------------------------------------------
def test_no_digit_reaches_a_sentence_without_a_registered_figure(svc):
    seen = 0
    for key, basis, intent, slots, _, answer in every_answer(svc):
        for part in text_of(answer):
            left = strip_figures(part, answer)
            assert not re.search(r"\d", left), f"{intent} {slots} ({key}/{basis}): unregistered number in {part!r}"
            seen += 1
    assert seen > 2000  # it really walked all of them


def test_the_guard_catches_a_number_typed_into_a_template(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all")
    draft = ans.HANDLERS["liquidity_enough"](ctx, {})
    draft.lead += " That is about 3.9x."
    answer = draft.build()
    assert re.search(r"\d", strip_figures(answer.lead, answer))


def test_the_same_figure_key_cannot_hold_two_values():
    b = ans.Builder()
    b.pct("x", "A", 0.1, "f", "p")
    with pytest.raises(ValueError):
        b.pct("x", "A", 0.2, "f", "p")


# ---- provenance -----------------------------------------------------------------------------------------------------------
_TOKEN = re.compile(r"([A-Za-z_][A-Za-z_0-9]*)|\[(\d+|-1)\]")


def resolve(root, path: str):
    node = root
    for name, index in _TOKEN.findall(path):
        if name:
            node = node[name] if isinstance(node, dict) else getattr(node, name)
        else:
            node = node[int(index)]
    return node


def root_for(field: str, analysis, profile, history, holdings):
    head = field.split(".")[0].split("[")[0]
    if head == "profile":
        return profile, field[len("profile."):]
    if head == "consolidation":
        return holdings, field[len("consolidation."):]
    if head in ("portfolios", "dates"):
        return history, field
    return analysis, field


def test_every_figure_equals_the_engine_value_at_its_source(svc):
    checked = 0
    for key in PERSONA_KEYS:
        for basis in BASES:
            ctx = context(svc, key, basis)
            analysis, history, holdings = ctx.a, ctx.history(), consolidation(False)
            for intent in ans.HANDLERS:
                for slots in slot_choices(intent):
                    answer = ans.HANDLERS[intent](ctx, slots).build()
                    for fig in answer.figures:
                        if fig.derived or fig.value is None or " " in fig.field or fig.field.startswith("engine"):
                            continue
                        root, path = root_for(fig.field, analysis, ctx.profile, history, holdings)
                        actual = resolve(root, path)
                        assert abs(float(actual) - fig.value) < 1e-9, f"{intent} {key}/{basis}: {fig.key} says {fig.value}, {fig.field} is {actual}"
                        checked += 1
    assert checked > 2500


def test_derived_figures_say_what_they_were_derived_from(svc):
    for _, _, intent, _, _, answer in every_answer(svc):
        for fig in answer.figures:
            if fig.derived:
                assert fig.field.strip(), f"{intent}: derived figure {fig.key} has no source"
            assert fig.label.strip() and fig.page.strip() and fig.field.strip()


def test_text_figures_carry_the_exact_text(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all")
    answer = ans.HANDLERS["scenario_loss"](ctx, {}).build()
    names = {f.shown for f in answer.figures if f.unit == "text"}
    assert {r.scenario for r in ctx.a.current_scenarios} <= names


# ---- the answers themselves -----------------------------------------------------------------------------------------------
def test_every_answer_has_a_lead_a_title_and_valid_follow_ups(svc):
    for key, basis, intent, slots, _, answer in every_answer(svc):
        assert answer.intent == intent and answer.title.strip() and answer.lead.strip(), (intent, slots)
        assert answer.caveats
        for chip in answer.follow_ups:
            assert chip.intent in ans.HANDLERS, chip
            assert intents.check_slots(chip.intent, chip.slots) is None, chip
        for link in answer.links:
            assert link.to in ans.PATHS.values()


def test_every_chip_in_the_catalogue_is_askable(svc):
    ctx = context(svc, PERSONA_KEYS[1], "all")
    for chip in intents.ALL_CHIPS:
        assert chip.intent in ans.HANDLERS and intents.check_slots(chip.intent, chip.slots) is None
        assert ans.HANDLERS[chip.intent](ctx, chip.slots).build().lead
    assert set(intents.EXAMPLES) == set(ans.HANDLERS) == {c.intent for c in intents.ALL_CHIPS}


def test_the_models_own_reasons_are_passed_through_unchanged(svc):
    ctx = context(svc, PERSONA_KEYS[2], "all")
    answer = ans.HANDLERS["why_mix"](ctx, {"option": "Growth"}).build()
    growth = next(o.portfolio for o in ctx.a.options if o.portfolio.label == "Growth")
    engine_sections = [sec for sec in answer.sections if sec.from_engine]
    assert engine_sections and engine_sections[0].lines == list(growth.explanation)


def test_liquidity_answer_matches_a_hand_calculation(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all")
    cur = ctx.a.current
    answer = ans.HANDLERS["liquidity_enough"](ctx, {}).build()
    ratio = cur.available_cover_cr / cur.required_cover_cr
    assert fmt.cr(cur.required_cover_cr, 0) in answer.lead and fmt.cr(cur.available_cover_cr, 0) in answer.lead
    assert f"{fmt.half_up(ratio, 1)}x" in answer.lead


def test_buy_sell_changes_add_up_to_nothing(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all")
    detail = next(o for o in ctx.a.options if o.portfolio.label == "Balanced")
    assert abs(sum(r.change_cr for r in detail.action_plan)) < 1e-6  # money moves between classes; none is created
    answer = ans.HANDLERS["buy_sell"](ctx, {"option": "Balanced"}).build()
    assert len(answer.tables[0].rows) == len(detail.action_plan)


def test_a_missing_option_is_defaulted_and_said_so(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all")
    answer = ans.HANDLERS["why_mix"](ctx, {}).build()
    assert any("Balanced" in n and "did not name" in n for n in answer.notes)
    answer = ans.HANDLERS["buy_sell"](ctx, {"option": "Current"}).build()
    assert answer.title.endswith("Balanced mix") and answer.notes


def test_an_empty_holdings_import_is_said_plainly(svc):
    ctx = context(svc, PERSONA_KEYS[0], "all", empty_holdings=True)
    for intent in ("holdings_summary", "holdings_vs_profile"):
        answer = ans.HANDLERS[intent](ctx, {}).build()
        assert "imported" in answer.lead.lower() and not answer.figures


def test_holdings_questions_need_no_allocation_run():
    profile = personas.PERSONAS[PERSONA_KEYS[0]]

    def boom():
        raise AssertionError("the allocation model was run for a holdings question")

    ctx = ans.Ctx(profile, analyse=boom, history=boom, consolidation=lambda: consolidation(False))
    for intent in ("holdings_summary", "holdings_vs_profile", "help"):
        assert ans.HANDLERS[intent](ctx, {}).build().lead


def test_user_supplied_names_arrive_as_registered_text_figures():
    profile = personas.PERSONAS[PERSONA_KEYS[0]]
    ctx = ans.Ctx(profile, analyse=lambda: None, history=lambda: None, consolidation=lambda: consolidation(False))
    answer = ans.HANDLERS["holdings_summary"](ctx, {}).build()
    assert any(f.shown == "Nifty 50 index fund" and f.unit == "text" for f in answer.figures)


def test_the_cvar_wording_matches_the_engine():
    assert engine.cvar_21d.__defaults__ == (0.95,)
    source = inspect.getsource(engine.cvar_21d)
    assert "c[21:]" in source and "c[:-21]" in source


@pytest.mark.parametrize("ratio, word", [(0.4, "shortfall of"), (0.99, "shortfall of"), (1.0, "thin margin"), (1.49, "thin margin"), (1.5, "comfortable margin"), (3.0, "comfortable margin")])
def test_the_liquidity_wording_changes_exactly_where_the_models_own_warning_does(svc, ratio, word):
    base = context(svc, PERSONA_KEYS[0], "all")
    analysis = base.a
    need = analysis.current.required_cover_cr
    moved = analysis.model_copy(update={"current": analysis.current.model_copy(update={"available_cover_cr": need * ratio})})
    ctx = ans.Ctx(base.profile, analyse=lambda: moved, history=base.history, consolidation=base.consolidation)
    answer = ans.HANDLERS["liquidity_enough"](ctx, {}).build()
    meaning = next(s for s in answer.sections if s.heading == "What this means").lines[0]
    assert word in meaning, (ratio, meaning)
    # the same thresholds as the engine's own insight (fo/engine.py build_insights): below one is a shortfall, below one and a half is thin
    insight = engine.build_insights(base.profile, _portfolio_with_cover(svc, base, need * ratio), _portfolio_with_cover(svc, base, need * ratio))
    tone_title = next(i for i in insight if i["title"] in ("Liquidity shortfall", "Thin liquidity cover", "Comfortable liquidity"))["title"]
    assert {"shortfall of": "Liquidity shortfall", "thin margin": "Thin liquidity cover", "comfortable margin": "Comfortable liquidity"}[word] == tone_title


def _portfolio_with_cover(svc, ctx, available):
    """The engine's own portfolio object for this family, with only the counted liquid assets changed."""
    import dataclasses

    entry = svc._entry(ctx.profile, "all")  # the cached engine objects behind the analysis
    current = entry.current if hasattr(entry, "current") else entry.portfolios[0]
    return dataclasses.replace(current, available_cover_cr=available)
