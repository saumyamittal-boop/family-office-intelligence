"""Fixtures for the API tests: a client per test, each with its own empty database."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from api.config import Settings
from api.main import create_app
from fo import accounts
from fo.data import make_sample_returns


@pytest.fixture(scope="session")
def sample_returns():
    return make_sample_returns()


@pytest.fixture()
def db_path(tmp_path, monkeypatch):
    path = tmp_path / "api_test.db"
    monkeypatch.setattr(accounts, "DB_PATH", path)
    return path


@pytest.fixture()
def make_client(db_path, sample_returns, monkeypatch):
    """Build API clients (each is its own browser, with its own cookies) on one shared test database."""
    monkeypatch.setattr("api.main.load_returns", lambda: (sample_returns, "sample"))
    started: list[TestClient] = []

    def _make(**overrides) -> TestClient:
        client = TestClient(create_app(replace(Settings(), **overrides)))
        client.__enter__()
        started.append(client)
        return client

    yield _make
    for client in started:
        client.__exit__(None, None, None)


@pytest.fixture()
def client(make_client):
    return make_client()
