"""Accounts and per-user profile storage.

SQLite and the standard library only (ADR-0010): usernames, scrypt-hashed passwords, and each user's
private family profiles. Every profile query is scoped by user_id, so one account can never read or
change another's profiles.

DEMO ONLY: this is a prototype. There is no email verification, no password reset and no rate limiting.
Use synthetic data and never reuse a real password.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .personas import PERSONAS, Profile, profile_from_dict, profile_to_dict, starter_profile

DB_PATH = Path(os.environ.get("FO_DB_PATH") or Path(__file__).resolve().parent.parent / "data" / "app.db")
_SCRYPT = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}
MIN_PASSWORD_LENGTH = 8
_USERNAME = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")

# Demo accounts have no usable password; the login page signs them in through demo buttons.
DEMO_ACCOUNTS = {"legacy": "A", "business": "B", "nextgen": "C", "gap": "D"}
# Demo families that open with the stricter liquidity cover switched on, so their shortfall shows at once.
STRICT_COVER_DEMOS = {"gap"}


@contextmanager
def _db(path: Path | str | None = None):
    target = Path(path or DB_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(target)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    finally:
        con.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, **_SCRYPT)


def init_db(path: Path | str | None = None) -> None:
    """Create tables and the three demo accounts if they are missing."""
    with _db(path) as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt BLOB NOT NULL,
                hash BLOB NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 0,
                created TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data TEXT NOT NULL,
                updated TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_profiles_user ON profiles(user_id);
            """
        )
        for username, persona_key in DEMO_ACCOUNTS.items():
            if con.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                continue
            cur = con.execute(
                "INSERT INTO users (username, salt, hash, is_demo, created) VALUES (?, ?, ?, 1, ?)",
                (username, secrets.token_bytes(16), secrets.token_bytes(32), _now()),
            )
            persona = PERSONAS[persona_key]
            con.execute(
                "INSERT INTO profiles (user_id, name, data, updated) VALUES (?, ?, ?, ?)",
                (cur.lastrowid, persona.name, json.dumps(profile_to_dict(persona)), _now()),
            )


def create_user(
    username: str, password: str, path: Path | str | None = None, max_accounts: int | None = None
) -> dict:
    username = username.strip()
    if not _USERNAME.match(username):
        raise ValueError("Username must be 3 to 32 characters: letters, numbers, dots, dashes or underscores.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if max_accounts is not None:
        with _db(path) as con:
            existing = con.execute("SELECT COUNT(*) FROM users WHERE is_demo = 0").fetchone()[0]
        if existing >= max_accounts:
            raise ValueError("Sign-ups are closed for this preview.")
    salt = secrets.token_bytes(16)
    try:
        with _db(path) as con:
            cur = con.execute(
                "INSERT INTO users (username, salt, hash, is_demo, created) VALUES (?, ?, ?, 0, ?)",
                (username, salt, _hash(password, salt), _now()),
            )
            user_id = cur.lastrowid
            starter = starter_profile()
            con.execute(
                "INSERT INTO profiles (user_id, name, data, updated) VALUES (?, ?, ?, ?)",
                (user_id, starter.name, json.dumps(profile_to_dict(starter)), _now()),
            )
    except sqlite3.IntegrityError:
        raise ValueError("That username is already taken.") from None
    return {"id": user_id, "username": username, "is_demo": False}


def authenticate(username: str, password: str, path: Path | str | None = None) -> dict | None:
    with _db(path) as con:
        row = con.execute(
            "SELECT id, username, salt, hash, is_demo FROM users WHERE username = ?", (username.strip(),)
        ).fetchone()
    # Always do the hash work so timing does not reveal whether the username exists.
    salt = row["salt"] if row else b"\x00" * 16
    candidate = _hash(password, salt)
    if row is None or row["is_demo"] or not hmac.compare_digest(candidate, row["hash"]):
        return None
    return {"id": row["id"], "username": row["username"], "is_demo": False}


def demo_user(username: str, path: Path | str | None = None) -> dict | None:
    if username not in DEMO_ACCOUNTS:
        return None
    with _db(path) as con:
        row = con.execute("SELECT id, username FROM users WHERE username = ? AND is_demo = 1", (username,)).fetchone()
    return {"id": row["id"], "username": row["username"], "is_demo": True} if row else None


# ---- Profiles (always scoped to the owning user) ------------------------------------------------
def list_profiles(user_id: int, path: Path | str | None = None) -> list[tuple[int, Profile]]:
    with _db(path) as con:
        rows = con.execute("SELECT id, data FROM profiles WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()
    return [(r["id"], profile_from_dict(json.loads(r["data"]), key=f"user{r['id']}")) for r in rows]


def get_profile(user_id: int, profile_id: int, path: Path | str | None = None) -> Profile | None:
    with _db(path) as con:
        row = con.execute(
            "SELECT data FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user_id)
        ).fetchone()
    return profile_from_dict(json.loads(row["data"]), key=f"user{profile_id}") if row else None


def add_profile(user_id: int, profile: Profile, path: Path | str | None = None) -> int:
    with _db(path) as con:
        cur = con.execute(
            "INSERT INTO profiles (user_id, name, data, updated) VALUES (?, ?, ?, ?)",
            (user_id, profile.name, json.dumps(profile_to_dict(profile)), _now()),
        )
        return int(cur.lastrowid)


def save_profile(user_id: int, profile_id: int, profile: Profile, path: Path | str | None = None) -> bool:
    """Update a profile the user owns. Returns False if it does not exist or belongs to someone else."""
    with _db(path) as con:
        cur = con.execute(
            "UPDATE profiles SET name = ?, data = ?, updated = ? WHERE id = ? AND user_id = ?",
            (profile.name, json.dumps(profile_to_dict(profile)), _now(), profile_id, user_id),
        )
        return cur.rowcount == 1


def delete_profile(user_id: int, profile_id: int, path: Path | str | None = None) -> bool:
    """Delete a profile the user owns, but never their last one."""
    with _db(path) as con:
        count = con.execute("SELECT COUNT(*) FROM profiles WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count <= 1:
            return False
        cur = con.execute("DELETE FROM profiles WHERE id = ? AND user_id = ?", (profile_id, user_id))
        return cur.rowcount == 1
