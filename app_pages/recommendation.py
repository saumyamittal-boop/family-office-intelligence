import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from fo import engine, session, ui
from fo.data import ASSET_CLASSES


def _remember_choice() -> None:
    st.session_state["rec_label"] = st.session_state["rec_widget"]


labels = ["Growth", "Balanced", "Defensive"]
st.html(ui.title_block("Recommendation", "Three mixes that respect your limits, from more growth to more safety."))
st.segmented_control(
    "Risk level", labels, default=st.session_state.get("rec_label", "Balanced"), required=True,
    key="rec_widget", on_change=_remember_choice,
)

ctx = session.context()
p, cur, rec = ctx.profile, ctx.current, ctx.rec

# ---- Headline numbers for the chosen mix ---------------------------------------------------------------------
tiles = st.columns(4, gap="medium")
tiles[0].html(
    ui.stat_tile(
        "Expected return", ui.pct(rec.exp_return),
        f"{ui.pct(rec.exp_real)} real vs {ui.pct(p.target_real_return)} target", "good" if rec.meets_target else "warn",
    )
)
tiles[1].html(ui.stat_tile("Volatility", ui.pct(rec.vol), f"Now: {ui.pct(cur.vol)}"))
tiles[2].html(
    ui.stat_tile(
        "Worst drawdown in history", ui.pct(rec.max_dd), f"Limit {ui.pct(p.max_drawdown, 0)}  ·  now {ui.pct(cur.max_dd)}",
        "good" if rec.dd_ok else "warn",
    )
)
tiles[3].html(
    ui.stat_tile(
        "Liquidity cover", f"{rec.available_cover_cr / rec.required_cover_cr:.1f}x",
        f"{ui.cr(rec.available_cover_cr, 0)} vs {ui.cr(rec.required_cover_cr, 0)} needed",
    )
)
st.space("medium")

# ---- Allocation and action plan --------------------------------------------------------------------------------------
col_donut, col_plan = st.columns([4, 5], gap="large")
with col_donut:
    with st.container(border=True):
        st.html(ui.card_title(f"{rec.label} allocation"))
        st.plotly_chart(
            ui.donut(rec.weights_total, ui.cr(p.corpus_cr, 0)), width="stretch",
            alt=f"Donut chart of the {rec.label} recommended allocation by asset class",
        )
        st.html(ui.legend_rows(rec.weights_total, p.corpus_cr))
with col_plan:
    with st.container(border=True):
        plan = engine.action_plan(p, rec)
        buys = plan.loc[plan["Change (INR cr)"] > 0.5, "Change (INR cr)"].sum()
        sells = -plan.loc[plan["Change (INR cr)"] < -0.5, "Change (INR cr)"].sum()
        st.html(ui.card_title("Action plan"))
        st.html(
            ui.pill(f"Buy {ui.cr(buys)}", "good") + ui.pill(f"Sell {ui.cr(sells)}", "bad")
            + ui.pill("Illiquid holdings unchanged", "neutral")
        )
        st.html(ui.plan_rows(plan))

st.space("medium")

# ---- Why ---------------------------------------------------------------------------------------------------------------
st.html(ui.card_title(f"Why the {rec.label} mix"))
for line in rec.explanation:
    st.html(ui.note_card(line))

st.space("medium")

# ---- Comparison ---------------------------------------------------------------------------------------------------------
with st.container(border=True):
    st.html(ui.card_title("Compare with your current mix"))
    categories = ASSET_CLASSES + ["Illiquid (fixed)"]
    fig = go.Figure()
    for portfolio, colour in [(cur, "#B5B8BC")] + [(pf, c) for pf, c in zip(ctx.portfolios, ["#089958", "#1890FF", "#212529"])]:
        fig.add_bar(
            name=portfolio.label, x=categories, y=[portfolio.weights_total[c] * 100 for c in ASSET_CLASSES + ["Illiquid"]],
            marker_color=colour,
        )
    fig.update_layout(barmode="group", yaxis_title="% of total corpus")
    st.plotly_chart(
        ui.style_fig(fig, 320), width="stretch",
        alt="Grouped bars comparing the current allocation with the three recommended portfolios by asset class",
    )
    rows = {}
    for portfolio in [cur] + ctx.portfolios:
        rows[portfolio.label] = {
            "Expected return": ui.pct(portfolio.exp_return),
            "Expected real return": ui.pct(portfolio.exp_real),
            "Meets target": "Yes" if portfolio.meets_target else "No",
            "Volatility": ui.pct(portfolio.vol),
            "Worst drawdown": ui.pct(portfolio.max_dd),
            "Within drawdown limit": "Yes" if portfolio.dd_ok else "No",
            "95% 1-month CVaR": ui.pct(portfolio.cvar21),
            "Liquidity counted / needed": f"{portfolio.available_cover_cr:,.0f} / {portfolio.required_cover_cr:,.0f} Cr",
        }
    st.dataframe(
        pd.DataFrame(rows), width="stretch",
        alt="Return, risk, drawdown and liquidity measures for the current mix and the three recommended portfolios",
    )

with st.expander("How these numbers are produced"):
    st.markdown(
        "- Expected returns are a 50/50 blend of the sample history and a long-run assumption.\n"
        "- Risk comes from monthly returns with correlations shrunk towards zero; drawdown and CVaR use the daily history.\n"
        "- A constrained mean-variance optimiser allocates the liquid part. Illiquid holdings stay fixed.\n"
        "- The three mixes sit 75%, 50% and 25% of the way from the safest to the highest-return mix your limits allow.\n"
        "- If the worst drawdown exceeds your limit, risk is tightened until it fits.\n"
        "- Target real return is reported, not enforced."
    )
st.caption("Illustrative simulation, not investment advice.")
