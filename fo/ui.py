"""Look and feel: clean white canvas, one green accent, soft cards, pill buttons.

Style patterns are inspired by IndMoney's public site. Only layout and style ideas are borrowed;
no logos, names or assets. Everything user-supplied is HTML-escaped before it reaches st.html.
"""
from __future__ import annotations

import html
from decimal import ROUND_HALF_UP, Decimal

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from .data import ASSET_CLASSES

GREEN, INK, MUTED, LINE, SURFACE = "#089958", "#121313", "#757779", "#E6E8EA", "#F5F6F7"
ILLIQUID = "Illiquid"
ASSET_COLORS = {
    "Large-cap equity": "#089958",
    "Mid-cap equity": "#6CC5A0",
    "Debt": "#1890FF",
    "Gold": "#F5A623",
    "Cash & liquid": "#B5B8BC",
    ILLIQUID: "#212529",
}

CSS = """
.fo-steps { display: flex; gap: .4rem; flex-wrap: wrap; margin: .2rem 0 1.2rem; }
.fo-step { border-radius: 999px; padding: .25rem .8rem; font-size: .8rem; font-weight: 600; background: #F0F1F2; color: #757779; }
.fo-step.done { background: #E6F6EE; color: #067A46; }
.fo-step.now { background: #121313; color: #FFFFFF; }

.fo-strat { background: #F5F6F7; border-radius: 22px; padding: 20px 20px 12px; height: 100%; border: 2px solid transparent; }
.fo-strat.on { background: #F1FAF5; border-color: #089958; }
.fo-strat-head { display: flex; align-items: center; gap: .7rem; margin-bottom: .45rem; }
.fo-strat-letter { width: 34px; height: 34px; border-radius: 50%; background: #121313; color: #FFFFFF; flex: none;
  display: inline-flex; align-items: center; justify-content: center; font-weight: 800; }
.fo-strat.on .fo-strat-letter { background: #089958; }
.fo-strat-name { font-weight: 700; font-size: 1.05rem; }
.fo-strat-big { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; margin-top: .6rem; }
.fo-strat-biglabel { font-size: .8rem; color: #757779; margin-bottom: .5rem; }
.fo-kv { display: flex; justify-content: space-between; gap: 1rem; padding: .45rem 0; border-top: 1px solid rgba(0,0,0,.06); font-size: .9rem; }
.fo-kv span { color: #757779; }
.fo-kv b { font-weight: 600; text-align: right; }

.modebar-container { display: none !important; }
.fo-muted { color: #757779; }
.fo-h1 { font-size: 1.9rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.15; }
.fo-h1-sub { color: #757779; margin-top: .15rem; }
.fo-card-title { font-size: 1.05rem; font-weight: 700; letter-spacing: -0.01em; margin-bottom: .35rem; }
.fo-brand { font-weight: 800; font-size: 1.2rem; letter-spacing: -0.02em; }
.fo-brand b { color: #089958; }

.st-key-hero { background: linear-gradient(135deg, #0D1A14 0%, #11261D 55%, #0B4D31 100%);
  border-radius: 24px; padding: 28px 32px; color: #FFFFFF; }
.fo-hero-label { font-size: .9rem; color: rgba(255,255,255,.65); }
.fo-hero-value { font-size: 2.8rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.08; margin: .25rem 0 .7rem; color: #FFFFFF; }
.fo-hero-sub { margin-top: .9rem; font-size: .9rem; color: rgba(255,255,255,.7); }
.fo-hero-sub b { color: #FFFFFF; font-weight: 600; }

.fo-pill { display: inline-flex; align-items: center; gap: .3rem; border-radius: 999px; padding: .18rem .7rem;
  font-size: .78rem; font-weight: 600; margin: 0 .35rem .25rem 0; white-space: nowrap; }
.fo-pill.good { background: #E6F6EE; color: #067A46; }
.fo-pill.warn { background: #FEF3E2; color: #A15C00; }
.fo-pill.bad  { background: #FDECEC; color: #C62F34; }
.fo-pill.info { background: #E8F3FF; color: #1070D0; }
.fo-pill.neutral { background: #F0F1F2; color: #4B4F53; }
.fo-pill.on-dark { background: rgba(52,211,153,.18); color: #7CE0B0; }
.fo-pill.on-dark-soft { background: rgba(255,255,255,.12); color: #FFFFFF; }

.fo-row { display: flex; align-items: center; gap: .85rem; padding: .72rem 0; border-bottom: 1px solid #F0F1F2; }
.fo-row:last-child { border-bottom: none; }
.fo-dot { width: 12px; height: 12px; border-radius: 50%; flex: none; }
.fo-row-main { flex: 1; min-width: 0; }
.fo-row-title { font-weight: 600; }
.fo-row-sub { font-size: .8rem; color: #757779; }
.fo-row-end { text-align: right; }
.fo-num { font-weight: 600; font-variant-numeric: tabular-nums; }

.fo-stat { background: #F5F6F7; border-radius: 18px; padding: 16px 18px; height: 100%; }
.fo-stat-label { font-size: .8rem; color: #757779; }
.fo-stat-value { font-size: 1.65rem; font-weight: 800; letter-spacing: -0.02em; margin-top: .1rem; }
.fo-stat-sub { font-size: .8rem; color: #757779; margin-top: .15rem; }
.fo-stat.good .fo-stat-value { color: #067A46; }
.fo-stat.warn .fo-stat-value { color: #A15C00; }

.fo-insight { border-radius: 16px; padding: 14px 16px; margin-bottom: 10px; background: #F5F6F7; border-left: 4px solid #B5B8BC; }
.fo-insight.good { border-left-color: #089958; background: #F1FAF5; }
.fo-insight.warn { border-left-color: #F5A623; background: #FFF8EC; }
.fo-insight.info { border-left-color: #1890FF; background: #F1F8FF; }
.fo-insight-title { font-weight: 700; margin-bottom: 2px; }
.fo-insight-body { font-size: .9rem; color: #3D4043; line-height: 1.45; }

.fo-meter { height: 12px; border-radius: 999px; background: #E9EBED; position: relative; }
.fo-meter-fill { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 999px; }
.fo-meter-mark { position: absolute; top: -5px; bottom: -5px; width: 3px; background: #121313; border-radius: 2px; }
.fo-meter-legend { display: flex; justify-content: space-between; font-size: .8rem; color: #757779; margin-top: .45rem; }

.fo-bar { height: 8px; border-radius: 999px; background: #E9EBED; overflow: hidden; }
.fo-bar > div { height: 100%; border-radius: 999px; background: #089958; }

.fo-scn { background: #F5F6F7; border-radius: 20px; padding: 18px 18px 12px; height: 100%; }
.fo-scn-name { font-weight: 700; }
.fo-scn-desc { font-size: .8rem; color: #757779; min-height: 2.4em; margin: .1rem 0 .5rem; }
.fo-scn-big { font-size: 2rem; font-weight: 800; letter-spacing: -0.02em; line-height: 1.1; }
.fo-scn-big.neg { color: #C62F34; }
.fo-scn-big.pos { color: #067A46; }

.fo-login-title { font-size: 2.9rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.08; }
.fo-login-title span { color: #089958; }
.fo-login-lead { font-size: 1.05rem; color: #55595C; margin: 1rem 0 1.4rem; max-width: 32rem; }
.fo-feature { display: flex; gap: .7rem; align-items: flex-start; margin-bottom: .8rem; }
.fo-feature-dot { width: 10px; height: 10px; border-radius: 50%; background: #089958; margin-top: .45rem; flex: none; }
"""


def inject_css() -> None:
    st.html(f"<style>{CSS}</style>")


# ---- Formatting ----------------------------------------------------------------------------------
def esc(text) -> str:
    return html.escape(str(text))


def cr(value: float, digits: int = 1) -> str:
    return f"₹{value:,.{digits}f} Cr"


def _half_up(value: float, digits: int) -> str:
    """Round half up on the decimal text, so 13.75 shows as 13.8 (float formatting would give 13.7)."""
    value = float(value)  # numpy floats have a repr that Decimal cannot read
    if value != value or value in (float("inf"), float("-inf")):
        return "n/a"
    exact = Decimal(str(round(value, 9)))
    return str(exact.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def pct(value: float, digits: int = 1) -> str:
    text = _half_up(value * 100, digits)
    return text if text == "n/a" else f"{text}%"


def signed_cr(value: float, digits: int = 1) -> str:
    sign = "+" if value >= 0 else "−"
    return f"{sign}₹{abs(value):,.{digits}f} Cr"


def signed_pct(value: float, digits: int = 1) -> str:
    text = _half_up(abs(float(value)) * 100, digits)
    if text == "n/a":
        return text
    return f"{'+' if value >= 0 else '−'}{text}%"


# ---- HTML pieces ---------------------------------------------------------------------------------
def pill(text: str, tone: str = "neutral") -> str:
    return f'<span class="fo-pill {tone}">{esc(text)}</span>'


def title_block(title: str, sub: str = "") -> str:
    sub_html = f'<div class="fo-h1-sub">{esc(sub)}</div>' if sub else ""
    return f'<div style="margin-bottom:1rem"><div class="fo-h1">{esc(title)}</div>{sub_html}</div>'


def card_title(text: str) -> str:
    return f'<div class="fo-card-title">{esc(text)}</div>'


def stat_tile(label: str, value: str, sub: str = "", tone: str = "") -> str:
    return (
        f'<div class="fo-stat {tone}"><div class="fo-stat-label">{esc(label)}</div>'
        f'<div class="fo-stat-value">{esc(value)}</div><div class="fo-stat-sub">{esc(sub)}</div></div>'
    )


def insight_card(item: dict) -> str:
    return (
        f'<div class="fo-insight {esc(item["tone"])}"><div class="fo-insight-title">{esc(item["title"])}</div>'
        f'<div class="fo-insight-body">{esc(item["body"])}</div></div>'
    )


def note_card(body: str, tone: str = "info") -> str:
    """An insight-style card with no title."""
    return f'<div class="fo-insight {esc(tone)}"><div class="fo-insight-body">{esc(body)}</div></div>'


def legend_rows(weights_total: dict, corpus_cr: float) -> str:
    rows = []
    for name in ASSET_CLASSES + [ILLIQUID]:
        share = weights_total.get(name, 0.0)
        if share < 0.0005:
            continue
        label = "Illiquid (fixed)" if name == ILLIQUID else name
        rows.append(
            f'<div class="fo-row"><span class="fo-dot" style="background:{ASSET_COLORS[name]}"></span>'
            f'<div class="fo-row-main"><div class="fo-row-title">{esc(label)}</div></div>'
            f'<div class="fo-row-end"><div class="fo-num">{cr(share * corpus_cr)}</div>'
            f'<div class="fo-row-sub">{pct(share)}</div></div></div>'
        )
    return "".join(rows)


def plan_rows(plan, compact: bool = False) -> str:
    """Rows of an action plan DataFrame (see engine.action_plan)."""
    rows = []
    for _, r in plan.iterrows():
        change = r["Change (INR cr)"]
        if abs(change) < 0.5:
            action = pill("Hold", "neutral")
        elif change > 0:
            action = pill(f"Buy {cr(change)}", "good")
        else:
            action = pill(f"Sell {cr(-change)}", "bad")
        sub = f'{pct(r["Current share"])} now → {pct(r["Recommended share"])}'
        amounts = "" if compact else f'<div class="fo-row-sub">{cr(r["Current (INR cr)"])} → {cr(r["Recommended (INR cr)"])}</div>'
        rows.append(
            f'<div class="fo-row"><span class="fo-dot" style="background:{ASSET_COLORS[r["Asset class"]]}"></span>'
            f'<div class="fo-row-main"><div class="fo-row-title">{esc(r["Asset class"])}</div>'
            f'<div class="fo-row-sub">{sub}</div>{amounts}</div><div class="fo-row-end">{action}</div></div>'
        )
    return "".join(rows)


def meter(value: float, limit: float, left_label: str, right_label: str) -> str:
    """A bar for `value` against a marked `limit` (both fractions). Green inside the limit, red beyond it."""
    scale = max(limit * 1.5, value * 1.1, 0.01)
    fill = min(value / scale, 1.0) * 100
    mark = min(limit / scale, 1.0) * 100
    colour = "#089958" if value <= limit else "#E5484D"
    return (
        f'<div class="fo-meter"><div class="fo-meter-fill" style="width:{fill:.1f}%;background:{colour}"></div>'
        f'<div class="fo-meter-mark" style="left:{mark:.1f}%"></div></div>'
        f'<div class="fo-meter-legend"><span>{esc(left_label)}</span><span>{esc(right_label)}</span></div>'
    )


def outflow_rows(table) -> str:
    peak = max(float(table["Total (INR cr)"].max()), 1e-9)
    rows = []
    for _, r in table.iterrows():
        tag = pill("One-off", "warn") if r["One-off (INR cr)"] > 0 else pill("Spending", "neutral")
        rows.append(
            f'<div class="fo-row"><div class="fo-row-main"><div class="fo-row-title">Year {int(r["Year"])} {tag}</div>'
            f'<div class="fo-bar" style="margin-top:.4rem"><div style="width:{r["Total (INR cr)"] / peak * 100:.0f}%"></div></div></div>'
            f'<div class="fo-row-end"><div class="fo-num">{cr(r["Total (INR cr)"])}</div></div></div>'
        )
    return "".join(rows)


# ---- Charts --------------------------------------------------------------------------------------
def style_fig(fig: go.Figure, height: int = 320, dark: bool = False) -> go.Figure:
    ink = "#D5DDD8" if dark else INK
    grid = "rgba(255,255,255,.08)" if dark else "#EEF0F1"
    fig.update_layout(
        font=dict(family="Inter, sans-serif", color=ink, size=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=16, b=16, l=8, r=8),
        height=height,
        hoverlabel=dict(font_family="Inter, sans-serif"),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=grid)
    fig.update_yaxes(gridcolor=grid, zeroline=False)
    return fig


def donut(weights_total: dict, centre_text: str, height: int = 250) -> go.Figure:
    names = [n for n in ASSET_CLASSES + [ILLIQUID] if weights_total.get(n, 0.0) >= 0.0005]
    fig = go.Figure(
        go.Pie(
            labels=names,
            values=[weights_total[n] for n in names],
            hole=0.72,
            sort=False,
            direction="clockwise",
            marker=dict(colors=[ASSET_COLORS[n] for n in names], line=dict(color="#FFFFFF", width=3)),
            textinfo="none",
            hovertemplate="%{label}<br>%{percent}<extra></extra>",
        )
    )
    fig.update_layout(
        showlegend=False,
        annotations=[
            dict(text=f"<b>{centre_text}</b>", showarrow=False, font=dict(size=22, family="Inter, sans-serif"), y=0.55),
            dict(text="Total corpus", showarrow=False, font=dict(size=12, color=MUTED, family="Inter, sans-serif"), y=0.40),
        ],
    )
    return style_fig(fig, height)


def projection_fig(series: dict, height: int = 250) -> go.Figure:
    """Projected corpus lines on the dark hero card. `series` maps a name to a DataFrame from project_corpus."""
    fig = go.Figure()
    palette = ["#9AA5A0", "#34D399"]
    for i, (name, df) in enumerate(series.items()):
        last = i == len(series) - 1
        fig.add_scatter(
            x=df["Year"], y=df["Nominal (INR cr)"], name=name, mode="lines",
            line=dict(color=palette[min(i, 1)], width=3 if last else 2, dash="solid" if last else "dot"),
            fill="tozeroy" if last else None, fillcolor="rgba(52,211,153,0.10)",
            hovertemplate="Year %{x}<br>₹%{y:,.1f} Cr<extra>" + name + "</extra>",
        )
    style_fig(fig, height, dark=True)
    fig.update_layout(legend=dict(orientation="h", y=1.15, x=0, font=dict(color="#D5DDD8")))
    fig.update_xaxes(title_text="Years from today", tickfont=dict(color="rgba(255,255,255,.6)"))
    fig.update_yaxes(tickprefix="₹", ticksuffix=" Cr", tickfont=dict(color="rgba(255,255,255,.6)"))
    return fig


def buy_rows(plan_df, instruments: dict, illiquid_cr: float) -> str:
    """What to buy or sell, named by plain instrument category, from an action plan DataFrame."""
    rows = []
    for _, r in plan_df.iterrows():
        change = r["Change (INR cr)"]
        if abs(change) < 0.5:
            action = pill("Keep", "neutral")
        elif change > 0:
            action = pill(f"Buy {cr(change)}", "good")
        else:
            action = pill(f"Sell {cr(-change)}", "bad")
        name, blurb = instruments[r["Asset class"]]
        rows.append(
            f'<div class="fo-row"><span class="fo-dot" style="background:{ASSET_COLORS[r["Asset class"]]}"></span>'
            f'<div class="fo-row-main"><div class="fo-row-title">{esc(name)}</div><div class="fo-row-sub">{esc(blurb)}</div>'
            f'<div class="fo-row-sub">{cr(r["Current (INR cr)"])} now → <b>{cr(r["Recommended (INR cr)"])}</b></div></div>'
            f'<div class="fo-row-end">{action}</div></div>'
        )
    name, blurb = instruments[ILLIQUID]
    rows.append(
        f'<div class="fo-row"><span class="fo-dot" style="background:{ASSET_COLORS[ILLIQUID]}"></span>'
        f'<div class="fo-row-main"><div class="fo-row-title">{esc(name)}</div><div class="fo-row-sub">{esc(blurb)}</div>'
        f'<div class="fo-row-sub">{cr(illiquid_cr)}</div></div><div class="fo-row-end">{pill("Keep", "neutral")}</div></div>'
    )
    return "".join(rows)


def steps(labels: list[str], current: int) -> str:
    """A row of progress pills for a multi-step flow."""
    pills = []
    for i, label in enumerate(labels):
        cls = "done" if i < current else ("now" if i == current else "")
        mark = "✓ " if i < current else f"{i + 1}. "
        pills.append(f'<span class="fo-step {cls}">{mark}{esc(label)}</span>')
    return f'<div class="fo-steps">{"".join(pills)}</div>'


def strategy_card(letter: str, name: str, badge: str, headline: str, headline_label: str, rows: list, on: bool = False) -> str:
    lines = "".join(f'<div class="fo-kv"><span>{esc(k)}</span><b>{esc(v)}</b></div>' for k, v in rows)
    return (
        f'<div class="fo-strat {"on" if on else ""}"><div class="fo-strat-head">'
        f'<span class="fo-strat-letter">{esc(letter)}</span><div class="fo-strat-name">{esc(name)}</div></div>'
        f"<div>{badge}</div><div class=\"fo-strat-big\">{esc(headline)}</div>"
        f'<div class="fo-strat-biglabel">{esc(headline_label)}</div>{lines}</div>'
    )


def compare_chart(table, recommended: str, height: int = 280) -> go.Figure:
    """Side by side: what each option changes by in a scenario (left) and the growth it expects (right)."""
    colours = {"Current": "#B5B8BC", "Growth": "#089958", "Balanced": "#1890FF", "Defensive": "#212529"}
    names = [f"{o} (recommended)" if o == recommended else o for o in table["Option"]]
    palette = [colours.get(o, "#6CC5A0") for o in table["Option"]]
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.06,
        subplot_titles=("Change in this scenario (₹ Cr)", "Expected return a year"),
    )
    fig.add_bar(
        x=table["Value change (INR cr)"], y=names, orientation="h", marker_color=palette, showlegend=False,
        text=[f"{v:+,.1f}" for v in table["Value change (INR cr)"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:+,.1f} Cr<extra></extra>", row=1, col=1,
    )
    fig.add_bar(
        x=table["Expected return"] * 100, y=names, orientation="h", marker_color=palette, showlegend=False,
        text=[f"{v * 100:.1f}%" for v in table["Expected return"]], textposition="outside", cliponaxis=False,
        hovertemplate="%{y}: %{x:.1f}% a year<extra></extra>", row=1, col=2,
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(zeroline=True, zerolinecolor="#B5B8BC", row=1, col=1)
    worst = float(min(table["Value change (INR cr)"].min(), 0.0))
    best = float(max(table["Value change (INR cr)"].max(), 0.0))
    fig.update_xaxes(range=[worst * 1.4 if worst < 0 else 0, best * 1.2 if best > 0 else 0], row=1, col=1)  # room for labels
    for annotation in fig.layout.annotations:
        annotation.font = dict(size=13, family="Inter, sans-serif", color=INK)
    style_fig(fig, height)
    fig.update_layout(bargap=0.35, margin=dict(t=40, b=16, l=8, r=56))  # after style_fig, which resets the margin
    return fig


def range_chart(rows: list, height: int = 230) -> go.Figure:
    """For each strategy: the typical-year range as a bar, the median as a dot, the worst year as a cross."""
    fig = go.Figure()
    for r, colour in zip(rows, ["#6CC5A0", "#089958", "#212529"]):
        fig.add_scatter(x=[r["low"] * 100, r["high"] * 100], y=[r["name"]] * 2, mode="lines", showlegend=False,
                        line=dict(color=colour, width=18), hoverinfo="skip")
        fig.add_scatter(x=[r["median"] * 100], y=[r["name"]], mode="markers", showlegend=False,
                        marker=dict(color="white", size=12, line=dict(color=colour, width=3)),
                        hovertemplate="Median year: %{x:.1f}%<extra></extra>")
        fig.add_scatter(x=[r["worst"] * 100], y=[r["name"]], mode="markers", showlegend=False,
                        marker=dict(symbol="x", color="#E5484D", size=11, line=dict(width=2.5)),
                        hovertemplate="Worst year in the history: %{x:.1f}%<extra></extra>")
    fig.update_xaxes(title_text="Return over a year (%)", zeroline=True, zerolinecolor="#B5B8BC")
    fig.update_yaxes(autorange="reversed")
    return style_fig(fig, height)
