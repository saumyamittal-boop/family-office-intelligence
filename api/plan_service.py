"""The guided plan: answers in, preview, strategies and a saved profile out.

Everything numerical comes from the unchanged engine (`fo.engine`, `fo.plan`). This module only arranges it:
- the *preview* uses cheap arithmetic (no optimiser) so it can update as a person types;
- the *strategies* use the cached analysis, so changing the comfort level costs nothing.
"""
from __future__ import annotations

from dataclasses import replace

from fo import accounts, engine
from fo import plan as fo_plan
from fo.formatting import cr, pct, signed_pct
from fo.personas import ILLIQUID, Profile, profile_to_dict

from . import plan_schemas as p
from .analysis import AnalysisService

STEPS = ["About you", "What's coming", "Your comfort", "Safety net", "What you own", "Your strategies"]
CRASH_LABEL = "In a severe market crash"
NEEDS_SPENDING = (
    "Enter what the family spends in a typical year (even a small amount), or add a commitment inside the safety-net "
    "window, so the plan can size the safety net."
)


def answers_dict(body: p.PlanAnswersIn) -> dict:
    """The plain dict that fo.plan works with (commitments as (kind, year, amount) tuples)."""
    return {
        "name": body.name, "wealth": body.wealth, "spending": body.spending, "risk": body.risk, "months": body.months,
        "commitments": [(c.kind, c.year, c.amount_cr) for c in body.commitments],
        "amounts": dict(body.amounts) if body.amounts is not None else None,
    }


def _completed(answers: dict) -> dict:
    """Answers with a typical split filled in when the family has not said what they own yet."""
    return {**answers, "amounts": answers["amounts"] or fo_plan.typical_split(answers["wealth"])}


def _problems(answers: dict) -> tuple[list[str], Profile | None]:
    problems = fo_plan.validate_answers(answers)
    if problems:
        return problems, None
    profile = fo_plan.profile_from_answers(answers)
    if engine.required_cover_cr(profile) <= 0:
        return [NEEDS_SPENDING], None
    return [], profile


def crash_info() -> p.CrashInfo:
    sc = engine.SCENARIOS["Market crash"]
    names = {"Large-cap equity": "large-cap equity", "Mid-cap equity": "mid-cap equity", "Debt": "debt", "Gold": "gold"}
    parts = [f"{names[c]} {signed_pct(v, 0)}" for c, v in sc["shocks"].items() if c in names]
    return p.CrashInfo(
        label=CRASH_LABEL,
        description=(
            "A stylised shock, not a replay of any real year: " + ", ".join(parts)
            + f", and illiquid holdings {signed_pct(sc['illiquid'], 0)}, all at once."
        ),
    )


def config() -> p.PlanConfigOut:
    defaults = fo_plan.default_answers()
    return p.PlanConfigOut(
        steps=STEPS,
        comfort=[
            p.ComfortOption(
                key=key, letter=spec["strategy"], headline=spec["headline"], blurb=spec["blurb"],
                max_drawdown=spec["max_dd"], target_real_return=spec["target"], portfolio=spec["portfolio"],
            )
            for key, spec in fo_plan.RISK_CHOICES.items()
        ],
        classes=[
            p.ClassInfo(name=name, label=fo_plan.INSTRUMENTS[name][0], description=fo_plan.INSTRUMENTS[name][1])
            for name in p.CLASSES
        ],
        commitment_kinds=list(fo_plan.COMMITMENT_KINDS),
        max_commitments=fo_plan.MAX_COMMITMENTS,
        horizon_years=fo_plan.HORIZON_YEARS,
        wealth=p.Bounds(min=1.0, max=1_000_000.0),
        spending=p.Bounds(min=0.0, max=100_000.0),
        months=p.Bounds(min=3, max=36),
        defaults=p.PlanDefaults(
            name=defaults["name"], wealth=defaults["wealth"], spending=defaults["spending"], risk=defaults["risk"],
            months=defaults["months"],
        ),
        crash=crash_info(),
    )


# ---- Live preview ------------------------------------------------------------------------------------------------------
def preview(body: p.PlanAnswersIn) -> p.PlanPreviewOut:
    answers = answers_dict(body)
    full = _completed(answers)
    typical = fo_plan.typical_split(body.wealth)
    problems, profile = _problems(full)

    if profile is None:
        comfort = [
            p.ComfortLoss(key=k, max_drawdown=s["max_dd"], loss_cr=body.wealth * s["max_dd"])
            for k, s in fo_plan.RISK_CHOICES.items()
        ]
        return p.PlanPreviewOut(problems=problems, typical_amounts=typical, comfort=comfort)

    corpus = profile.corpus_cr
    illiquid_cr = corpus * profile.illiquid_share
    liquid_cr = corpus - illiquid_cr
    required = engine.required_cover_cr(profile)
    commitments_cr = sum(a for _, year, a in full["commitments"] if 12 * year <= profile.cover_months)  # the engine's own window
    outflows = engine.upcoming_outflows(profile, 5)
    near = float(outflows["Total (INR cr)"].head(3).sum())
    near_share = near / liquid_cr if liquid_cr > 0 else 0.0
    entered_total = sum(full["amounts"].values())
    differs = answers["amounts"] is not None and abs(entered_total - body.wealth) > max(0.5, 0.01 * body.wealth)
    spec = fo_plan.RISK_CHOICES[body.risk]

    effects = [
        f"{spec['headline']}: the plan is built so a bad year costs about {pct(spec['max_dd'], 0)} of wealth "
        f"({cr(corpus * spec['max_dd'])}) or less. A higher comfort level allows more shares and a higher expected return; "
        "a lower one keeps more in bonds, gold and cash.",
        f"Over the next {body.months} months the family needs about {cr(required)} within easy reach: {cr(required - commitments_cr)} of "
        "spending" + (f" plus {cr(commitments_cr)} of planned commitments." if commitments_cr > 0 else ".")
        + " The plan checks this and says so if it cannot be met.",
    ]
    if near > 0:
        effects.append(
            f"Planned spending and commitments over the next 3 years come to {cr(near)}, {pct(near_share, 0)} of the "
            f"{cr(liquid_cr)} that can be invested."
        )
    if profile.illiquid_share > 0:
        effects.append(
            f"{pct(profile.illiquid_share, 0)} of the wealth ({cr(illiquid_cr)}) is in property, business and other holdings that cannot be "
            "sold quickly. It stays as it is and does not count towards the safety net."
        )
    effects.append(
        f"What the family owns today decides what to buy and sell. The recommended mix itself is worked out for the {cr(liquid_cr)} that can be invested."
    )

    return p.PlanPreviewOut(
        problems=[],
        typical_amounts=typical,
        comfort=[
            p.ComfortLoss(key=k, max_drawdown=s["max_dd"], loss_cr=corpus * s["max_dd"]) for k, s in fo_plan.RISK_CHOICES.items()
        ],
        corpus_cr=corpus, liquid_cr=liquid_cr, illiquid_cr=illiquid_cr, illiquid_share=profile.illiquid_share,
        safety_net=p.SafetyNet(months=profile.cover_months, required_cr=required, spending_cr=required - commitments_cr, commitments_cr=commitments_cr),
        outflows=[
            p.OutflowRow(year=int(r["Year"]), spending_cr=r["Spending (INR cr)"], one_off_cr=r["One-off (INR cr)"], total_cr=r["Total (INR cr)"])
            for r in outflows.to_dict("records")
        ],
        near_outflows_cr=near, near_outflows_share_of_liquid=near_share,
        amounts_total_cr=entered_total, amounts_differ_from_wealth=differs, effects=effects,
    )


# ---- Strategies ---------------------------------------------------------------------------------------------------------------
def strategies(body: p.PlanAnswersIn, svc: AnalysisService) -> p.PlanStrategiesOut:
    """Strategy A, B and C, each built for its own comfort level. Raises ValueError with the problems if the answers are not usable."""
    full = _completed(answers_dict(body))
    problems, base = _problems(full)
    if base is None:
        raise ValueError(" ".join(problems))

    out: list[p.StrategyOut] = []
    for key, spec in fo_plan.RISK_CHOICES.items():
        variant = fo_plan.variant_profile(base, key)
        analysis = svc.analyse(0, variant, "strict")  # cached: identical for every comfort choice, so comfort changes are free
        detail = next(o for o in analysis.options if o.portfolio.label == spec["portfolio"])
        pf = detail.portfolio
        crash = next(r for r in detail.scenarios if r.scenario == "Market crash")
        out.append(
            p.StrategyOut(
                key=key, letter=spec["strategy"], headline=spec["headline"], blurb=spec["blurb"], portfolio=pf,
                within_comfort_of={k: pf.max_dd <= s["max_dd"] for k, s in fo_plan.RISK_CHOICES.items()},
                meets_goal_of={k: pf.exp_real >= s["target"] for k, s in fo_plan.RISK_CHOICES.items()},
                year_range=detail.year_range,
                crash=p.CrashResult(value_change=crash.value_change, value_change_cr=crash.value_change_cr),
                cover_ratio=pf.available_cover_cr / pf.required_cover_cr,
                description=fo_plan.describe_strategy(variant, pf, key),
                action_plan=[
                    p.PlanActionRow(**row.model_dump(), instrument_name=fo_plan.INSTRUMENTS[row.asset_class][0],
                                    instrument_note=fo_plan.INSTRUMENTS[row.asset_class][1])
                    for row in detail.action_plan
                ],
                illiquid_cr=variant.illiquid_share * variant.corpus_cr,
                illiquid_name=fo_plan.INSTRUMENTS[ILLIQUID][0], illiquid_note=fo_plan.INSTRUMENTS[ILLIQUID][1],
            )
        )
    first = analysis  # any analysis carries the same labels and data source
    return p.PlanStrategiesOut(
        profile_name=base.name, corpus_cr=base.corpus_cr, strategies=out, commitments=list(body.commitments),
        crash=crash_info(), basis_label=first.basis_label, data_source=first.data_source,
    )


# ---- Saving ----------------------------------------------------------------------------------------------------------------------
def build_saved_profile(body: p.PlanAnswersIn, key: str) -> Profile:
    full = _completed(answers_dict(body))
    problems, base = _problems(full)
    if base is None:
        raise ValueError(" ".join(problems))
    variant = fo_plan.variant_profile(base, key)
    return replace(variant, name=f"{base.name} · Strategy {fo_plan.RISK_CHOICES[key]['strategy']}")


class ProfileLimitReached(Exception):
    """The account already holds as many profiles as it may."""


def save(user_id: int, body: p.SaveRequest, max_profiles: int) -> tuple[int, Profile, bool]:
    """Save the chosen strategy as a profile. Saving the same plan twice returns the first copy instead of making another."""
    profile = build_saved_profile(body.answers, body.strategy)
    wanted = profile_to_dict(profile)
    existing_profiles = accounts.list_profiles(user_id)
    for existing_id, existing in existing_profiles:
        if profile_to_dict(existing) == wanted:
            return existing_id, existing, False
    if len(existing_profiles) >= max_profiles:
        raise ProfileLimitReached
    return accounts.add_profile(user_id, profile), profile, True
