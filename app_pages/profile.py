import pandas as pd
import streamlit as st

from fo import accounts, session, ui
from fo.data import ASSET_CLASSES
from fo.personas import ILLIQUID, IlliquidBucket, Profile, starter_profile

uid = session.user()["id"]
pid, p = session.active_profile()
k = f"p{pid}"


def _new_blank() -> None:
    st.session_state["active_profile_id"] = accounts.add_profile(uid, starter_profile("New profile"))


def _build(inputs: dict) -> tuple[Profile | None, list[str]]:
    """Turn the form values into a Profile, or explain what is wrong."""
    errors: list[str] = []
    name = inputs["name"].strip()
    if not name:
        errors.append("Give the profile a name.")

    holds = {c: v / 100 for c, v in inputs["holdings"].items()}
    total = sum(holds.values())
    if abs(total - 1.0) > 0.005:
        errors.append(f"Holdings add up to {total * 100:.1f}%. They need to add up to 100%.")
    elif total > 0:
        holds = {c: v / total for c, v in holds.items()}
    if holds.get(ILLIQUID, 0) > 0.95:
        errors.append("Illiquid holdings can be at most 95% of the corpus; the model needs a liquid part to allocate.")

    limits = {}
    lim = inputs["limits"]
    for _, row in lim.iterrows():
        lo, hi = float(row["Minimum (%)"]) / 100, float(row["Maximum (%)"]) / 100
        if not (0 <= lo <= hi <= 1):
            errors.append(f"{row['Asset class']}: the minimum must be between 0% and the maximum, and the maximum at most 100%.")
        limits[row["Asset class"]] = (lo, hi)
    if limits and (sum(v[0] for v in limits.values()) > 1 + 1e-9 or sum(v[1] for v in limits.values()) < 1 - 1e-9):
        errors.append("The class limits can't add up to 100% of the liquid part: minimums must total at most 100% "
                      "and maximums at least 100%.")

    one_offs = []
    rows = inputs["one_offs"].dropna(how="any")
    if len(rows) > 3:
        errors.append("Enter at most three one-off outflows.")
    for _, row in rows.iterrows():
        year, amount = int(row["Year"]), float(row["Amount (₹ Cr)"])
        if not 1 <= year <= inputs["horizon"]:
            errors.append(f"A one-off outflow in year {year} is outside the {inputs['horizon']}-year horizon.")
        if amount <= 0:
            errors.append("One-off amounts must be above zero.")
        one_offs.append((year, amount))

    if errors:
        return None, errors
    return (
        Profile(
            key=p.key, name=name, deciding_constraint=p.deciding_constraint, corpus_cr=inputs["corpus"],
            holdings=holds,
            illiquid=IlliquidBucket(inputs["ill_desc"].strip() or "Illiquid holdings", inputs["ill_ret"] / 100,
                                    inputs["ill_vol"] / 100, inputs["lock"], inputs["corr"]),
            annual_spending_cr=inputs["spending"], one_offs=tuple(sorted(one_offs)), horizon_years=inputs["horizon"],
            max_drawdown=inputs["max_dd"] / 100, cover_months=inputs["cover"], limits=limits,
            target_real_return=inputs["target"] / 100,
        ),
        [],
    )


head, action = st.columns([4, 1], vertical_alignment="center")
head.html(ui.title_block("Family profile", "What you own, what you need, and the limits you want respected."))
action.button("New profile", on_click=_new_blank, icon=":material/add:", width="stretch")

if flash := st.session_state.pop("flash", None):
    st.success(flash, icon=":material/check_circle:")
if session.user()["is_demo"]:
    st.caption("This is a demo family. Changes are saved for anyone using this machine's demo accounts.")

with st.form(f"profile_form_{k}"):
    st.html(ui.card_title("Basics"))
    name = st.text_input("Profile name", p.name, max_chars=60)
    c = st.columns(3)
    corpus = c[0].number_input("Total corpus (₹ Cr)", 1.0, 1_000_000.0, float(p.corpus_cr), 5.0)
    spending = c[1].number_input("Annual spending (₹ Cr)", 0.0, 100_000.0, float(p.annual_spending_cr), 0.5)
    horizon = c[2].number_input("Investment horizon (years)", 1, 60, int(p.horizon_years))
    c = st.columns(3)
    max_dd = c[0].number_input("Max tolerable drawdown (%)", 1.0, 80.0, round(p.max_drawdown * 100, 1), 1.0)
    cover = c[1].number_input("Liquidity cover (months of outflows)", 1, 240, int(p.cover_months))
    target = c[2].number_input("Target real return (% a year)", -5.0, 25.0, round(p.target_real_return * 100, 1), 0.5)

    st.html(ui.card_title("Current holdings (% of total corpus)"))
    holdings = {}
    for row_names in (ASSET_CLASSES[:3], ASSET_CLASSES[3:] + [ILLIQUID]):
        cols = st.columns(3)
        for col, asset in zip(cols, row_names):
            holdings[asset] = col.number_input(
                "Illiquid (fixed)" if asset == ILLIQUID else asset, 0.0, 100.0, round(p.holdings[asset] * 100, 2), 1.0,
                key=f"{k}_hold_{asset}",
            )

    st.html(ui.card_title("Illiquid holdings"))
    c = st.columns(4)
    ill_desc = c[0].text_input("What is it?", p.illiquid.description, max_chars=60)
    ill_ret = c[1].number_input("Assumed return (% a year)", -10.0, 40.0, round(p.illiquid.expected_return * 100, 1), 0.5)
    ill_vol = c[2].number_input("Assumed volatility (%)", 0.0, 80.0, round(p.illiquid.volatility * 100, 1), 1.0,
                                help="Appraisal-based values look calmer than the true risk. Treat this as a floor.")
    lock = c[3].number_input("Lock-in (years)", 0, 30, int(p.illiquid.lock_in_years))
    corr = st.slider("Correlation with listed equities", 0.0, 1.0, float(p.illiquid.corr_with_equity), 0.05)

    st.html(ui.card_title("Planned one-off outflows (up to three)"))
    oo = pd.DataFrame(
        {"Year": pd.Series([y for y, _ in p.one_offs], dtype="int64"),
         "Amount (₹ Cr)": pd.Series([a for _, a in p.one_offs], dtype="float64")}
    )
    one_offs = st.data_editor(
        oo, num_rows="dynamic", hide_index=True, width="stretch", key=f"{k}_oneoffs",
        column_config={
            "Year": st.column_config.NumberColumn(min_value=1, max_value=60, step=1),
            "Amount (₹ Cr)": st.column_config.NumberColumn(min_value=0.0, step=1.0),
        },
        alt="Planned one-off outflows by year and amount",
    )

    st.html(ui.card_title("Limits for each asset class (% of the liquid part)"))
    lim = pd.DataFrame(
        {
            "Asset class": ASSET_CLASSES,
            "Minimum (%)": [round(p.limits[a][0] * 100, 1) for a in ASSET_CLASSES],
            "Maximum (%)": [round(p.limits[a][1] * 100, 1) for a in ASSET_CLASSES],
        }
    )
    limits = st.data_editor(
        lim, hide_index=True, width="stretch", disabled=["Asset class"], key=f"{k}_limits",
        column_config={
            "Minimum (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0),
            "Maximum (%)": st.column_config.NumberColumn(min_value=0.0, max_value=100.0, step=1.0),
        },
        alt="Minimum and maximum share allowed for each asset class",
    )
    buttons = st.columns([1, 1, 3])
    save = buttons[0].form_submit_button("Save changes", type="primary", width="stretch")
    save_new = buttons[1].form_submit_button("Save as new", width="stretch")

if save or save_new:
    profile, problems = _build(
        {
            "name": name, "corpus": corpus, "spending": spending, "horizon": int(horizon), "max_dd": max_dd,
            "cover": int(cover), "target": target, "holdings": holdings, "ill_desc": ill_desc, "ill_ret": ill_ret,
            "ill_vol": ill_vol, "lock": int(lock), "corr": corr, "one_offs": one_offs, "limits": limits,
        }
    )
    if problems:
        for problem in problems:
            st.error(problem, icon=":material/error:")
    elif save:
        accounts.save_profile(uid, pid, profile)
        st.session_state["flash"] = "Profile saved. The overview and recommendation now use these numbers."
        st.rerun()
    else:
        st.session_state["active_profile_id"] = accounts.add_profile(uid, profile)
        st.session_state["flash"] = f"Saved as a new profile: {profile.name}."
        st.rerun()

with st.expander("Delete this profile"):
    st.caption("You always keep at least one profile.")
    if st.button("Delete profile", key=f"delete_{k}", icon=":material/delete:"):
        if accounts.delete_profile(uid, pid):
            st.session_state.pop("active_profile_id", None)
            st.rerun()
        else:
            st.error("This is your only profile, so it can't be deleted.")
st.caption("Illustrative simulation, not investment advice. Use synthetic data only.")
