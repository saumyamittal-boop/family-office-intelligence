"""Migrations, the shared database file, and the optimiser-failure flag (decision D4)."""
import sqlite3

import numpy as np
import pytest

from api import db
from fo import accounts, engine
from fo.personas import PERSONAS


def tables(path):
    with sqlite3.connect(path) as con:
        return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_migrating_a_fresh_database_creates_everything_once(db_path):
    assert db.migrate(db_path) == [1, 2]
    assert {"users", "profiles", "sessions", "dashboard_preferences", "schema_version"} <= tables(db_path)
    assert db.migrate(db_path) == []  # nothing left to apply the second time


def test_a_database_made_by_the_streamlit_app_is_upgraded_in_place(db_path):
    accounts.init_db(db_path)  # what the Streamlit app has always done
    created = accounts.create_user("existing_member", "long enough pass", db_path)
    assert "sessions" not in tables(db_path)
    db.migrate(db_path)
    assert accounts.authenticate("existing_member", "long enough pass", db_path)["id"] == created["id"]
    assert len(accounts.list_profiles(created["id"], db_path)) == 1


def test_the_streamlit_side_keeps_working_after_the_api_migrations(db_path):
    db.migrate(db_path)
    accounts.init_db(db_path)  # idempotent: must not disturb the API's tables
    assert accounts.demo_user("gap", db_path)["is_demo"] is True
    assert "sessions" in tables(db_path)


def test_a_failing_migration_rolls_back_completely(db_path, tmp_path, monkeypatch):
    broken = tmp_path / "migrations"
    broken.mkdir()
    (broken / "001_ok.sql").write_text("CREATE TABLE first_ok (id INTEGER);", encoding="utf-8")
    (broken / "002_bad.sql").write_text("CREATE TABLE half_done (id INTEGER); INSERT INTO nope VALUES (1);", encoding="utf-8")
    monkeypatch.setattr(db, "MIGRATIONS_DIR", broken)
    with pytest.raises(sqlite3.OperationalError):
        db.migrate(db_path)
    found = tables(db_path)
    assert "first_ok" in found and "half_done" not in found  # 002 left no trace
    with sqlite3.connect(db_path) as con:
        assert [r[0] for r in con.execute("SELECT version FROM schema_version")] == [1]


def test_deleting_a_user_removes_their_sessions_and_profiles(db_path):
    db.migrate(db_path)
    user = accounts.create_user("to_delete", "long enough pass", db_path)
    with accounts.connect(db_path) as con:
        con.execute("INSERT INTO sessions (token_hash, user_id, created, expires) VALUES ('h', ?, 'a', 'b')", (user["id"],))
        con.execute("DELETE FROM users WHERE id = ?", (user["id"],))
        assert con.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?", (user["id"],)).fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM profiles WHERE user_id = ?", (user["id"],)).fetchone()[0] == 0


def test_data_survives_an_application_restart(make_client):
    first = make_client()
    r = first.post("/api/auth/signup", json={"username": "persistent_user", "password": "long enough pass"})
    headers = {"X-CSRF-Token": r.json()["csrf_token"]}
    body = first.get(f"/api/profiles/{first.get('/api/profiles').json()[0]['id']}").json()
    body.pop("id")
    body["name"] = "Survives restarts"
    first.post("/api/profiles", json=body, headers=headers)

    restarted = make_client()  # a brand-new app and process state, same database file
    assert restarted.post("/api/auth/login", json={"username": "persistent_user", "password": "long enough pass"}).status_code == 200
    assert "Survives restarts" in [p["name"] for p in restarted.get("/api/profiles").json()]


# ---- Optimiser failure is now visible (D4): the numbers are unchanged, the flag is new ----------------------------------------------------------
def test_a_clean_solve_reports_that_the_optimiser_converged(sample_returns):
    options = engine.recommend(PERSONAS["A"], sample_returns, "all")
    assert all(pf.optimiser_converged for pf in options)
    assert engine.analyse_current(PERSONAS["A"], sample_returns).optimiser_converged is True  # nothing is optimised there


def test_a_solver_failure_is_flagged_and_explained_without_changing_the_weights(sample_returns, monkeypatch):
    real_minimize = engine.minimize
    failures = []

    def failing(*args, **kwargs):
        result = real_minimize(*args, **kwargs)
        result.success = False
        failures.append(1)
        return result

    honest = engine.recommend(PERSONAS["B"], sample_returns, "all")
    monkeypatch.setattr(engine, "minimize", failing)
    flagged = engine.recommend(PERSONAS["B"], sample_returns, "all")

    assert failures
    for good, bad in zip(honest, flagged):
        assert bad.optimiser_converged is False and good.optimiser_converged is True
        assert any("did not report a clean solution" in line for line in bad.explanation)
        assert not any("did not report a clean solution" in line for line in good.explanation)
        np.testing.assert_allclose(bad.weights_sleeve, good.weights_sleeve, rtol=0, atol=1e-12)
        assert bad.exp_return == good.exp_return and bad.max_dd == good.max_dd
