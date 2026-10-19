# Changelog

## Unreleased: React + FastAPI migration (branch `react-migration`)

### Phase 2: Design system, navigation and overview (2026-10-19)
- Added the design tokens and light, dark and match-my-device themes (no flash on load; contrast of 64 colour pairs tested).
- Added the app shell: collapsible sidebar (a drawer on small screens), top bar, skip link, and the chosen family and cover basis kept in the address.
- Added reusable components with accessible semantics, loading, empty and error states, and error boundaries at app, page and chart level.
- Added Recharts charts (allocation, projection, outflows, scenario comparison), each with a text summary and a table view.
- Replaced the Foundation page with the Overview: always-visible warnings, headline numbers with "About" panels, allocation, action plan, projection, outflows,
  scenario comparison, reasons and insights. Pages for later phases are honest placeholders.
- Tests: the Foundation page tests were migrated to the new UI (none dropped); added theme, shell, component, chart, wording-vs-golden-master and axe accessibility tests.
- Details and evidence: [docs/migration/phase-2-report.md](docs/migration/phase-2-report.md). Design: [docs/design-system.md](docs/design-system.md).

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
