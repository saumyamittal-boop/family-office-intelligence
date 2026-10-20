"""Storage for imported holdings. Every query carries the account id (taken from the session by the caller)."""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone

from fo import accounts
from fo.holdings_import import Parsed

from . import holdings_schemas as hs


class LimitReached(Exception):
    pass


class AlreadyImported(Exception):
    pass


@dataclass(frozen=True)
class StoredLine:
    name: str
    asset_class: str
    account: str
    value_cr: float


def _import_out(row: sqlite3.Row) -> hs.ImportOut:
    return hs.ImportOut(
        id=row["id"], label=row["label"], filename=row["filename"], file_kind=row["file_kind"], unit=row["unit"],
        row_count=row["row_count"], total_cr=row["total_cr"], created=row["created"],
    )


def has_fingerprint(user_id: int, profile_id: int, fingerprint: str) -> bool:
    with accounts.connect() as con:
        return con.execute(
            "SELECT 1 FROM holding_imports WHERE profile_id = ? AND user_id = ? AND content_sha256 = ?", (profile_id, user_id, fingerprint)
        ).fetchone() is not None


def add_import(user_id: int, profile_id: int, label: str, filename: str, parsed: Parsed) -> hs.ImportOut:
    """Store a confirmed import and its lines in one transaction."""
    with accounts.connect() as con:
        imports, lines = con.execute(
            "SELECT COUNT(*), COALESCE(SUM(row_count), 0) FROM holding_imports WHERE profile_id = ? AND user_id = ?", (profile_id, user_id)
        ).fetchone()
        if imports >= hs.MAX_IMPORTS_PER_PROFILE:
            raise LimitReached(f"A profile can hold at most {hs.MAX_IMPORTS_PER_PROFILE} imports. Delete one first.")
        if lines + len(parsed.lines) > hs.MAX_LINES_PER_PROFILE:
            raise LimitReached(f"A profile can hold at most {hs.MAX_LINES_PER_PROFILE:,} imported lines. Delete an import first.")
        stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            cur = con.execute(
                "INSERT INTO holding_imports (profile_id, user_id, label, filename, file_kind, unit, content_sha256, row_count, total_cr, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (profile_id, user_id, label, filename, parsed.file_kind, parsed.unit, parsed.fingerprint(), len(parsed.lines), parsed.total_cr, stamp),
            )
        except sqlite3.IntegrityError:
            raise AlreadyImported from None
        import_id = int(cur.lastrowid)
        con.executemany(
            "INSERT INTO holdings (import_id, row_no, name, asset_class, account, value_cr) VALUES (?, ?, ?, ?, ?, ?)",
            [(import_id, l.row, l.name, l.asset_class, l.account, l.value_cr) for l in parsed.lines],
        )
        return _import_out(con.execute("SELECT * FROM holding_imports WHERE id = ?", (import_id,)).fetchone())


def list_imports(user_id: int, profile_id: int) -> list[hs.ImportOut]:
    with accounts.connect() as con:
        rows = con.execute("SELECT * FROM holding_imports WHERE profile_id = ? AND user_id = ? ORDER BY id", (profile_id, user_id)).fetchall()
    return [_import_out(r) for r in rows]


def delete_import(user_id: int, profile_id: int, import_id: int) -> bool:
    with accounts.connect() as con:
        cur = con.execute("DELETE FROM holding_imports WHERE id = ? AND profile_id = ? AND user_id = ?", (import_id, profile_id, user_id))
        return cur.rowcount == 1


def stored_lines(user_id: int, profile_id: int) -> tuple[int, list[StoredLine]]:
    """(number of imports, every stored line) for the profile."""
    with accounts.connect() as con:
        imports = con.execute("SELECT COUNT(*) FROM holding_imports WHERE profile_id = ? AND user_id = ?", (profile_id, user_id)).fetchone()[0]
        rows = con.execute(
            "SELECT h.name, h.asset_class, h.account, h.value_cr FROM holdings h JOIN holding_imports i ON i.id = h.import_id "
            "WHERE i.profile_id = ? AND i.user_id = ? ORDER BY h.id",
            (profile_id, user_id),
        ).fetchall()
    return imports, [StoredLine(r["name"], r["asset_class"], r["account"], r["value_cr"]) for r in rows]
