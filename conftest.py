# Presence of this file at the project root makes `fo` importable from the tests.
import pytest
import streamlit as st


@pytest.fixture(autouse=True)
def _fresh_shared_resources():
    """The login and access-code throttles are process-wide; start every test with clean ones."""
    st.cache_resource.clear()
    yield
