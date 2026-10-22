# Database and migrations

One SQLite file, `data/app.db` by default (`FO_DB_PATH` moves it). The Streamlit app and the API share it. It holds accounts, sessions, family
profiles, holdings imports and dashboard choices. It does **not** hold market data (the engine reads returns from `fo/data.py` or an optional CSV
snapshot) and it does not store questions asked of the Assistant.

## Tables

| Table | Created by | Holds | Removed when |
|---|---|---|---|
| `users` | `fo/accounts.py::init_db` (baseline, shared with Streamlit) | username (unique, case-insensitive), scrypt salt and hash, `is_demo`, created | n/a |
| `profiles` | baseline | one family profile per row: name and a JSON document of the inputs, updated time | its user is deleted |
| `schema_version` | `api/db.py::migrate` | which numbered migrations have been applied, and when | n/a |
| `sessions` | migration `001` | SHA-256 hash of each browser's session token, user, created, expires | its user is deleted; expired rows are purged at each sign-in |
| `dashboard_preferences` | migration `002` | which four dashboard modules an account chose, in order (one row per account) | its user is deleted |
| `holding_imports` | migration `003` | one confirmed import: label, file name, kind (`csv`/`xlsx`), unit, content SHA-256, row count, total in crore | its profile or user is deleted |
| `holdings` | migration `003` | the lines of an import: name, asset class, account, value in crore | its import is deleted |

Foreign keys are on (`PRAGMA foreign_keys = ON`) and cascade, so deleting a profile removes its imports and lines, and deleting a user
removes everything of theirs. The journal mode is WAL, so next to `app.db` you will see `app.db-wal` and `app.db-shm` while it is in use.

Every query that reads or changes a profile or an import carries the signed-in account's id, taken from the server-side session, so a profile
id belonging to someone else finds nothing (the API answers 404, the same as for an id that does not exist).

On first start `init_db` also creates four demo accounts (`legacy`, `business`, `nextgen`, `gap`; the fourth is the liquidity-gap example), flagged
`is_demo`, each with a random unknown password hash, so nobody can sign in to them with a password. **They are present in any database the
application has started on.** Sign-in through `/api/auth/demo` does not use them directly: it makes a private, throwaway copy for the visitor
(`demo-<family>-<random>`), and copies older than `FO_API_DEMO_HOURS` are deleted the next time anyone starts a demo (there is no timer, so on a
quiet server they stay until then).

## Migrations

Numbered, plain-SQL files in `api/migrations/`, applied in order at every API start (`lifespan` calls `api.db.migrate()`), each once, each in
one transaction, and recorded in `schema_version`. They are **forward-only**: there are no down-migrations, so to go back, restore a backup.

| Version | File | Adds |
|---|---|---|
| 001 | `001_sessions.sql` | `sessions` |
| 002 | `002_dashboard_preferences.sql` | `dashboard_preferences` |
| 003 | `003_holdings.sql` | `holding_imports`, `holdings` |

To add one: create `api/migrations/004_short_name.sql` (three-digit prefix, plain SQL, no `BEGIN`/`COMMIT`; the runner wraps it), add a test, and
restart. Never edit a migration that has been applied anywhere.

### What was verified (Phase 8, 2026-10-22)

`api.db.migrate()` was run on: an empty database; a database made by the Streamlit app alone (only `users` and `profiles`, no
`schema_version`); a database with 001 and 002 recorded and 003 missing; and a copy of the development database. In each case the end state was
versions 1, 2, 3 recorded, `PRAGMA integrity_check` = `ok`, no foreign-key violations, and a second run applied nothing. The development
database itself was not touched. This does not cover a database that is already at a **newer** version than the code (the runner ignores
versions it does not know), nor a crash half-way through a migration beyond SQLite's own transaction rollback.

## Backup and restore

SQLite in WAL mode must be copied consistently. With the API stopped, copy `app.db` (and `app.db-wal` / `app.db-shm` if present). With the API
running, use SQLite's own backup so the copy is consistent:

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; s=sqlite3.connect('data/app.db'); d=sqlite3.connect('data/app-backup.db'); s.backup(d); d.close(); s.close()"
```

To restore: stop the API, replace `app.db` with the backup (and delete any leftover `-wal`/`-shm`), start the API; migrations bring an older
backup up to date. Backups hold password hashes and family data, so protect them like the database. **No backup, restore drill or retention
policy has been set up or tested** (see [production-readiness.md](production-readiness.md)).

## Limits of this design

- SQLite allows one writer at a time and lives on one machine's disk: run **one API process** against a file, on a disk that persists. A
  platform with an ephemeral disk (Streamlit Community Cloud, free tiers of most hosts) loses accounts and data on restart.
- No encryption at rest. Sensitive fields are not encrypted separately; the file's protection is the disk's and the host's.
- No audit trail of who changed what, and no account-deletion or data-export feature yet.
- Moving to PostgreSQL is planned to stay local to `api/db.py` and `fo/accounts.py` (ADR-0017) but has not been done or tried.
