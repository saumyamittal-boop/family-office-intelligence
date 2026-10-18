"""Deployment settings.

Read from environment variables first, then from Streamlit secrets (.streamlit/secrets.toml locally, or the
Secrets box on Streamlit Community Cloud). Every setting is optional, so local use needs no configuration.

FO_ACCESS_CODE   If set, visitors must enter this code before they can even see the sign-in screen.
FO_MAX_ACCOUNTS  Cap on self-registered accounts (default 200). Demo families do not count.
FO_DB_PATH       Where the SQLite database lives. Point it at a persistent volume when hosting with Docker.
"""
from __future__ import annotations

import os

DEFAULT_MAX_ACCOUNTS = 200


def get(name: str, default: str | None = None) -> str | None:
    value = os.environ.get(name)
    if value:
        return value
    try:
        import streamlit as st

        found = st.secrets.get(name)
    except Exception:  # no secrets file, or not running inside Streamlit
        return default
    return str(found) if found else default


def access_code() -> str | None:
    return get("FO_ACCESS_CODE")


def max_accounts() -> int:
    try:
        return max(0, int(get("FO_MAX_ACCOUNTS") or DEFAULT_MAX_ACCOUNTS))
    except ValueError:
        return DEFAULT_MAX_ACCOUNTS
