"""End-to-end checks of the Streamlit app using Streamlit's headless test harness."""
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from fo import accounts

APP = Path(__file__).resolve().parent.parent / "app.py"
PAGES = ["overview", "recommendation", "risk_liquidity", "scenarios", "profile"]


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "app_test.db"
    monkeypatch.setattr(accounts, "DB_PATH", path)
    accounts.init_db(path)
    return path


def _app(user=None):
    at = AppTest.from_file(str(APP), default_timeout=180)
    if user:
        at.session_state["user"] = user
    return at.run()


def test_logged_out_visitors_see_only_the_login_screen(db):
    at = _app()
    assert not at.exception
    labels = [b.label for b in at.button]
    assert "Log in" in labels and "Create account" in labels
    assert {"Legacy-conservative family", "Business-heavy family", "Next-gen growth family"} <= set(labels)
    assert not at.sidebar.selectbox  # no profile picker, no app, before signing in


@pytest.mark.parametrize("page", PAGES)
def test_every_page_runs_for_a_signed_in_user(db, page):
    at = _app(accounts.demo_user("business", db))
    if page != "overview":
        at.switch_page(f"app_pages/{page}.py").run()
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error


def test_wrong_password_is_rejected_and_right_one_signs_in(db):
    accounts.create_user("login_check", "a good password", db)
    at = _app()
    at.text_input(key="login_user").set_value("login_check")
    at.text_input(key="login_pass").set_value("not the password")
    next(b for b in at.button if b.label == "Log in").click()
    at.run()
    assert any("Wrong username or password" in e.value for e in at.error)
    assert "user" not in at.session_state  # still signed out

    at.text_input(key="login_pass").set_value("a good password")
    next(b for b in at.button if b.label == "Log in").click()
    at.run()
    assert at.session_state["user"]["username"] == "login_check"
    assert not at.exception


def test_saving_the_profile_form_updates_the_stored_profile(db):
    user = accounts.create_user("editor_fo", "editor password 1", db)
    pid = accounts.list_profiles(user["id"], db)[0][0]
    at = _app(user)
    at.switch_page("app_pages/profile.py").run()
    at.text_input[0].set_value("Renamed by the form")
    next(b for b in at.button if b.label == "Save changes").click()
    at.run()
    assert not at.exception and not at.error
    assert accounts.get_profile(user["id"], pid, db).name == "Renamed by the form"


def test_holdings_that_do_not_add_up_are_rejected_with_a_clear_message(db):
    user = accounts.create_user("badsum_fo", "badsum password 1", db)
    pid = accounts.list_profiles(user["id"], db)[0][0]
    original = accounts.get_profile(user["id"], pid, db)
    at = _app(user)
    at.switch_page("app_pages/profile.py").run()
    at.number_input(key=f"p{pid}_hold_Debt").set_value(90.0)  # now well over 100% in total
    next(b for b in at.button if b.label == "Save changes").click()
    at.run()
    assert any("add up to" in e.value for e in at.error)
    assert accounts.get_profile(user["id"], pid, db) == original  # nothing was saved
