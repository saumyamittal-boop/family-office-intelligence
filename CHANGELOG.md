# Changelog

## Unreleased: React + FastAPI migration (branch `react-migration`)

### Phase 5: Holdings import and consolidation (2026-10-20)
- Added the **Holdings** page: choose a CSV or Excel (`.xlsx`) statement, see exactly what was read (columns used, every line, totals by asset class, how each label was mapped) *before* anything is stored, then import it.
  A template can be downloaded. Amounts can be in rupees crore, lakh or rupees (a unit named in the value column's heading wins). Labels the model does not know (for example plain "Equity") are never guessed: the person assigns a class.
- Added the consolidated view: totals by asset class and by account, the five largest holdings across accounts (the same name in several accounts is added together), and a comparison with the profile's own holdings.
  Imports can be listed and deleted (two clicks). The same data cannot be imported twice into one profile.
- Added **"Use these holdings in my profile"** as a separate, explicit step with a before-and-after table (and an optional tick to set the corpus too). Nothing in a profile changes until it is pressed; the same rules as the profile editor
  apply (for example illiquid holdings at most 95%), and analysis results are recalculated afterwards.
- Dashboard module 8, **Holdings consolidation**, can now be chosen like any other (it was listed as "not ready" before).
- Files are read defensively: 150 KB, 1,000 rows and 30 columns at most; Excel files are inspected before they are opened (macros, external links, ActiveX, embedded objects, path tricks, zip bombs and XML entity bombs are refused);
  formulas and text starting `= + - @` are refused; the server parses again on import and never trusts the preview. Rate-limited, scoped to the signed-in account (another account's profile answers 404).
- Added to the API (migration `003`, tables `holding_imports` and `holdings`): `GET /api/holdings/template`, and under `/api/profiles/{id}/`: `holdings/preview`, `holdings/imports` (create, list, delete), `holdings/consolidation`,
  `holdings/apply/preview`, `holdings/apply`. New dependencies for the API only: `openpyxl`, `defusedxml`, `et-xmlfile` (pinned). The engine, the Streamlit app and every number are unchanged.
- Decision: [ADR-0020](docs/adr/0020-holdings-import-and-consolidation.md). Details and evidence: [docs/migration/phase-5-report.md](docs/migration/phase-5-report.md).

### Development tooling (2026-10-20)
- Recorded the design skills, hooks, Figma and Playwright setup and the separate free-model gateway in [docs/dev-tooling.md](docs/dev-tooling.md), with sources, pinned commits and how to undo each.
  No third-party file is stored in this repository and no app code or number changed.

### Phase 4: Personalised dashboard and analyst workspace (2026-10-19)
- Added the dashboard: the person picks exactly four of the modules, orders them, and the choice is saved to their account (restored after sign-out, private to the account, default allocation / liquidity / risk / stress scenarios).
  The customise panel has four slots (picking a module that is already used swaps the two), move up and down, a preview and a list of where every module lives. Warnings and the headline tiles are never hidden by the choice.
- Added seven modules, each in a glance size and a full size: Allocation and actions, Liquidity and commitments, Risk exposure, Stress scenarios, Net worth and projection, Historical performance, Why this recommendation. Holdings consolidation is listed and waits for Phase 5.
- Added the analyst pages: Recommendation (mixes side by side, measures table, projection, reasons, method and limits), Risk and liquidity (drawdown against your limit, CVaR, liquidity ladder, outflows, value history, calendar-year returns),
  Scenarios (what each built-in scenario assumes, six custom dials with a live result, every option compared under one scenario) and Family profile (edit every input, several profiles, save as new, delete with confirmation).
- Added to the API: `GET/PUT/DELETE /api/dashboard` (migration `002`), `GET /api/profiles/{id}/history`, `POST /api/profiles/{id}/scenarios`; `/api/meta` lists the built-in scenarios and the dial limits; the analysis carries `current_ladder` and `current_scenarios`.
- **Fixed the intermittent test stall** open since Phase 1. Cause: SciPy's bundled HiGHS solver hangs (spinning a core) or crashes the process when a thread that has used it exits, on Windows. A bare script hung in 27 of 30 runs;
  with a thread that stays alive, 0 of 30. Engine threads are now pooled and never exit. The engine and every number are unchanged. See the Phase 4 report for the evidence and what is still unproven.
- The golden master gained two fields per family and basis, added without regenerating the rest (every existing value re-verified first). The profile editor is tested against 115 recorded server verdicts.
- Fixed while testing: link and label names could be read run together by screen readers (a hidden span carried its own leading space); the editor accepted a holdings total of exactly 99.5% or 100.5% and a name over 60 characters, which the server refuses.
- Details and evidence: [docs/migration/phase-4-report.md](docs/migration/phase-4-report.md). Decision: [ADR-0019](docs/adr/0019-personalised-dashboard-and-analyst-workspace.md).

### Phase 3: Guided planning (2026-10-19)
- Added the six-step "Plan my money" flow in React: about you, what's coming, comfort with a bad year, safety net, what you own, then Strategy A, B and C.
- Made it live: a read-out ("what this means so far") follows the answers as they are typed and keeps the previous figure on screen while it updates;
  switching comfort level is instant with no request; changing the safety net or spending recalculates while the old strategies stay visible.
- Added review and edit of every answer, the browser's Back button between steps, a draft that survives a reload (this tab only), and landing a
  brand-new account on the plan.
- Added the plan API (`/api/plan/config`, `preview`, `strategies`, `save`): numbers come from the unchanged engine and are checked against the golden
  master through the real HTTP API; saving is idempotent; recalculation is rate-limited.
- Added `year_range` (typical year, median, worst and best) to every analysis; added the pure `fo.formatting` module shared by both apps.
- Copy: "In a crash like 2020" is "In a severe market crash" in the React app, with the preset's actual shocks.
- Fixed while testing: focus did not move to a new step in production builds; the answer review was invalid HTML; step buttons had a run-together accessible name.
- Found, not fixed (engine is protected): zero spending with no commitment in the safety-net window makes the scenario step divide by zero; the API now refuses it clearly.
- After review: the commitment type "Other" is now **Custom** in the React app; a family can name their own expense, and the name shows in the answers list
  and the reasons. It changes no number, and the saved profile keeps only the year and amount.
- Details and evidence: [docs/migration/phase-3-report.md](docs/migration/phase-3-report.md). Decision: [ADR-0018](docs/adr/0018-guided-plan-api-and-live-recalculation.md).

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
