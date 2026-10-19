# Changelog

## Unreleased: React + FastAPI migration (branch `react-migration`)

### Phase 1: Foundation (2026-10-19)
- Added a golden master of the financial engine and tests that compare the engine and the HTTP API to it.
- Added the FastAPI backend (`api/`): sessions, CSRF protection, private demo copies, profile CRUD, analysis with an explicit cover basis,
  numbered migrations, and a single engine thread with a timeout.
- Added the Vite + React + TypeScript shell (`web/`) with types generated from the API contract.
- Engine: `Portfolio.optimiser_converged` now reports solver failure (no change to any number).
- Moved profile validation to `fo/profile_form.py`, shared by both apps.
- Rupee amounts now round half up, like percentages (display only).
- Fixed a stray form-feed character in the README setup command.
- Details and evidence: [docs/migration/phase-1-report.md](docs/migration/phase-1-report.md). Decisions: [ADR-0017](docs/adr/0017-react-fastapi-migration.md).

## Earlier
- 2026-10-18: Streamlit prototype deployed behind an access code ([ADR-0016](docs/adr/0016-hosting-and-public-link-protections.md)).
- 2026-10-17: Scope, requirements and ADR-0001 to ADR-0015.
