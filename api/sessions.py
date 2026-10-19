"""Server-side sessions and CSRF tokens.

The browser holds a random token in an HttpOnly cookie. The database stores only its SHA-256 hash. The CSRF
token is derived from the session token (HMAC), so it needs no storage and is useless without the cookie.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fo import accounts

COOKIE = "fo_session"
CSRF_HEADER = "X-CSRF-Token"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def csrf_for(token: str) -> str:
    return hmac.new(token.encode("utf-8"), b"fo-csrf-v1", hashlib.sha256).hexdigest()


def create(user_id: int, hours: float) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with accounts.connect() as con:
        con.execute(
            "INSERT INTO sessions (token_hash, user_id, created, expires) VALUES (?, ?, ?, ?)",
            (_hash(token), user_id, _iso(now), _iso(now + timedelta(hours=hours))),
        )
    return token


def lookup(token: str | None) -> dict | None:
    """The signed-in user for a token, or None if it is missing, unknown or expired."""
    if not token or len(token) > 200:
        return None
    with accounts.connect() as con:
        row = con.execute(
            "SELECT u.id, u.username, u.is_demo, s.expires FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ?",
            (_hash(token),),
        ).fetchone()
    if row is None or row["expires"] <= _iso(datetime.now(timezone.utc)):
        return None
    return {"id": row["id"], "username": row["username"], "is_demo": bool(row["is_demo"])}


def destroy(token: str | None) -> None:
    if token:
        with accounts.connect() as con:
            con.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash(token),))


def purge_expired() -> int:
    with accounts.connect() as con:
        return con.execute("DELETE FROM sessions WHERE expires <= ?", (_iso(datetime.now(timezone.utc)),)).rowcount
