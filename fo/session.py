"""Shared state and cached computation for the app's pages."""
from __future__ import annotations

import json
from dataclasses import dataclass

import streamlit as st

from . import accounts, engine
from .security import Throttle
from .data import load_returns
from .personas import Profile, profile_from_dict, profile_to_dict


@st.cache_resource
def init() -> bool:
    accounts.init_db()
    return True


@st.cache_data
def get_returns():
    return load_returns()


@st.cache_data(max_entries=64, ttl=3600, show_spinner="Running the allocation model...")
def _analyse(profile_json: str, basis: str) -> dict:
    daily, _ = get_returns()
    profile = profile_from_dict(json.loads(profile_json))
    inputs = engine.estimate_inputs(daily)
    return {
        "current": engine.analyse_current(profile, daily, basis, inputs),
        "portfolios": engine.recommend(profile, daily, basis, inputs),
    }


def analyse(profile: Profile, basis: str = "all") -> dict:
    """Cached analysis of any profile (saved or not): {"current": Portfolio, "portfolios": [Portfolio x 3]}."""
    return _analyse(json.dumps(profile_to_dict(profile), sort_keys=True), basis)


@st.cache_resource
def _throttles() -> dict[str, Throttle]:
    return {"login": Throttle(5, 600), "gate": Throttle(8, 600)}


def throttle(kind: str) -> Throttle:
    """Shared across sessions in this server process: \"login\" or \"gate\"."""
    return _throttles()[kind]


def user() -> dict | None:
    return st.session_state.get("user")


def log_in(account: dict) -> None:
    st.session_state["user"] = account
    st.session_state.pop("active_profile_id", None)
    st.session_state.pop("rec_label", None)
    if account["username"] in accounts.STRICT_COVER_DEMOS:
        st.session_state["strict_cover"] = True
    else:
        st.session_state.pop("strict_cover", None)


def log_out() -> None:
    for key in ("user", "active_profile_id", "rec_label", "strict_cover"):
        st.session_state.pop(key, None)


def profiles() -> list[tuple[int, Profile]]:
    return accounts.list_profiles(user()["id"])


def active_profile() -> tuple[int, Profile]:
    items = profiles()
    ids = [pid for pid, _ in items]
    active = st.session_state.get("active_profile_id")
    if active not in ids:
        active = ids[0]
    st.session_state["active_profile_id"] = active
    return active, dict(items)[active]


@dataclass
class Context:
    profile_id: int
    profile: Profile
    current: engine.Portfolio
    portfolios: list
    rec: engine.Portfolio
    basis: str
    source: str


def context() -> Context:
    """Analyse the active profile (cached) and return everything a page needs."""
    pid, profile = active_profile()
    basis = "strict" if st.session_state.get("strict_cover") else "all"
    try:
        result = _analyse(json.dumps(profile_to_dict(profile), sort_keys=True), basis)
    except ValueError as err:
        st.error(f"This profile can't be analysed yet: {err}")
        st.page_link("app_pages/profile.py", label="Fix it in Family profile", icon=":material/edit:")
        st.stop()
    portfolios = result["portfolios"]
    wanted = st.session_state.get("rec_label", "Balanced")
    rec = next((p for p in portfolios if p.label == wanted), portfolios[1])
    _, source = get_returns()
    return Context(pid, profile, result["current"], portfolios, rec, basis, source)
