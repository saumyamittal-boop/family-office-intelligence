import numpy as np
import plotly.graph_objects as go
import streamlit as st

from fo import engine, session, ui

st.html(ui.title_block("Risk and liquidity", "How rough the ride has been, and whether cash will be there when it is needed."))

ctx = session.context()
p = ctx.profile
options = ["Current"] + [pf.label for pf in ctx.portfolios]
choice = st.segmented_control("Portfolio", options, default="Current", required=True, key="risk_choice")
pf = ctx.current if choice == "Current" else next(x for x in ctx.portfolios if x.label == choice)

tiles = st.columns(4, gap="medium")
tiles[0].html(ui.stat_tile("Expected return", ui.pct(pf.exp_return), f"{ui.pct(pf.exp_real)} after inflation"))
tiles[1].html(ui.stat_tile("Volatility", ui.pct(pf.vol), "Annual, including illiquid holdings"))
tiles[2].html(
    ui.stat_tile("Worst drawdown", ui.pct(pf.max_dd), "Peak to trough in the sample history", "good" if pf.dd_ok else "warn")
)
tiles[3].html(ui.stat_tile("95% 1-month CVaR", ui.pct(pf.cvar21), "Average loss in the worst 5% of months"))
st.space("medium")

# ---- Drawdown -------------------------------------------------------------------------------------------------------------
with st.container(border=True):
    verdict = ui.pill("Within your limit", "good") if pf.dd_ok else ui.pill("Above your limit", "bad")
    st.html(ui.card_title("Drawdown against your limit") + verdict)
    st.html(
        ui.meter(
            pf.max_dd, p.max_drawdown, f"Worst in history: {ui.pct(pf.max_dd)}", f"Your limit: {ui.pct(p.max_drawdown, 0)}"
        )
    )
    st.space("small")
    r = pf.replay_returns
    value = 100 * np.cumprod(1 + r.to_numpy())
    drawdown = value / np.maximum.accumulate(value) - 1

    left, right = st.columns(2, gap="large")
    with left:
        fig_v = go.Figure(go.Scatter(x=r.index, y=value, mode="lines", line=dict(color=ui.GREEN, width=2.5), name="Value"))
        fig_v.update_layout(title=dict(text="Value of 100 invested", font=dict(size=14)), yaxis_title=None)
        st.plotly_chart(
            ui.style_fig(fig_v, 280), width="stretch", alt="Line chart of the historical value of 100 invested in the portfolio"
        )
    with right:
        fig_d = go.Figure(
            go.Scatter(x=r.index, y=drawdown * 100, fill="tozeroy", mode="lines", line=dict(color="#E5484D", width=1.5),
                       fillcolor="rgba(229,72,77,.15)", name="Drawdown")
        )
        fig_d.add_hline(y=-p.max_drawdown * 100, line_dash="dash", line_color=ui.INK,
                        annotation_text="Your limit", annotation_position="bottom right")
        fig_d.update_layout(title=dict(text="Drawdown from the previous peak (%)", font=dict(size=14)), yaxis_title=None)
        st.plotly_chart(
            ui.style_fig(fig_d, 280), width="stretch", alt="Area chart of historical drawdown with the drawdown limit marked"
        )
    st.caption("Illiquid holdings accrue smoothly in this replay, so real drawdowns would look worse than shown.")

st.space("medium")

# ---- Liquidity ------------------------------------------------------------------------------------------------------------
with st.container(border=True):
    ratio = pf.available_cover_cr / pf.required_cover_cr
    st.html(ui.card_title("Liquidity") + (ui.pill("Cover held", "good") if ratio >= 1 else ui.pill("Shortfall", "bad")))
    cols = st.columns(3, gap="medium")
    cols[0].html(ui.stat_tile("Counted liquid assets", ui.cr(pf.available_cover_cr, 0), "After haircuts"))
    cols[1].html(ui.stat_tile("Needed", ui.cr(pf.required_cover_cr, 0), f"Next {p.cover_months} months of outflows"))
    cols[2].html(ui.stat_tile("Cover", f"{ratio:.1f}x", "Counted assets divided by need", "good" if ratio >= 1.5 else "warn"))
    st.space("small")

    ladder = engine.liquidity_ladder(p, pf, years=min(p.horizon_years, 12))
    fig_l = go.Figure()
    fig_l.add_bar(x=ladder["Year"], y=ladder["Outflows (INR cr)"], name="Outflows", marker_color="#F5A623")
    fig_l.add_scatter(x=ladder["Year"], y=ladder["Liquid sleeve value (INR cr)"], name="Liquid assets", mode="lines+markers",
                      line=dict(color=ui.GREEN, width=3))
    fig_l.update_layout(xaxis_title="Year", yaxis=dict(tickprefix="₹", ticksuffix=" Cr"))
    st.plotly_chart(
        ui.style_fig(fig_l, 300), width="stretch", alt="Yearly outflows against the projected liquid assets"
    )
    if (ladder["Liquid sleeve value (INR cr)"] < 0).any():
        st.error("The liquid assets run out before the end of the ladder at expected returns.", icon=":material/warning:")
    table = ladder.rename(columns={
        "Outflows (INR cr)": "Outflows (₹ Cr)", "Liquid sleeve value (INR cr)": "Liquid assets (₹ Cr)",
        "Months of spending covered": "Months of spending covered",
    }).set_index("Year").round(1)
    st.dataframe(table, width="stretch", alt="Liquidity ladder: yearly outflows, projected liquid assets and months of spending covered")
    st.caption(
        "A steady projection at the portfolio's expected return. Proceeds from illiquid holdings after their lock-in "
        "are not included."
    )
st.caption("Illustrative simulation, not investment advice.")
