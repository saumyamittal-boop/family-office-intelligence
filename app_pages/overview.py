import streamlit as st

from fo import engine, session, ui

ctx = session.context()
p, cur, rec = ctx.profile, ctx.current, ctx.rec

title_col, plan_col = st.columns([4, 1], vertical_alignment="center")
title_col.html(ui.title_block(f"Welcome back, {session.user()['username']}", p.name))
plan_col.page_link("app_pages/plan.py", label="Plan my money", icon=":material/explore:", width="stretch")

if ctx.source == "sample":
    st.info(
        "Market returns are synthetic and the demo families are fictional.",
        title="Sample data", icon=":material/science:",
    )

# ---- Hero: corpus and projection ------------------------------------------------------------------
with st.container(key="hero"):
    left, right = st.columns([5, 6], vertical_alignment="center", gap="large")
    with left:
        st.html(
            f"""
            <div class="fo-hero-label">Total family corpus</div>
            <div class="fo-hero-value">{ui.cr(p.corpus_cr)}</div>
            <div>{ui.pill(f"{ui.pct(cur.exp_return)} expected a year", "on-dark")}
                 {ui.pill(f"{ui.pct(cur.exp_real)} after inflation", "on-dark-soft")}</div>
            <div class="fo-hero-sub"><b>{ui.cr(p.corpus_cr * p.sleeve_share)}</b> liquid
              &nbsp;·&nbsp; <b>{ui.cr(p.corpus_cr * p.illiquid_share)}</b> illiquid
              &nbsp;·&nbsp; <b>{p.horizon_years}</b> year horizon</div>
            """
        )
    with right:
        st.plotly_chart(
            ui.projection_fig(
                {
                    "Current mix": engine.project_corpus(p, cur.exp_return),
                    f"{rec.label} mix": engine.project_corpus(p, rec.exp_return),
                }
            ),
            width="stretch",
            alt="Projected corpus over the horizon for the current mix and the recommended mix, after planned outflows",
        )

st.space("medium")

# ---- Allocation and what to do -----------------------------------------------------------------------
col_alloc, col_plan = st.columns([4, 5], gap="large")
with col_alloc:
    with st.container(border=True):
        st.html(ui.card_title("Your allocation"))
        st.plotly_chart(
            ui.donut(cur.weights_total, ui.cr(p.corpus_cr, 0)),
            width="stretch",
            alt="Donut chart of the current allocation by asset class",
        )
        st.html(ui.legend_rows(cur.weights_total, p.corpus_cr))
with col_plan:
    with st.container(border=True):
        head, link = st.columns([3, 2], vertical_alignment="center")
        head.html(ui.card_title(f"Towards the {rec.label} mix"))
        link.page_link("app_pages/recommendation.py", label="Full action plan", icon=":material/arrow_forward:")
        st.html(ui.plan_rows(engine.action_plan(p, rec), compact=True))
        st.html(
            f'<div class="fo-row-sub" style="margin-top:.6rem">Illiquid holdings ({ui.pct(p.illiquid_share, 0)} of the corpus) '
            "stay fixed until their lock-in ends.</div>"
        )

st.space("medium")

# ---- Key numbers ---------------------------------------------------------------------------------------
ratio = cur.available_cover_cr / cur.required_cover_cr
tiles = st.columns(4, gap="medium")
tiles[0].html(
    ui.stat_tile(
        "Expected return", ui.pct(cur.exp_return),
        f"{ui.pct(cur.exp_real)} real vs {ui.pct(p.target_real_return)} target", "good" if cur.meets_target else "warn",
    )
)
tiles[1].html(ui.stat_tile("Volatility", ui.pct(cur.vol), f"{rec.label} mix: {ui.pct(rec.vol)}"))
tiles[2].html(
    ui.stat_tile(
        "Worst drawdown in history", ui.pct(cur.max_dd), f"Your limit: {ui.pct(p.max_drawdown, 0)}",
        "good" if cur.dd_ok else "warn",
    )
)
tiles[3].html(
    ui.stat_tile(
        "Liquidity cover", f"{ratio:.1f}x",
        f"{ui.cr(cur.available_cover_cr, 0)} vs {ui.cr(cur.required_cover_cr, 0)} needed",
        "good" if ratio >= 1.5 else "warn",
    )
)

st.space("medium")

# ---- Insights and outflows ---------------------------------------------------------------------------------
col_ins, col_out = st.columns([3, 2], gap="large")
with col_ins:
    with st.container(border=True):
        st.html(ui.card_title("Insights"))
        st.html("".join(ui.insight_card(i) for i in engine.build_insights(p, cur, rec)))
with col_out:
    with st.container(border=True):
        st.html(ui.card_title("Planned outflows, next 5 years"))
        st.html(ui.outflow_rows(engine.upcoming_outflows(p, 5)))
        st.html(
            f'<div class="fo-row-sub" style="margin-top:.6rem">Spending grows with inflation '
            f"({ui.pct(engine.INFLATION)} a year). One-off amounts are as entered.</div>"
        )

st.caption("Illustrative simulation, not investment advice.")
