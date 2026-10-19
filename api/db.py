"""Database setup for the API: the shared SQLite file plus numbered migrations.

`fo.accounts.init_db` still creates the users and profiles tables (the baseline both apps share). Everything
the API adds goes through the numbered files in `api/migrations`, applied once each and recorded in
`schema_version`. Plain SQL on purpose (ADR-0017): the swap to PostgreSQL stays local to this module.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fo import accounts

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def migrate(path: Path | str | None = None) -> list[int]:
    """Create the baseline tables, then apply any migration not yet recorded. Returns the versions applied."""
    accounts.init_db(path)
    applied: list[int] = []
    with accounts.connect(path) as con:
        con.execute("PRAGMA journal_mode = WAL")
        con.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied TEXT NOT NULL)")
        done = {row[0] for row in con.execute("SELECT version FROM schema_version")}
        for file in sorted(MIGRATIONS_DIR.glob("[0-9][0-9][0-9]_*.sql")):
            version = int(file.name[:3])
            if version in done:
                continue
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            # One transaction per migration: if any statement fails, the connection closes and all of it rolls back.
            con.executescript(
                f"BEGIN;\n{file.read_text(encoding='utf-8')}\n"
                f"INSERT INTO schema_version (version, applied) VALUES ({version}, '{stamp}');\nCOMMIT;"
            )
            applied.append(version)
    return applied
