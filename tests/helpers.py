"""Small helpers shared by the API tests."""
from fastapi.testclient import TestClient


def sign_up(client: TestClient, username: str, password: str = "correct horse battery") -> dict:
    """Create an account and return the headers a state-changing request needs."""
    r = client.post("/api/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return {"X-CSRF-Token": r.json()["csrf_token"]}


def demo(client: TestClient, family: str) -> dict:
    """Open a private copy of a demo family and return the headers a state-changing request needs."""
    r = client.post("/api/auth/demo", json={"family": family})
    assert r.status_code == 200, r.text
    return {"X-CSRF-Token": r.json()["csrf_token"]}


def profile_body(client: TestClient, profile_id: int | None = None) -> dict:
    """A valid profile request body, copied from an existing profile of the signed-in user."""
    pid = profile_id or client.get("/api/profiles").json()[0]["id"]
    body = client.get(f"/api/profiles/{pid}").json()
    body.pop("id")
    return body
