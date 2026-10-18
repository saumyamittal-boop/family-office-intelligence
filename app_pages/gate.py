import hmac

import streamlit as st

from fo import security, session, settings

_, middle, _ = st.columns([1, 2, 1])
with middle:
    st.html(
        """
        <div class="fo-brand" style="margin:3rem 0 1.4rem">Family Office <b>Intelligence</b></div>
        <div class="fo-h1">This preview is private</div>
        <div class="fo-h1-sub" style="margin-bottom:1.2rem">Enter the access code you were given to continue.</div>
        """
    )
    with st.container(border=True):
        with st.form("gate_form", border=False):
            code = st.text_input("Access code", type="password", key="gate_code")
            submitted = st.form_submit_button("Continue", type="primary", width="stretch")
    if submitted:
        gate = session.throttle("gate")
        wait = gate.blocked_for("gate")
        if wait:
            st.error(f"Too many attempts. Try again in {security.minutes(wait)} minute(s).", icon=":material/lock_clock:")
        elif hmac.compare_digest(code.encode("utf-8"), (settings.access_code() or "").encode("utf-8")):
            gate.reset("gate")
            st.session_state["access_ok"] = True
            st.rerun()
        else:
            gate.record_failure("gate")
            st.error("That code isn't right.", icon=":material/error:")
    st.caption("Ask the project team for the code. This prototype uses synthetic data only.")
