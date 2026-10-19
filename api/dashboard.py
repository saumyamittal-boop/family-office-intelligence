"""The personalised dashboard: which modules exist, which four a person has picked, and where that is stored.

The titles, descriptions and layouts live in the web app; the server only knows the ids (so a request can't name a
module that doesn't exist), which of them are ready, and the default four.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import get_args

from fo import accounts

from . import schemas as s

FEATURED = 4
MODULE_IDS: tuple[str, ...] = get_args(s.ModuleId)

# Ready to show. Holdings consolidation needs the holdings import (Phase 5).
AVAILABLE: tuple[str, ...] = tuple(m for m in MODULE_IDS if m != "holdings_consolidation")

DEFAULT_MODULES: tuple[str, ...] = (
    "allocation_actions",
    "liquidity_commitments",
    "risk_exposure",
    "stress_scenarios",
)


def catalog() -> list[s.ModuleInfo]:
    return [s.ModuleInfo(id=m, available=m in AVAILABLE) for m in MODULE_IDS]


def _out(modules: list[str], updated: str | None) -> s.DashboardOut:
    return s.DashboardOut(
        modules=modules, is_default=updated is None, updated=updated,
        default_modules=list(DEFAULT_MODULES), catalog=catalog(),
    )


def load(user_id: int, path: Path | str | None = None) -> s.DashboardOut:
    with accounts.connect(path) as con:
        row = con.execute("SELECT modules, updated FROM dashboard_preferences WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return _out(list(DEFAULT_MODULES), None)
    try:
        saved = json.loads(row[0])
    except ValueError:
        saved = []
    # A stored choice that is no longer valid (a module was retired, the row was edited by hand) falls back to the default.
    valid = (
        isinstance(saved, list) and len(saved) == FEATURED and all(isinstance(m, str) for m in saved)
        and len(set(saved)) == FEATURED and all(m in AVAILABLE for m in saved)
    )
    if not valid:
        return _out(list(DEFAULT_MODULES), None)
    return _out(saved, row[1])


def save(user_id: int, modules: list[str], path: Path | str | None = None) -> s.DashboardOut:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with accounts.connect(path) as con:
        con.execute(
            "INSERT INTO dashboard_preferences (user_id, modules, updated) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET modules = excluded.modules, updated = excluded.updated",
            (user_id, json.dumps(modules), stamp),
        )
    return _out(modules, stamp)


def reset(user_id: int, path: Path | str | None = None) -> s.DashboardOut:
    with accounts.connect(path) as con:
        con.execute("DELETE FROM dashboard_preferences WHERE user_id = ?", (user_id,))
    return _out(list(DEFAULT_MODULES), None)
