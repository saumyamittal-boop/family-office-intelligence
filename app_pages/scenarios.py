import pandas as pd
import streamlit as st

from fo import engine, session, ui
from fo.data import ASSET_CLASSES

DESCRIPTIONS = {
    "Equities fall 25%": "Shares fall 25% and nothing else changes.",
    "Market crash": "Equities fall sharply and illiquid assets are marked down.",
    "Inflation and rate spike": "Rates and prices jump. Bonds and equities both fall.",
    "Large unexpected expense": "A one-off bill of 8% of the corpus arrives.",
    "Lost decade": "Returns run 4 points a year lower for the whole horizon.",
}

st.html(ui.title_block("Scenarios", "Stress the plan before the market does."))

ctx = session.context()
p = ctx.profile
options = ["Current"] + [pf.label for pf in ctx.portfolios]
choice = st.segmented_control("Portfolio", options, default=ctx.rec.label, required=True, key="scn_choice")
pf = ctx.current if choice == "Current" else next(x for x in ctx.portfolios if x.label == choice)


def scenario_card(row: dict, description: str) -> str:
    change = row["Portfolio value change"]
    cls = "neg" if change < -0.0005 else ("pos" if change > 0.0005 else "")
    if cls:
        headline, subline = ui.signed_pct(change), ui.signed_cr(row["Value change (INR cr)"])
    else:  # no immediate hit: the effect is on long-run purchasing power
        real = row["Real corpus at horizon (x today)"]
        headline, subline = f"{real:.2f}x", "real corpus at the horizon"
        cls = "neg" if real < 1 else "pos"
    pills = (
        ui.pill("Within drawdown limit" if row["Within drawdown limit"] else "Drawdown limit breached",
                "good" if row["Within drawdown limit"] else "bad")
        + ui.pill(f"Liquidity {row['Liquidity cover (x required)']:.1f}x", "good" if row["Cover held"] else "bad")
        + ui.pill(f"Real corpus {row['Real corpus at horizon (x today)']:.2f}x",
                  "good" if row["Real corpus at horizon (x today)"] >= 1 else "warn")
    )
    return (
        f'<div class="fo-scn"><div class="fo-scn-name">{ui.esc(row["Scenario"])}</div>'
        f'<div class="fo-scn-desc">{ui.esc(description)}</div>'
        f'<div class="fo-scn-big {cls}">{headline}</div>'
        f'<div class="fo-row-sub" style="margin-bottom:.6rem">{subline}</div>{pills}</div>'
    )


table = engine.run_scenarios(p, pf)
baseline = table.iloc[0]
st.html(
    ui.pill(f"Baseline: real corpus {baseline['Real corpus at horizon (x today)']:.2f}x of today at the horizon", "neutral")
    + ui.pill(f"Liquidity cover {baseline['Liquidity cover (x required)']:.1f}x", "neutral")
)
st.space("small")
presets = list(table.iloc[1:].iterrows())
for chunk in (presets[:3], presets[3:]):
    for col, (_, row) in zip(st.columns(3, gap="medium"), chunk):
        col.html(scenario_card(row.to_dict(), DESCRIPTIONS[row["Scenario"]]))
    st.space("small")

st.space("medium")

# ---- Build your own ------------------------------------------------------------------------------------------------------
with st.container(border=True):
    st.html(ui.card_title("Build your own scenario"))
    left, right = st.columns(2, gap="large")
    with left:
        equity = st.slider("Equity shock (%)", -60, 20, -25, 1, help="Applied to large-cap; mid-cap moves 25% more.")
        debt = st.slider("Debt shock (%)", -20, 10, -3, 1)
        gold = st.slider("Gold shock (%)", -30, 40, 5, 1)
    with right:
        illiquid = st.slider("Illiquid mark-down (%)", -50, 10, -10, 1)
        expense = st.slider("One-off expense (% of corpus)", 0, 40, 5, 1)
        drag = st.slider("Return drag per year (points)", 0.0, 8.0, 0.0, 0.5)
    custom = {
        "shocks": {
            ASSET_CLASSES[0]: equity / 100,
            ASSET_CLASSES[1]: max(equity * 1.25, -95) / 100,
            ASSET_CLASSES[2]: debt / 100,
            ASSET_CLASSES[3]: gold / 100,
            ASSET_CLASSES[4]: 0.0,
        },
        "illiquid": illiquid / 100,
        "extra_outflow": expense / 100,
        "return_drag": drag / 100,
    }
    result = engine.scenario_row(p, pf, "Your scenario", custom)
    st.html(scenario_card(result, "The shocks set above, applied once to today's holdings."))

st.space("medium")

# ---- Compare options under one scenario ---------------------------------------------------------------------------------------
with st.container(border=True):
    st.html(ui.card_title("Compare your options under one scenario"))
    st.caption("Your current mix against the three recommended options, hit by the same shock.")
    scenario_names = list(engine.SCENARIOS) + ["Your scenario"]
    which = st.segmented_control("Scenario", scenario_names, default=scenario_names[0], required=True, key="cmp_scenario")
    shock = custom if which == "Your scenario" else engine.SCENARIOS[which]
    compared = engine.compare_options(p, [ctx.current] + ctx.portfolios, shock)

    st.plotly_chart(
        ui.compare_chart(compared, ctx.rec.label), width="stretch",
        alt="Bars comparing the current mix and the three options: change in the scenario, and expected return a year",
    )
    for note in engine.comparison_insights(compared):
        st.html(ui.note_card(note["body"], note["tone"]))

    st.dataframe(
        pd.DataFrame(
            {
                "Change": [ui.signed_pct(v) for v in compared["Value change"]],
                "Change (₹ Cr)": [f"{v:+,.1f}" for v in compared["Value change (INR cr)"]],
                "Safety net after (x need)": [f"{v:.1f}x" for v in compared["Liquidity cover after (x required)"]],
                "Safety net held": ["Yes" if v else "No" for v in compared["Cover held"]],
                "Expected return": [ui.pct(v) for v in compared["Expected return"]],
                "Expected real return": [ui.pct(v) for v in compared["Expected real return"]],
                "Worst drawdown in history": [ui.pct(v) for v in compared["Worst drawdown in history"]],
            },
            index=compared["Option"],
        ),
        width="stretch",
        alt="Side-by-side results for the current mix and each recommended option under the chosen scenario",
    )

st.space("medium")
with st.container(border=True):
    st.html(ui.card_title("All results"))
    display = pd.DataFrame(
        {
            "Value change": [ui.signed_pct(v) for v in table["Portfolio value change"]],
            "Value change (₹ Cr)": [f"{v:+,.1f}" for v in table["Value change (INR cr)"]],
            "Within drawdown limit": ["Yes" if v else "No" for v in table["Within drawdown limit"]],
            "Liquidity cover": [f"{v:.1f}x" for v in table["Liquidity cover (x required)"]],
            "Real corpus at horizon": [f"{v:.2f}x" for v in table["Real corpus at horizon (x today)"]],
        },
        index=table["Scenario"],
    )
    st.dataframe(display, width="stretch", alt="Results of each stress scenario on the selected portfolio")
    st.caption(
        "Shock sizes are fixed placeholders in this sample; the full build calibrates them from the data snapshot. "
        "Real corpus at horizon projects the corpus at expected returns less the scenario drag, after outflows and "
        "inflation. Below 1.00x, purchasing power is not preserved."
    )
st.caption("Illustrative simulation, not investment advice.")
