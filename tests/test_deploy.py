"""Protections for a public link: throttling, the access-code gate, the sign-up cap, and configuration."""
import importlib
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from fo import accounts, security, settings

APP = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture()
def db(tmp_path, monkeypatch):
    path = tmp_path / "deploy_test.db"
    monkeypatch.setattr(accounts, "DB_PATH", path)
    accounts.init_db(path)
    return path


def _click(at, label):
    next(b for b in at.button if b.label == label).click()
    return at.run()


def _text(at):
    return " ".join(h.value for h in at.get("html"))


# ---- the throttle -----------------------------------------------------------------------------------------------
def test_throttle_blocks_after_too_many_failures_then_recovers():
    now = [0.0]
    t = security.Throttle(max_failures=3, window_seconds=60, clock=lambda: now[0])
    assert t.blocked_for("a") == 0
    for _ in range(3):
        t.record_failure("a")
    assert t.blocked_for("a") == pytest.approx(60)
    now[0] = 30
    assert t.blocked_for("a") == pytest.approx(30)
    assert t.blocked_for("someone_else") == 0  # keys are independent
    now[0] = 61
    assert t.blocked_for("a") == 0  # old failures age out


def test_throttle_reset_clears_the_count_and_minutes_round_up():
    t = security.Throttle(max_failures=1, window_seconds=600)
    t.record_failure("a")
    assert t.blocked_for("a") > 0
    t.reset("a")
    assert t.blocked_for("a") == 0
    assert security.minutes(1) == 1 and security.minutes(61) == 2 and security.minutes(0) == 1


# ---- settings ------------------------------------------------------------------------------------------------------
def test_settings_come_from_the_environment_with_safe_defaults(monkeypatch):
    monkeypatch.setattr(st, "secrets", {})  # ignore any real secrets file on this machine
    monkeypatch.delenv("FO_ACCESS_CODE", raising=False)
    monkeypatch.delenv("FO_MAX_ACCOUNTS", raising=False)
    assert settings.access_code() is None
    assert settings.max_accounts() == settings.DEFAULT_MAX_ACCOUNTS
    monkeypatch.setenv("FO_ACCESS_CODE", "letmein")
    monkeypatch.setenv("FO_MAX_ACCOUNTS", "7")
    assert settings.access_code() == "letmein" and settings.max_accounts() == 7
    monkeypatch.setenv("FO_MAX_ACCOUNTS", "not a number")
    assert settings.max_accounts() == settings.DEFAULT_MAX_ACCOUNTS


def test_settings_fall_back_to_streamlit_secrets(monkeypatch):
    monkeypatch.delenv("FO_ACCESS_CODE", raising=False)
    monkeypatch.setattr(st, "secrets", {"FO_ACCESS_CODE": "from-secrets"})
    assert settings.access_code() == "from-secrets"


def test_the_database_location_can_be_set_from_the_environment(monkeypatch, tmp_path):
    target = tmp_path / "volume" / "app.db"
    monkeypatch.setenv("FO_DB_PATH", str(target))
    reloaded = importlib.reload(accounts)
    try:
        assert reloaded.DB_PATH == target
        reloaded.init_db()  # creates the folder and seeds the demo families there
        assert target.exists() and reloaded.demo_user("gap") is not None
    finally:
        monkeypatch.delenv("FO_DB_PATH")
        importlib.reload(accounts)


# ---- the sign-up cap ---------------------------------------------------------------------------------------------------
def test_signup_cap_counts_only_real_accounts_not_demo_families(db):
    accounts.create_user("first_user", "first password", db, max_accounts=2)
    accounts.create_user("second_user", "second password", db, max_accounts=2)
    with pytest.raises(ValueError, match="closed"):
        accounts.create_user("third_user", "third password", db, max_accounts=2)
    assert accounts.create_user("third_user", "third password", db)["username"] == "third_user"  # no cap, no problem


def test_the_app_reports_closed_signups(db, monkeypatch):
    monkeypatch.setenv("FO_MAX_ACCOUNTS", "0")
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    at.text_input(key="signup_user").set_value("latecomer_fo")
    at.text_input(key="signup_pass").set_value("latecomer password")
    _click(at, "Create account")
    assert any("closed" in e.value for e in at.error)
    assert accounts.authenticate("latecomer_fo", "latecomer password", db) is None


# ---- the access-code gate --------------------------------------------------------------------------------------------------
def test_no_gate_when_no_access_code_is_configured(db, monkeypatch):
    monkeypatch.setattr(st, "secrets", {})
    monkeypatch.delenv("FO_ACCESS_CODE", raising=False)
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    assert "Log in" in [b.label for b in at.button]
    assert "private" not in _text(at)


def test_the_gate_hides_everything_until_the_right_code_is_entered(db, monkeypatch):
    monkeypatch.setenv("FO_ACCESS_CODE", "mentor-preview-code")
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    assert "This preview is private" in _text(at)
    labels = [b.label for b in at.button]
    assert "Log in" not in labels and "Legacy-conservative family" not in labels  # no demo buttons either

    at.text_input(key="gate_code").set_value("wrong code")
    _click(at, "Continue")
    assert any("isn't right" in e.value for e in at.error)
    assert "Legacy-conservative family" not in [b.label for b in at.button]

    at.text_input(key="gate_code").set_value("mentor-preview-code")
    _click(at, "Continue")
    assert not at.exception, [e.value for e in at.exception]
    assert "Legacy-conservative family" in [b.label for b in at.button]  # now the login screen
    assert at.session_state["access_ok"] is True


def test_guessing_the_access_code_gets_locked_out(db, monkeypatch):
    monkeypatch.setenv("FO_ACCESS_CODE", "the-real-code")
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    for i in range(8):
        at.text_input(key="gate_code").set_value(f"guess {i}")
        _click(at, "Continue")
    at.text_input(key="gate_code").set_value("the-real-code")  # even the right code is refused while locked
    _click(at, "Continue")
    assert any("Too many attempts" in e.value for e in at.error)
    assert "access_ok" not in at.session_state


# ---- login throttling ---------------------------------------------------------------------------------------------------------
def test_repeated_wrong_passwords_lock_the_account_for_a_while(db):
    accounts.create_user("throttled_fo", "the right password", db)
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    for _ in range(5):
        at.text_input(key="login_user").set_value("throttled_fo")
        at.text_input(key="login_pass").set_value("a wrong password")
        _click(at, "Log in")
    assert any("Wrong username or password" in e.value for e in at.error)

    at.text_input(key="login_user").set_value("throttled_fo")
    at.text_input(key="login_pass").set_value("the right password")
    _click(at, "Log in")
    assert any("Too many attempts" in e.value for e in at.error)
    assert "user" not in at.session_state  # the right password did not get in while locked


def test_a_correct_login_clears_earlier_failures(db):
    accounts.create_user("forgetful_fo", "the right password", db)
    at = AppTest.from_file(str(APP), default_timeout=240).run()
    for _ in range(3):
        at.text_input(key="login_user").set_value("forgetful_fo")
        at.text_input(key="login_pass").set_value("oops")
        _click(at, "Log in")
    at.text_input(key="login_user").set_value("forgetful_fo")
    at.text_input(key="login_pass").set_value("the right password")
    _click(at, "Log in")
    assert at.session_state["user"]["username"] == "forgetful_fo"
