import streamlit as st

from fo import accounts, security, session, settings

left, right = st.columns([6, 5], gap="large", vertical_alignment="center")

with left:
    st.html(
        """
        <div class="fo-brand" style="margin-bottom:2.2rem">Family Office <b>Intelligence</b></div>
        <div class="fo-login-title">Your family's wealth,<br><span>in one place.</span></div>
        <div class="fo-login-lead">Decide how to spread capital across asset classes, keep enough liquidity for
        what is coming, and stress-test the plan. Every recommendation comes with its reasons.</div>
        <div class="fo-feature"><span class="fo-feature-dot"></span><div><b>See the whole picture.</b>
        Net worth, allocation, risk and upcoming outflows on one screen.</div></div>
        <div class="fo-feature"><span class="fo-feature-dot"></span><div><b>Know what to do next.</b>
        A clear buy and sell plan towards a mix that fits your limits.</div></div>
        <div class="fo-feature"><span class="fo-feature-dot"></span><div><b>Test the downside.</b>
        Market crashes, rate spikes and big expenses, before they happen.</div></div>
        """
    )

with right:
    with st.container(border=True):
        tab_in, tab_new = st.tabs(["Log in", "Create account"])
        with tab_in:
            with st.form("login_form", border=False):
                username = st.text_input("Username", key="login_user")
                password = st.text_input("Password", type="password", key="login_pass")
                submitted = st.form_submit_button("Log in", type="primary", width="stretch")
            if submitted:
                tries = session.throttle("login")
                key = username.strip().lower()
                wait = tries.blocked_for(key)
                if wait:
                    st.error(f"Too many attempts. Try again in {security.minutes(wait)} minute(s).", icon=":material/lock_clock:")
                else:
                    found = accounts.authenticate(username, password)
                    if found:
                        tries.reset(key)
                        session.log_in(found)
                        st.rerun()
                    else:
                        tries.record_failure(key)
                        st.error("Wrong username or password.")
        with tab_new:
            with st.form("signup_form", border=False):
                new_user = st.text_input("Choose a username", key="signup_user")
                new_pass = st.text_input(
                    "Choose a password", type="password", key="signup_pass",
                    help=f"At least {accounts.MIN_PASSWORD_LENGTH} characters.",
                )
                created = st.form_submit_button("Create account", type="primary", width="stretch")
            if created:
                try:
                    session.log_in(accounts.create_user(new_user, new_pass, max_accounts=settings.max_accounts()))
                    st.session_state["go_plan"] = True
                    st.rerun()
                except ValueError as err:
                    st.error(str(err))

    st.html('<div class="fo-muted" style="margin:1rem 0 .4rem">Or explore a demo family</div>')
    demo_names = {
        "legacy": "Legacy-conservative family",
        "business": "Business-heavy family",
        "nextgen": "Next-gen growth family",
        "gap": "₹1,000 Cr liquidity-gap example",
    }
    for username, label in demo_names.items():
        if st.button(label, key=f"demo_{username}", width="stretch", icon=":material/arrow_forward:"):
            session.log_in(accounts.demo_user(username))
            st.rerun()
    st.caption(
        "Prototype with synthetic data only. Do not reuse a real password, and do not enter real client data."
    )
