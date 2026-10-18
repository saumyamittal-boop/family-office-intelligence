from dataclasses import replace

import pandas as pd
import streamlit as st

from fo import accounts, engine, plan, session, ui
from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID

STEPS = ["About you", "What's coming", "Your comfort", "Safety net", "What you own", "Your strategies"]
STRATEGY_LABELS = {"Protect": "A · Protect", "Balance": "B · Balance", "Grow": "C · Grow"}

if "plan_answers" not in st.session_state:
    st.session_state["plan_answers"] = plan.default_answers()
    st.session_state["plan_step"] = 0
a = st.session_state["plan_answers"]
step = st.session_state["plan_step"]


def _go(delta: int) -> None:
    st.session_state["plan_step"] = max(0, min(len(STEPS) - 1, st.session_state["plan_step"] + delta))


def _restart() -> None:
    st.session_state["plan_answers"] = plan.default_answers()
    st.session_state["plan_step"] = 0
    st.session_state.pop("plan_saved", None)


def _advance() -> None:
    st.session_state["plan_step"] = step + 1
    st.rerun()


def _back_button() -> None:
    if step > 0:
        st.button("Back", on_click=_go, args=(-1,), key=f"plan_back_{step}", icon=":material/arrow_back:")


st.html(ui.title_block("Plan my money", "Answer a few plain questions. Get three strategies, with exactly what to buy."))
st.html(ui.steps(STEPS, step))

# ---- Step 1: about you -------------------------------------------------------------------------------------------
if step == 0:
    with st.container(border=True):
        with st.form("plan_form_0", border=False):
            st.html(ui.card_title("Tell us about the family"))
            name = st.text_input("What should we call this plan?", a["name"], max_chars=60)
            wealth = st.number_input(
                "About how much is the family's total wealth? (₹ Cr)", 1.0, 1_000_000.0, float(a["wealth"]), 5.0,
                help="A rough number is fine.",
            )
            spending = st.number_input(
                "About how much does the family spend in a typical year? (₹ Cr)", 0.0, 100_000.0, float(a["spending"]), 0.5
            )
            submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        if abs(wealth - a["wealth"]) > 1e-9:
            a["amounts"] = None  # suggest a fresh split for the new total
        a.update(name=name, wealth=wealth, spending=spending)
        _advance()

# ---- Step 2: what's coming -----------------------------------------------------------------------------------------
elif step == 1:
    with st.container(border=True):
        st.html(ui.card_title("Anything big coming up?"))
        st.caption(
            "For example a child's education, a wedding, buying a property or investing in a business. Add up to "
            f"{plan.MAX_COMMITMENTS}. Leave it empty if nothing is planned."
        )
        with st.form("plan_form_1", border=False):
            columns = ["What", "In how many years", "Amount (₹ Cr)"]
            frame = (
                pd.DataFrame(a["commitments"], columns=columns)
                if a["commitments"]
                else pd.DataFrame(
                    {"What": pd.Series(dtype="object"), "In how many years": pd.Series(dtype="int64"),
                     "Amount (₹ Cr)": pd.Series(dtype="float64")}
                )
            )
            edited = st.data_editor(
                frame, num_rows="dynamic", hide_index=True, width="stretch", key="plan_commitments",
                column_config={
                    "What": st.column_config.SelectboxColumn(options=plan.COMMITMENT_KINDS, required=True),
                    "In how many years": st.column_config.NumberColumn(min_value=1, max_value=plan.HORIZON_YEARS, step=1, required=True),
                    "Amount (₹ Cr)": st.column_config.NumberColumn(min_value=0.0, step=1.0, required=True),
                },
                alt="Upcoming commitments: what, in how many years, and how much",
            )
            submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        rows = [(r["What"], int(r["In how many years"]), float(r["Amount (₹ Cr)"])) for _, r in edited.dropna(how="any").iterrows()]
        problems = plan.validate_answers({**a, "commitments": rows, "amounts": {"x": 1.0}})
        if problems:
            for problem in problems:
                st.error(problem, icon=":material/error:")
        else:
            a["commitments"] = rows
            _advance()
    _back_button()

# ---- Step 3: comfort with risk ---------------------------------------------------------------------------------------
elif step == 2:
    with st.container(border=True):
        with st.form("plan_form_2", border=False):
            st.html(ui.card_title("How do you feel about a bad year?"))
            keys = list(plan.RISK_CHOICES)
            captions = [
                f"{c['blurb']} We would plan for a fall of up to about {ui.cr(a['wealth'] * c['max_dd'])} ({c['max_dd']:.0%}) in a bad year."
                for c in plan.RISK_CHOICES.values()
            ]
            choice = st.radio(
                "Which sounds most like the family?", keys, index=keys.index(a["risk"]),
                format_func=lambda k: plan.RISK_CHOICES[k]["headline"], captions=captions,
            )
            submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        a["risk"] = choice
        _advance()
    _back_button()

# ---- Step 4: safety net -------------------------------------------------------------------------------------------------
elif step == 3:
    with st.container(border=True):
        with st.form("plan_form_3", border=False):
            st.html(ui.card_title("Your safety net"))
            months = st.slider(
                "How many months of spending should always be within easy reach?", 3, 36, int(a["months"]), 1,
                help="Counted: cash, liquid funds, bonds and gold. Shares are not counted, because they can be down exactly when the money is needed.",
            )
            st.caption("Planned commitments in that window are added on top of ordinary spending.")
            submitted = st.form_submit_button("Continue", type="primary")
    if submitted:
        a["months"] = months
        _advance()
    _back_button()

# ---- Step 5: what you own ------------------------------------------------------------------------------------------------
elif step == 4:
    amounts = a["amounts"] or plan.typical_split(a["wealth"])
    labels = {c: plan.INSTRUMENTS[c][0] for c in ASSET_CLASSES + [ILLIQUID]}
    with st.container(border=True):
        st.html(ui.card_title("What does the family own today? (₹ Cr)"))
        st.caption(
            f"We started with a typical split of {ui.cr(a['wealth'], 0)}. Change anything that is different. "
            "A rough picture is enough."
        )
        with st.form("plan_form_4", border=False):
            entered = {}
            for names in (ASSET_CLASSES[:3], ASSET_CLASSES[3:] + [ILLIQUID]):
                for col, asset in zip(st.columns(3), names):
                    entered[asset] = col.number_input(labels[asset], 0.0, 1_000_000.0, float(amounts[asset]), 1.0, key=f"plan_amt_{asset}")
            submitted = st.form_submit_button("See my strategies", type="primary")
    if submitted:
        trial = {**a, "amounts": entered}
        problems = plan.validate_answers(trial)
        if problems:
            for problem in problems:
                st.error(problem, icon=":material/error:")
        else:
            a["amounts"] = entered
            if abs(sum(entered.values()) - a["wealth"]) > max(0.5, 0.01 * a["wealth"]):
                st.session_state["plan_note"] = (
                    f"These add up to {ui.cr(sum(entered.values()))}, so the plan uses that as the total "
                    f"(you said {ui.cr(a['wealth'])} earlier)."
                )
            _advance()
    _back_button()

# ---- Step 6: strategies ----------------------------------------------------------------------------------------------------
else:
    try:
        profile = plan.profile_from_answers(a)
    except ValueError as err:
        st.error(str(err))
        st.button("Back", on_click=_go, args=(-1,), key="plan_back_err")
        st.stop()

    if note := st.session_state.pop("plan_note", None):
        st.info(note, icon=":material/info:")

    # Each strategy is built for its own comfort level, so A, B and C genuinely differ.
    variants = {k: plan.variant_profile(profile, k) for k in plan.RISK_CHOICES}
    portfolio_of = {
        k: next(p for p in session.analyse(variants[k], "strict")["portfolios"] if p.label == plan.RISK_CHOICES[k]["portfolio"])
        for k in plan.RISK_CHOICES
    }
    chosen = plan.RISK_CHOICES[a["risk"]]
    st.html(
        f'<div class="fo-card-title">Three ways to run {ui.cr(profile.corpus_cr, 0)}</div>'
        f'<div class="fo-muted" style="margin-bottom:.8rem">Based on what you told us, <b>Strategy {chosen["strategy"]}</b> '
        f"fits best. The other two show what you would give up or gain by taking less or more risk.</div>"
    )

    chart_rows, columns = [], st.columns(3, gap="medium")
    for col, key in zip(columns, plan.RISK_CHOICES):
        spec, pf, variant = plan.RISK_CHOICES[key], portfolio_of[key], variants[key]
        year = plan.rolling_year_range(pf.replay_returns)
        crash = engine.run_scenarios(variant, pf).set_index("Scenario").loc["Market crash"]
        within = pf.max_dd <= profile.max_drawdown
        badge = (ui.pill("Recommended for you", "good") if key == a["risk"] else "") + (
            ui.pill("Within your comfort", "good") if within else ui.pill("Beyond your comfort", "warn")
        )
        rows = [
            ("Expected a year", f"{ui.pct(pf.exp_return)} ({ui.pct(pf.exp_real)} after inflation)"),
            ("Worst year in the history", ui.signed_pct(year["worst"])),
            ("In a crash like 2020", f"{ui.signed_pct(crash['Portfolio value change'])} ({ui.signed_cr(crash['Value change (INR cr)'])})"),
            ("Safety net", f"{pf.available_cover_cr / pf.required_cover_cr:.1f}x what you need"),
            ("Meets your return goal", "Yes" if pf.exp_real >= profile.target_real_return else "Not quite"),
        ]
        col.html(
            ui.strategy_card(
                spec["strategy"], spec["headline"], badge,
                f"{ui.signed_pct(year['low'])} to {ui.signed_pct(year['high'])}",
                "In a typical year (the middle 80% of years in the history)", rows, on=(key == a["risk"]),
            )
        )
        chart_rows.append({"name": STRATEGY_LABELS[key], **year})

    st.space("small")
    with st.container(border=True):
        st.html(ui.card_title("How a year can turn out"))
        st.plotly_chart(
            ui.range_chart(chart_rows), width="stretch",
            alt="For each strategy, the typical yearly return range, the median year and the worst year in the history",
        )
        st.caption("Bar: the typical year (middle 80% of years). White dot: the median year. Red cross: the worst year in the history.")

    st.space("medium")
    pick = st.segmented_control(
        "See exactly what to buy for", list(STRATEGY_LABELS.values()), default=STRATEGY_LABELS[a["risk"]],
        required=True, key="plan_detail",
    )
    detail_key = next(k for k, v in STRATEGY_LABELS.items() if v == pick)
    detail_spec, pf, variant = plan.RISK_CHOICES[detail_key], portfolio_of[detail_key], variants[detail_key]
    left, right = st.columns([4, 5], gap="large")
    with left:
        with st.container(border=True):
            st.html(ui.card_title(f"Strategy {detail_spec['strategy']}: your money afterwards"))
            st.plotly_chart(
                ui.donut(pf.weights_total, ui.cr(variant.corpus_cr, 0)), width="stretch",
                alt="Donut chart of the allocation under the selected strategy",
            )
    with right:
        with st.container(border=True):
            st.html(ui.card_title("What to buy and sell"))
            st.html(ui.buy_rows(engine.action_plan(variant, pf), plan.INSTRUMENTS, variant.illiquid_share * variant.corpus_cr))
            st.caption("Kinds of product, not specific recommendations. Illustrative, on sample data.")

    st.space("medium")
    st.html(ui.card_title(f"Why Strategy {detail_spec['strategy']}"))
    for line in plan.describe_strategy(variant, pf, detail_key):
        st.html(ui.note_card(line))
    if variant.one_offs:
        listing = ", ".join(f"{kind.lower()} in {year} years ({ui.cr(amount)})" for kind, year, amount in a["commitments"])
        st.html(ui.note_card(f"Your upcoming commitments are built in: {listing}.", "good"))

    st.space("medium")

    def _save() -> None:
        named = replace(variant, name=f"{profile.name} · Strategy {detail_spec['strategy']}")
        new_id = accounts.add_profile(session.user()["id"], named)
        st.session_state.setdefault("plan_saved", {})[detail_key] = new_id
        st.session_state["active_profile_id"] = new_id
        st.session_state["rec_label"] = detail_spec["portfolio"]

    saved = st.session_state.get("plan_saved", {})
    done = detail_key in saved
    buttons = st.columns([3, 2, 3])
    buttons[0].button(
        f"Strategy {detail_spec['strategy']} saved to your profiles" if done else f"Save Strategy {detail_spec['strategy']} to my profiles",
        type="primary", on_click=_save, disabled=done,
        icon=":material/check:" if done else ":material/bookmark_add:", width="stretch",
    )
    buttons[1].button("Start over", on_click=_restart, icon=":material/restart_alt:", width="stretch")
    if saved:
        st.success("Saved. It is now your active profile, so every page shows this plan.", icon=":material/check_circle:")
        links = st.columns(4)
        links[0].page_link("app_pages/overview.py", label="Overview", icon=":material/space_dashboard:")
        links[1].page_link("app_pages/recommendation.py", label="Recommendation", icon=":material/auto_graph:")
        links[2].page_link("app_pages/risk_liquidity.py", label="Risk and liquidity", icon=":material/shield:")
        links[3].page_link("app_pages/scenarios.py", label="Scenarios", icon=":material/bolt:")
    _back_button()

st.caption("Illustrative simulation on sample data, not investment advice.")
