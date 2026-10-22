# Phase 8 report: Documentation, final verification and handover

Date: 2026-10-22. Branch `react-migration` (nothing pushed; Phase 8 is **not committed**, awaiting your approval). Phase 8 changed **no product
code**: the engine, the API behaviour and the web app are as committed in Phase 7 (`007d10f`). It added documentation, one documentation generator, two
test files, and corrected `.env.example`.

> Illustrative simulation, not investment advice. Results depend on the data, assumptions, and methodology used. Historical outcomes do not
> guarantee future performance.

## 1. What was done

1. **Clean-room setup.** Cloned the committed branch into an empty folder and followed the install steps from nothing: virtual environment, `pip install`,
   model fetch, `npm ci`, type-check, unit tests, build, the full Python suite and the browser tests. Result and the one failure: section 3.
2. **Builds and migrations.** Web build reproduces; the OpenAPI file, the TypeScript types and the API reference regenerate with no change. Migrations
   were applied to an empty database, a Streamlit-only database, a partly migrated one and a copy of the development database: all end at versions 1 to 3
   with `integrity_check` = ok and no foreign-key violations; second runs apply nothing. The development database was not touched.
3. **Documentation** for every item in the brief's list (section 17), written from the code and checked by tests: see section 2.
4. **Deployment preparation.** A deployment guide for the React + FastAPI version, a proxy example, a smoke-test list, and a production-readiness
   checklist that keeps genuine family data blocked. Not executed anywhere (no host, no Linux, no Docker): the guide says so line by line.
5. **A real check of a deployment risk from Phase 7.** With a header sent by hand, uvicorn's default settings use `X-Forwarded-For` from a proxy on
   the same machine, so the per-address limits count real visitors (limitation 3 becomes a configuration step, not a code change). Also verified:
   `--no-server-header` removes the `Server` banner; `HEAD /api/health` answers 405 (documented; probes must use GET).
6. **A cross-check of two independent views of the API.** The generated reference works out who may call each operation from the code's dependencies:
   8 public, 8 signed-in, 16 signed-in with a CSRF token. The Phase 7 security review reached the same split (8 public, 24 needing sign-in of
   which 16 need CSRF) by a separate walk over the OpenAPI document.
7. **Documentation honesty tests**, proven by 11 deliberate breakages (all caught): links resolve; every setting the code reads is in
   `docs/configuration.md` and `.env.example`; documented defaults and assumption values equal the code's; the proxy example carries the exact
   security headers the web app was tested with; no document claims compliance, validation or security assurance the project lacks; the disclaimer is
   present where a reader starts.

## 2. Files

**Created (documentation):** `docs/README.md` (index), `architecture.md`, `setup.md`, `configuration.md`, `database.md`, `api.md` (generated),
`methodology.md`, `holdings-import.md`, `testing.md`, `deployment-react.md`, `production-readiness.md`, `limitations.md`, `handover.md`, and this report.

**Created (code):** `tools/export_api_docs.py` (writes `docs/api.md` from the running application), `tests/test_api_docs.py` (4 tests), `tests/test_docs.py` (122 tests).

**Modified:** `README.md` (restructured: two versions, quick start with `npm ci`, documentation index; stale "Phase 6 of 8" removed), `.env.example` (now says
nothing reads a `.env` file; added `FO_EMBED`, `FO_EMBED_DIR`, `FO_API_URL`), `docs/deployment.md` (banner pointing to the React guide), `CHANGELOG.md`.

**Removed:** nothing. **Not touched:** `fo/`, `api/`, `web/` source, `tests/golden/`, `data/app.db`, the Streamlit app, `sample-statement.csv`.

## 3. Test and verification results (actual)

| Check | Result |
|---|---|
| Clean room, fresh clone of `007d10f`: `pip install`, model fetch, `npm ci` | ok (139 s, 22 s, 32 s) |
| Clean room: `npm run typecheck`, `npm test`, `npm run build` | ok; 548 web tests in 24 files; build 960 KB JavaScript |
| Clean room: `pytest` | **774 passed, 1 expected failure**, 875 s |
| Clean room: `npm run e2e`, first run | **28 passed, 1 failed** (`flows.spec.ts` "a statement is read…"): see below |
| Clean room: `npm run e2e`, second run on a quiet machine | **29 passed** (1.3 min, against 2.8 min for the first, loaded run) |
| Real tree after Phase 8 changes: `npm run typecheck`, `npm test`, `npm run build` | ok; **548 web tests passed** (24 files, 46 s); build ok |
| Real tree: `pytest` | **900 passed, 1 expected failure** (the Assistant's 85% accuracy bar), 359 s: the 774 from Phase 7 plus 126 new |
| Real tree: `npm run e2e` | **29 passed** (1.1 min) |
| Migrations on 4 database states | ok (section 1.2) |
| Documentation breakage checks | 11 of 11 caught |

**The browser-test failure.** In the first clean-room run, one of 29 browser tests failed: after importing holdings, it opened *Family profile* and the
page was still showing "Loading the profile" when its 15-second wait ran out (the message "Not an input element" is Playwright's last observation
of the page it had just left). I was running other heavy jobs on the same laptop at that moment (the documentation breakage checks and further
test runs), and the whole browser suite then passed 29 of 29 twice on a quiet machine (once in the clean room, once in the real tree), in about half the time. An
attempt to reproduce the failure by loading every CPU thread did not trigger it in one run, so the cause is a likely, not a proven, load effect. I did not change the application or the test. **Treat the browser tests as sensitive to
a loaded machine**: run them with nothing else busy. If it recurs on a quiet machine, the profile page's loading state needs investigating.

## 4. Documentation defects found by doing the setup, and fixed

| Defect | Fix |
|---|---|
| `.env.example` told the reader to copy it to `.env`; **nothing reads a `.env` file** (no `python-dotenv`), so settings placed there would silently do nothing | Rewritten with the real mechanism (environment variables) and examples; a test checks every `FO_*` name |
| `FO_EMBED`, `FO_EMBED_DIR`, `FO_API_URL` were read by the code but documented nowhere | Documented in `.env.example` and `docs/configuration.md` |
| README install used `npm install` (may rewrite the lock file) | `npm ci` |
| README mixed the Streamlit and React instructions and said "Phase 6 of 8" | Restructured |
| `docs/deployment.md` opens with "Nothing has been published" although the app was deployed on 18 Oct | Banner added; the rest left as the owner wrote it |
| Earlier docs said the engine was "unchanged"; it differs from `main` by a seven-line `optimiser_converged` flag, and two Streamlit files were refactored to share code | `docs/architecture.md` states exactly this: the engine's numbers are unchanged (golden master) |

## 5. Final report (the brief's section 19)

### Definition of success

| Criterion | Status |
|---|---|
| Front end runs in Chrome and other Chromium browsers on localhost | **Partly**: tested in Microsoft Edge (Chromium) only; Chrome itself, Firefox and Safari were not |
| Back end uses FastAPI and the existing engine | Done |
| Financial functionality preserved or changes approved | Done: golden master; only the approved `optimiser_converged` flag differs in source |
| Guided family experience end to end | Done |
| Advanced analyst workspace end to end | Done |
| All eight dashboard modules available | Done |
| Choose, reorder and persist exactly four modules | Done |
| Risk warnings visible where relevant | Done (tests on Overview, Assistant, plan results) |
| Authoritative backend calculations | Done: the web app calculates nothing; parity tests |
| CSV/Excel imports validated, cannot silently corrupt holdings | Done: preview, re-parse on import, explicit apply, refusal tests |
| Persistence behaves as documented | Done: `docs/database.md`; one process per file |
| Security boundaries tested | Done as a self-review with executable tests; **no outside review** |
| Light and dark themes | Done |
| Financial, regression and browser tests with documented results | Done: section 3 and `docs/testing.md` |
| Set up and run from the instructions | Done on Windows from a fresh clone; other systems untested |
| Codebase and limitations documented | Done |
| Deployment path explained without claiming an unverified deployment | Done: `docs/deployment-react.md` |
| Genuine family data blocked until readiness checks are satisfied | Done: `docs/production-readiness.md` section A, repeated in the README |

### Complete / partially complete / incomplete

- **Complete:** the eight phases' scope as listed in [limitations.md](../limitations.md) section 1.
- **Partially complete:** the Assistant's routing (79% against an 85% bar), accessibility (automated only), browser and operating-system coverage
  (Edge on Windows only), deployment (documented, never run), security (self-reviewed).
- **Incomplete / not built:** real market data, external account integrations, production authentication, any regulatory claim, independent financial
  validation, account deletion and export, audit trail, language-model features, CI, containers for the API. See [limitations.md](../limitations.md) section 3.

### Known defects

[limitations.md](../limitations.md) section 4 (11 items). None changes a number silently; each is shown on screen or refused with a message.

### Security limitations

[production-readiness.md](../production-readiness.md) section A (12 items) and B. The headline ones: no encryption at rest; per-process in-memory rate limits;
scrypt cost below current guidance with the database shared with the Streamlit app; no account deletion, audit trail, password reset or second factor;
demo sign-in and API docs on by default; no outside review; Windows only.

### Financial-model limitations

[methodology.md](../methodology.md) section 9 and [protected-assumptions.md](../protected-assumptions.md): synthetic data; draft priors, haircuts and shock sizes;
constant-weight replay without costs; the liquidity-cover constraint never binds for the demo families; no backtest or second-optimiser cross-check; no
independent validation.

### Deployment status

**Not deployed anywhere.** The Streamlit app is live from `main` (since 18 Oct). The React + FastAPI version has only run on the development laptop.
The guide, the proxy example and the smoke-test list are untested on a host.

## 6. Decisions waiting for you

1. **Commit Phase 8?** (documentation, one tool, two test files, `.env.example`, README, CHANGELOG; no product code).
2. Which security limitations must close before any real family is invited (recommended: encryption at rest, account deletion and export, demo and docs
   off, HTTPS settings, the proxy settings; password cost after you decide about the shared database).
3. Whether to **push** `react-migration` (the repository is public; a push publishes all of it). Pushing also enables a Linux CI run, the one
   verification still missing.
4. How to improve the Assistant's routing, or accept 79% for now.
5. The liquidity-cover fix and default cover basis, the "In a severe market crash" wording, the target customer, and a hosting choice.
6. Saturday's mentor meeting (24 Oct): the Streamlit demo on `main` is unchanged; this branch is not needed for it.

## 7. Recommended next step

Stop building. Review the documentation set (start at `docs/README.md`), decide the commit, then spend the time before Saturday on the mentor
conversation rather than on code. If you want a further phase, the most valuable is a **Linux run** (push + a CI workflow, or WSL), because it is the
largest unverified assumption in the deployment guide.

## Run it

Exact commands for a clean machine: [setup.md](../setup.md). Checks:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
cd web
npm run typecheck; npm test; npm run build; npm run e2e
```
