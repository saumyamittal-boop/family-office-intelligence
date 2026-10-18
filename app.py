"""Family Office Intelligence: prototype entry point.

Run with:  streamlit run app.py
Synthetic sample data and fictional demo families. An illustrative simulation, not investment advice.
"""
import streamlit as st

from fo import session, settings, ui

st.set_page_config(page_title="Family Office Intelligence", page_icon=":material/account_balance:", layout="wide")
ui.inject_css()
session.init()

account = session.user()

if settings.access_code() and not st.session_state.get("access_ok"):
    page = st.navigation([st.Page("app_pages/gate.py", title="Access", icon=":material/lock:")], position="hidden")
elif account is None:
    page = st.navigation(
        [st.Page("app_pages/login.py", title="Log in", icon=":material/login:")], position="hidden"
    )
else:
    with st.sidebar:
        st.html('<div class="fo-brand">Family Office <b>Intelligence</b></div>')
        label = account["username"] + (" (demo)" if account["is_demo"] else "")
        st.caption(f"Signed in as {label}")

        items = session.profiles()
        ids = [pid for pid, _ in items]
        names = {pid: p.name for pid, p in items}
        active = st.session_state.get("active_profile_id")
        if active not in ids:
            active = ids[0]
        chosen = st.selectbox("Family profile", ids, index=ids.index(active), format_func=lambda i: names[i])
        st.session_state["active_profile_id"] = chosen

        st.toggle(
            "Stricter liquidity cover",
            key="strict_cover",
            help="Count only cash, debt and gold towards the liquidity cover. Equities are excluded.",
        )
        st.divider()
        st.button("Log out", on_click=session.log_out, icon=":material/logout:", width="stretch")
        st.caption("Illustrative simulation, not investment advice. Synthetic sample data.")

    plan_page = st.Page("app_pages/plan.py", title="Plan my money", icon=":material/explore:")
    page = st.navigation(
        [
            st.Page("app_pages/overview.py", title="Overview", icon=":material/space_dashboard:", default=True),
            plan_page,
            st.Page("app_pages/recommendation.py", title="Recommendation", icon=":material/auto_graph:"),
            st.Page("app_pages/risk_liquidity.py", title="Risk and liquidity", icon=":material/shield:"),
            st.Page("app_pages/scenarios.py", title="Scenarios", icon=":material/bolt:"),
            st.Page("app_pages/profile.py", title="Family profile", icon=":material/groups:"),
        ],
        position="top",
    )
    if st.session_state.pop("go_plan", False):  # a brand-new account starts with the guided plan
        st.switch_page(plan_page)

page.run()
