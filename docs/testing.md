# Testing instructions

There are three layers of automated tests, plus two generated files that tests keep honest. All use **synthetic data only** and temporary or
throwaway databases, never `data/app.db`.

| Layer | Tool | Where | What it proves |
|---|---|---|---|
| Python | pytest | `tests/` | Engine behaviour, the golden master, accounts, the whole HTTP API, security properties, the holdings parser, the Assistant's answers and router, the Streamlit app, and that the documentation matches the code |
| Web unit and component | vitest + jsdom + axe-core | `web/src/**/*.test.ts(x)` | Every page and component renders, behaves and is accessible to automated checks; formatters match the Python ones; colours meet contrast ratios |
| Browser | Playwright (Edge) | `web/e2e/` | Real browser, real API, real engine: sign-in, the main flows, keyboard use, phone/tablet/desktop layouts, isolation between accounts, security headers, and no Content-Security-Policy violation on any page |
| Types | TypeScript | `npm run typecheck` | The web app and the browser tests compile against the generated API types |

## Run everything

From the project root, in PowerShell (the virtual environment from [setup.md](setup.md) must exist):

```powershell
.\.venv\Scripts\python.exe -m pytest -q          # Python: see "Latest results" for the count and time
cd web
npm run typecheck                                # app and browser-test configurations
npm test                                         # web unit and component tests (prints harmless "Not implemented: HTMLCanvasElement" lines)
npm run build                                    # production build (also type-checks)
npm run e2e                                      # browser tests; starts its own API (8110), dev server (5180) and preview (5181)
```

Useful variations: `pytest tests/test_golden.py -q` (one file), `pytest -k explain -q` (by name), `pytest -x -q` (stop at the first failure),
`npm test -- src/pages/PlanPage.test.tsx`, `npm run e2e -- --headed` (watch the browser), `npm run e2e -- e2e/security.spec.ts`.

The browser tests need Microsoft Edge installed (nothing is downloaded), free ports 8110, 5180 and 5181, and the Python environment at
`<project>\.venv`. They build the web app first, so allow a couple of minutes.

## What the Python tests cover

| Group (files in `tests/`) | Checks |
|---|---|
| Engine and plan: `test_engine.py`, `test_plan.py`, `test_scenarios.py` | Allocation limits, drawdown enforcement, liquidity, scenario arithmetic (for example a 25% equity fall costing exactly 137.5 crore for the liquidity-gap family), guided-plan answers |
| **Golden master**: `test_golden.py`, `test_api_parity.py`, `tests/golden/engine_golden.json` | Every protected assumption, estimated input and every demo family's analysis on both cover bases is unchanged, directly and through the HTTP API (compared to 1e-9) |
| Invariants: `test_financial_invariants.py` | Random valid profiles through the API: weights add up and respect limits, results repeat exactly, renaming changes no number, impossible inputs are refused with a reason |
| API: `test_api_auth.py`, `_profiles.py`, `_plan.py`, `_analyst.py`, `_dashboard.py`, `_holdings.py`, `_explain.py`, `_database.py`, `_engine_thread.py` | Each endpoint's behaviour and errors, migrations, and the single long-lived engine thread (including a subprocess run of the solver-hang scenario) |
| Security: `test_security_review.py`, `test_accounts.py` | Sessions, CSRF, `Origin`, body guard, throttles, account isolation on every profile route, error bodies that never echo input, headers, upload attacks; one walk over the API's own OpenAPI document so a new route cannot skip the checks |
| Holdings: `test_holdings_import.py` | CSV and Excel parsing, units, class labels, hostile files (zip bombs, macros, formulas, control characters, huge rows) |
| Assistant: `test_explain_answers.py`, `test_explain_golden.py`, `test_question_match.py`, `test_question_hybrid.py` | A digit cannot reach an answer without a registered source figure; every figure equals the engine's value at the path it names; refusals; the router on 640 questions in five pinned splits |
| Demo kit: `test_demo_script.py` | Every figure quoted in `docs/demo-script-react.md` equals what the application produces (the same check the launcher runs), the demo statement is the synthetic ₹1,000 Cr file, and the launcher uses its own database |
| Contract and docs: `test_openapi_contract.py`, `test_api_docs.py`, `test_docs.py`, `test_format_vectors.py`, `test_profile_vectors.py` | The committed OpenAPI file, TypeScript types and `docs/api.md` match the code; links resolve; documented settings, defaults and assumptions equal the code's; no document claims compliance or validation; Python and TypeScript formatters agree |
| Streamlit: `test_app.py`, `test_deploy.py`, `test_profile_form.py` | The original app still runs through its pages; deployment gate and settings |

One test is an **expected failure** (`xfail`): the Assistant's accuracy bars on the untouched final question set (85%) are not met (79%). It is
kept visible on purpose and will start to pass when the router improves ([Phase 6 report](migration/phase-6-report.md)).

## What the browser tests cover (`web/e2e/`)

`auth` (a new account lands on the guided plan and survives a reload; wrong password; lock-out after repeated guesses; demo family; cookie invisible
to scripts and ended by the server on log-out; the Back button after log-out), `flows` (overview numbers and a warning that explains itself; dashboard
choice remembered; a statement read, checked, imported, consolidated and only then offered to the profile; the Assistant answering, declining and
offering a way forward; the same page every time), `isolation` (another account's profile is not found, changed or deleted; separate dashboards),
`keyboard` (reaching and using the Assistant without a mouse; a side panel traps focus and hands it back; focus is always visible), `responsive`
(no sideways scrolling, menu as a drawer on a phone, tap-sized controls, the dark theme), `security` (CSRF and `Origin`, cross-site form posts,
markup shown as text, hostile spreadsheets and oversized files refused, no-cache and no-frame headers), `csp` (the built app under the production
policy: no violation on any page, and an injected script is blocked). The scenarios, recommendation, risk and profile-edit screens are
covered by the web unit tests and the API tests rather than by a browser test.

## Not covered

- Linux, macOS, Firefox, Safari; a real host; a real proxy or certificate.
- Manual screen-reader use and visual review by a person (automated accessibility and contrast checks only).
- Load and soak testing; the engine runs one analysis at a time by design, so throughput was not a goal.
- Real market data, real families, or an independent check of the financial method ([methodology.md](methodology.md)).
- Whether people understand the Assistant's answers (a comprehension check was designed and has not been run with people).

## Regenerating and extending

- **Golden master:** only after the project owner approves a change to a protected assumption: `python tools/make_golden.py`, then a changelog line.
- **Contract and API reference:** `python tools/export_openapi.py`, `python tools/export_api_docs.py`, `npm run gen:api` in `web/`.
- **Formatter vectors:** `python tools/make_format_vectors.py` and `python tools/make_profile_vectors.py` (the web tests read them).
- **Assistant evaluation:** `python tools/eval_questions.py [--split heldout|confirm|calib|final] [--lexical] [--misses]`. The question sets in
  `tests/golden/questions.txt` are hash-pinned: changing one fails `test_explain_golden.py` on purpose.
- **A new test:** put Python tests in `tests/` (use the `client` fixture from `tests/conftest.py` for API tests; it gives a fresh temporary
  database), web tests next to the component (`Component.test.tsx`), and browser tests in `web/e2e/` (import `helpers.ts`).

## Latest results

Phase 8, 2026-10-22, Windows 11, Python 3.12.10, Node 24.21.0, Edge, on a machine with nothing else running:

| Suite | Result | Time |
|---|---|---|
| `pytest -q` | 910 passed, 1 expected failure (`xfail`), 1 warning (900 at Phase 8; 10 more were added on 2026-10-23 for the demo kit and the new documents) | 6 min |
| `npm run typecheck` | clean (app and browser-test configurations) | 6 s |
| `npm test` | 548 passed in 24 files | 46 s |
| `npm run build` | ok; about 960 KB of JavaScript (285 KB gzipped) | 6 s |
| `npm run e2e` | 29 passed | 1.1 min |

The same suites on a fresh clone (the clean-room check, [setup.md](setup.md) section 6) gave the same counts, except that one browser test timed out
on its first run because the machine was busy with other jobs, and passed on a quiet re-run. The browser tests roughly double in duration, and can
time out, on a loaded machine: run them with nothing else busy. A full `pytest` run took 15 minutes on that same busy machine and 6 minutes on a quiet one.
