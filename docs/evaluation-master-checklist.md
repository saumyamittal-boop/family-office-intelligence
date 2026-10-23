# Evaluation of the web app against the master-prompt checklist

> Illustrative simulation, not investment advice. Synthetic data only. Dated 2026-10-23, commit `61b9894`. An engineering evaluation by the developer's
> assistant, not an independent review: nothing here is a certification, a security audit or a compliance opinion.

The checklist is the "Master Prompt Checklist" (sections 1 to 11) the project owner kept for the Claude Code master prompt. Every item below was
checked against the code, the tests, the documents or the running application. "Today" means this evaluation; "carried" means earlier evidence that
no later change could have affected. Status words:

- **Met**: built and checked.
- **Partly**: built, but with a stated gap.
- **Not met**: not built.
- **Deferred**: the checklist itself makes it a future gate (real family data); not built, by design.

## Scoreboard

| Section | Met | Partly | Not met | Deferred | Items |
|---|---|---|---|---|---|
| 1. Project scope and architecture | 11 | 2 | 0 | 0 | 13 |
| 2. Product experience and visual design | 20 | 1 | 0 | 0 | 21 |
| 3. Guided family experience and analyst workspace | 25 | 1 | 0 | 0 | 26 |
| 4. Financial engine and modelling integrity | 22 | 3 | 1 | 0 | 26 |
| 5. Conversational copilot | 10 | 1 | 0 | 0 | 11 |
| 6. Holdings imports, database and persistence | 23 | 3 | 0 | 0 | 26 |
| 7. Authentication, security and privacy | 14 | 5 | 1 | 7 | 27 |
| 8. Local development, deployment and documentation | 21 | 2 | 0 | 0 | 23 |
| 9. Testing and acceptance criteria | 37 | 8 | 1 | 0 | 46 |
| 10. Change control | 10 | 0 | 0 | 0 | 10 |
| 11. Final deliverables | 10 | 0 | 0 | 0 | 10 |
| **All** | **203** | **26** | **3** | **7** | **239** |

**203 of 239 items are met (85%); 26 are partly met; 3 are not met; 7 are deferred by the checklist's own design (the real-data gate).** The counts are of
items, not of importance: the few unmet items (no independent optimiser cross-check, no encryption at rest, no automated browser test of the whole
wizard) matter more than the many met presentation items. "Met" means built and checked by the developer's own tests and reading; **nobody outside
the project has reviewed any of it.** Each partly-met or unmet item states its gap in the tables below; the priorities are at the end.

### Test results behind this evaluation (today)

| Suite | Result |
|---|---|
| Python (`pytest -q`) | **924 passed, 1 expected failure** (the Assistant's accuracy bar), 5 min 47 s, on a quiet machine |
| Web unit and component | **548 passed**, 24 files, 43 s |
| TypeScript (`npm run typecheck`) | clean |
| `npm audit --omit=dev` | 0 vulnerabilities |
| Browser tests (29) | **not re-run today**: they use port 5181, which the shared demo holds; last run 29 passed at Phase 8 and no web code has changed since |
| Backup and restore drill | passed (identical rows, integrity `ok`, no foreign-key violations, no migration applied on restart) |
| Through the real tunnel | 13 of 13 checks passed (earlier today) |

**A defect found by this run, now fixed (not yet committed).** The first full run today ended 921 passed, **1 failed**: the repository's own secret scanner
(`test_nothing_that_looks_like_a_secret_is_in_the_repository_files`) rejected a made-up password constant (a quoted three-word phrase assigned to a variable called `PASSWORD`) in the gate tests I
committed in `61b9894`. I had run only part of the suite before committing, so the commit left the full suite red. The scanner was right to be strict, so the
fix is in the test (the constant is now built from three words instead of written out); the scanner was not loosened. The whole suite then passed.

## 1. Project scope and architecture

| Item | Status | Evidence |
|---|---|---|
| React frontend | Met | `web/` (React 19) |
| Vite build tooling | Met | Vite 8; production build today (about 960 KB of JavaScript) |
| TypeScript | Met | `tsc` clean for the app and the browser tests (today) |
| Python FastAPI backend | Met | `api/`; 32 operations ([api.md](api.md)) |
| Preserve the Python financial engine | Met | Numbers frozen by the golden master (passes today). Source differs from `main` by a seven-line `optimiser_converged` flag, disclosed ([architecture.md](architecture.md)) |
| Inspect the repository first | Met | Phase 0 report |
| Inspect existing tests and Git changes | Met | Phase 0 baseline; Git history clean since |
| Baseline of 102 tests | Met | 102 passed at Phase 0; none removed since (no test file was ever deleted; the 910 now include them) |
| Define API contracts | Met | Generated OpenAPI file, generated TypeScript types and API reference, each guarded by a test |
| Evaluate SQLite versus PostgreSQL | Met | [ADR-0017](adr/0017-react-fastapi-migration.md): SQLite with numbered migrations; PostgreSQL deferred, with reasons |
| Run locally in Chrome/Chromium | Partly | Tested in Microsoft Edge (Chromium) only; Chrome itself, Firefox and Safari were not |
| Avoid mandatory Electron packaging | Met | None |
| Keep a path to hosted deployment | Partly | Documented ([deployment-react.md](deployment-react.md)); never run on a host or on Linux; a temporary tunnel was run today |

## 2. Product experience and visual design

| Item | Status | Evidence |
|---|---|---|
| Original institutional-fintech design system | Met | [design-system.md](design-system.md); owner reviewed Phase 2 |
| Modern fintech polish | Met | Screens read today (Overview, plan, results, scenarios, holdings); owner reviewed |
| Collapsible left sidebar | Met | "Collapse sidebar" control; `AppShell` tests |
| Contextual panels | Met | "Why?" side panel (focus trap, Escape) tested in the browser |
| Light and dark themes | Met | Theme chooser; browser test; both axe-audited |
| Responsive layouts | Met | Browser tests: no sideways scrolling on a phone, drawer menu, tap-sized controls. Real phone not tried |
| Accessible forms and navigation | Partly | Automated axe audits, keyboard-only browser tests, contrast checks. No manual screen-reader test |
| Reusable design components | Met | `web/src/ui`, `charts`, `layout` |
| Loading, empty, success and error states | Met | Seen live today ("Loading the profile", "No holdings imported yet", "Your profile now uses these holdings."); unit tests for error states |
| Consistent charts and status indicators | Met | One chart frame (text summary, chart/table switch) and one status vocabulary (OK / Warning / Problem) |

### Personalised dashboard

| Item | Status | Evidence |
|---|---|---|
| All eight modules exist | Met | Listed on the customise panel today |
| Select exactly four | Met | Four slots; API refuses anything else |
| Preview the selection | Met | "Preview" strip in the customise panel |
| Reorder modules | Met | Slot order is display order; unit tests for `place` |
| Replace one module with another | Met | Browser test replaces slot 4 |
| Save and restore a configuration | Met | `PUT /api/dashboard` saves; `DELETE` restores the default four |
| Preferences persist across reloads | Met | Browser test reloads and sees the choice |
| All eight remain available through navigation | Met | The other four are listed with where they live ("in Recommendation", "in Risk and liquidity", "in Holdings") |
| A sensible default selection | Met | Allocation, liquidity, risk, stress |
| Account or profile decided | Met | Per account (decision D8, [ADR-0019](adr/0019-personalised-dashboard-and-analyst-workspace.md)) |
| Hiding a module never hides warnings | Met | Warnings sit above the modules; a test ("warnings are never hidden by the modules a person chooses") |

## 3. Guided family experience and analyst workspace

| Item | Status | Evidence |
|---|---|---|
| Six-step guided flow | Met | Walked through in a real browser today: About you, What's coming, Your comfort, Safety net, What you own, Your strategies |
| Wealth and spending inputs | Met | Step 1 |
| Upcoming commitments | Met | Step 2 (up to three, with a custom type) |
| Plain-language comfort with a bad year | Met | Step 3: Protect / Balance / Grow with rupee falls |
| Safety net and accessible reserves | Met | Step 4 |
| Current holdings inputs | Met | Step 5 |
| Review and strategy comparison | Met | Step 6; "Your answers" with an Edit button for each |
| Progress indicator and inline validation | Met | Stepper; field errors (for example the plan name) |
| Review and edit previous answers | Met | Stepper and the Edit buttons |
| Explanations of how inputs affect the plan | Met | "What this means so far" panel updates as you type |
| Strategy A Protect, B Balance, C Grow | Met | Results page today |
| Rupee-denominated illustrative action plan | Met | "Sell ₹15.6 Cr / Buy ₹8.4 Cr / Buy ₹14.9 Cr" |
| Caveats and assumptions | Met | "Kinds of product, not specific recommendations. Illustrative, on synthetic data." and the limits note on the results |
| Allocation and exposure analysis | Met | Allocation module, Recommendation page |
| Holdings and asset-class breakdown | Met | Holdings page, by class and by account |
| Strategy comparisons | Met | Mix selector; side-by-side under a scenario |
| Historical drawdown replay | Met | Risk exposure module and Risk and liquidity page |
| 95% one-month CVaR | Met | "95% 1-month CVaR" tile |
| Liquidity ladder | Met | Chart and table |
| Upcoming outflows | Met | Outflows chart |
| Preset and custom stress scenarios | Met | Five presets plus "Your scenario" |
| Current portfolio versus alternatives | Met | Compare your options under one scenario |
| Model assumptions and methodology | Partly | In the Rationale module, the glossary and the Assistant ("How are the numbers produced?"); no dedicated methodology page in the app (written up in [methodology.md](methodology.md)) |
| Recommendation explanations and limitations | Met | "Why this recommendation", "Why?" panels |
| Drill-down analytical panels | Met | "Full view" links and the explanation panels |
| Both experiences use the same backend calculations | Met | One engine service; parity tests |

## 4. Financial engine and modelling integrity

| Item | Status | Evidence |
|---|---|---|
| Six asset classes | Met | Five market classes plus the illiquid bucket |
| Constrained mean-variance with SLSQP | Met | `fo/engine.py::solve_weights` |
| Monthly covariance estimation | Met | `estimate_inputs` |
| Schaefer-Strimmer shrinkage | Met | `shrink_cov` |
| Daily historical drawdown replay | Met | `replay`, `max_drawdown` |
| 50% history / 50% priors | Met | Golden master (today) |
| Existing long-run priors | Met | 11%, 12.5%, 7%, 6.5%, 6%; checked against the document by a test |
| 4.5% inflation | Met | Same |
| Protect, Balance, Grow thresholds | Met | 8% and 2%, 15% and 4%, 25% and 6%; seen on screen today |
| Illiquid assets fixed | Met | Held fixed in the optimiser; shown "Illiquid (fixed)" |
| Liquidity haircuts | Met | 0, 8, 15, 30, 40 and 100%; test compares document and code |
| 95% one-month CVaR | Met | `cvar_21d` |
| Typical-year range and worst year | Met | "+3.5% to +16.8%", "−6.8%" |
| 2020-style crash in rupees | Partly | Shown as "In a severe market crash" (−₹15.5 Cr), a stylised shock that says it is not a replay of any year; the relabelling from "2020-style" was never confirmed by the owner |
| Optimiser failure handling | Partly | A non-converged solve is flagged and a warning is shown; the mix is still displayed (with the warning), not withheld |
| Independent calculation checks | Met | Hand-worked cases (for example a 25% equity fall costs exactly ₹137.5 Cr for the gap family), 14 random-profile invariants through the API |
| Cross-check against an independent optimiser | Not met | Suggested; not built |
| No silent financial-model changes | Met | Golden master passes (today) |
| All eleven protected assumptions | Met | Checked against the golden file and the document |
| Real-return goal reported, not a constraint | Met | "Meets your return goal: Not quite" never changes the mix |
| Illiquid assets accrue smoothly (not hidden) | Met | Stated on screen in the Risk module and in the docs |
| Liquidity cover may not bind (not hidden) | Partly | Documented ([protected-assumptions.md](protected-assumptions.md), [limitations.md](limitations.md)); **not shown on screen** |
| Thresholds and priors are provisional | Met | Glossary: "drafts, not forecasts and not externally validated" |
| History does not guarantee the future | Met | On screen: "Past sample returns do not predict future ones" (charts and plan results) |
| Not called optimal or independently validated | Met | No such wording in the app; a test fails if a document claims it |
| The ₹1,000 Cr example is computed, not hard-coded | Met | Produced by the engine from the profile; golden master |

## 5. Conversational copilot

| Item | Status | Evidence |
|---|---|---|
| Compare rule-based, LLM and hybrid | Met | [ADR-0021](adr/0021-grounded-explainer-copilot.md); owner's research |
| Development effort and cost | Met | ADR-0021 |
| Privacy implications | Met | ADR-0021 (nothing leaves the machine; question not stored) |
| Reliability and hallucination risk | Met | ADR-0021; a digit cannot reach an answer without a source figure |
| Testability and extensibility | Met | Five pinned question sets; evaluation tool |
| Approval before paid API or external data | Met | None used; the optional local model was fetched once with approval |
| Explanations grounded in engine outputs | Met | 3,440 figures in 336 answers each equal the engine's value |
| Explains recommendations, liquidity, scenarios, assumptions | Met | Twenty question types |
| Prevents fabricated calculations or claims | Met | Digit guard test; fixed refusals |
| Prevents autonomous execution of trades | Met | No such capability; action requests get a fixed refusal |
| Assistant routing accuracy | Partly | 79% on fresh questions against an 85% bar (word matching alone 71%); it never invents a figure |

## 6. Holdings imports, database and persistence

| Item | Status | Evidence |
|---|---|---|
| Manual asset-class entry remains | Met | Family profile editor |
| CSV import | Met | [holdings-import.md](holdings-import.md) |
| Excel import | Met | `.xlsx`, defensively parsed |
| Documented sample template | Met | "Download a template"; `GET /api/holdings/template` |
| File type and size validation | Met | 150 KB, 1,000 rows, 30 columns, type sniffing |
| Preview before saving | Met | "Rows read", columns used, every line, totals |
| Column mapping where useful | Partly | Headings are recognised automatically and class labels are assigned by the person ("Class for Equity"); there is no interactive column picker |
| Missing-value and duplicate checks | Met | Row errors for empty fields; repeated rows warned; identical imports refused |
| Row-level and field-level errors | Met | "Row 8: …", with row and field |
| Mapping to the six asset classes | Met | Synonym table; unknown labels never guessed |
| Explicit illiquid treatment | Met | "Illiquid (held fixed)" |
| Confirmation before saving | Met | Import, then a separate "Use these holdings in my profile" |
| No silent overwriting | Met | Apply is explicit, with a before and after table |
| Summary of imported, rejected and skipped rows | Partly | Rows read, lines, problems and totals are shown; the import is all-or-nothing, so nothing is silently skipped, but there is no "rejected / skipped" tally |
| Future regulated integrations documented, not built | Met | [limitations.md](limitations.md) |
| Inspect the existing SQLite implementation | Met | Phase 0 |
| Compare SQLite with PostgreSQL | Met | ADR-0017 |
| Recommend a database and trade-offs | Met | ADR-0017, [database.md](database.md) |
| Preserve existing data-access logic | Met | `fo/accounts.py` shared with Streamlit |
| Persist accounts and profiles | Met | `users`, `profiles` |
| Persist holdings and inputs | Met | `holding_imports`, `holdings` |
| Persist dashboard preferences | Met | `dashboard_preferences` |
| Results stored or recomputed (defined) | Met | Recomputed on request with a cache; documented |
| Database migrations | Met | Three numbered migrations; verified on four database states |
| Test persistence across restarts | Met | `test_data_survives_an_application_restart` in `tests/test_api_database.py` |
| Backup and recovery for a pilot | Partly | Documented, and **a backup and restore drill was run today on the live demo database** (rows, integrity and foreign keys identical; the restart applied no migration). No schedule, off-site copy or retention policy |

## 7. Authentication, security and privacy

### Local prototype safeguards

| Item | Status | Evidence |
|---|---|---|
| Clearly identified demo login | Met | "Or explore a demo family"; "Synthetic data" badge |
| Synthetic data only | Met | Stated on sign-in, README and every page footer |
| No secrets committed | Met | Pattern scan of every tracked file: none (today); built bundle: none (today) |
| `.env.example` with placeholders | Met | Corrected in Phase 8 (nothing reads a `.env` file) |
| Server-side authentication and authorisation | Met | Server-side sessions on every non-public route (8 public, 8 signed-in, 16 with CSRF) |
| User and family isolation | Met | Another account's profile answers 404 (tests and a browser test) |
| Protection against identifier manipulation | Met | Same |
| Input validation | Met | Strict request models; error text never echoes input |
| Secure password hashing | Partly | scrypt with a random salt, but cost N=2^14, below current guidance of 2^17 |
| Safe error handling | Met | Generic 500s; one error shape |
| Appropriate local CORS | Met | Origin allowlist, JSON only |
| Security tests (protected endpoints, cross-user) | Met | 52 security-review tests, 14 invariant tests, and browser tests for cookies, CSRF, hostile files, injected markup, headers and the security policy |

### Future production gate

| Item | Status | Evidence |
|---|---|---|
| Production-grade authentication and sessions | Deferred | Own sign-in; [ADR-0022](adr/0022-authentication-own-or-managed.md) proposed |
| Password reset and recovery | Deferred | None |
| Persistent database and tested recovery | Partly | SQLite persists; recovery drill passed today; no schedule or off-site copy |
| Encryption in transit | Partly | Verified through the real tunnel (https, secure cookie, strict headers); a production certificate was never set up |
| Encryption at rest | Deferred | **Not encrypted**: the file starts "SQLite format 3" and holds names and profile text in plain bytes (checked today) |
| Secure secret management | Deferred | No secrets exist yet; nothing to manage |
| Audit logging | Deferred | None |
| Upload security | Met | Hostile-file tests (macros, zip bombs, formulas, oversize), browser tests |
| Rate limiting and abuse protection | Met | Per-route limits (in memory, per process) and the gate's lock-out |
| Dependency and vulnerability review | Partly | `npm audit`: 0 (today). Python: advisories in Pillow only at Phase 7; `pip-audit` is not installed, so **not re-run today** |
| Privacy, consent, retention, deletion | Deferred | None; no account deletion or export |
| Review of Indian privacy obligations | Not met | Mentioned in [deployment.md](deployment.md); no review |
| Review of SEBI Investment Advisers applicability | Partly | Positioned as outside regulated advice ([ADR-0001](adr/0001-prototype-on-synthetic-data.md)); a summary in ADR-0021, explicitly not legal advice |
| Incident response and monitoring | Deferred | None |
| Explicit readiness approval before real data | Met | The gate is [production-readiness.md](production-readiness.md) section A, repeated in the README |

## 8. Local development, deployment and documentation

| Item | Status | Evidence |
|---|---|---|
| Frontend starts locally | Met | `npm run dev`, or the demo launcher (20 seconds) |
| FastAPI backend starts locally | Met | Same |
| Chrome/Chromium browser workflow | Partly | Edge (Chromium) |
| Required software versions documented | Met | [setup.md](setup.md) |
| Dependency installation instructions | Met | Same; verified from a fresh clone |
| Environment setup documented | Met | [configuration.md](configuration.md) |
| Database initialisation and migrations work | Met | Verified |
| Test commands documented | Met | [testing.md](testing.md) |
| Synthetic demo account setup and reset | Met | Seeded automatically; throwaway copies; `demo\start-demo.cmd` gives a fresh database each time |
| Troubleshooting instructions | Met | [handover.md](handover.md) |
| Practical, low-cost pilot architecture recommended | Met | One small host ([plan-sharing-and-deployment.md](plan-sharing-and-deployment.md)) |
| Hosting topology documented | Met | Same; [deployment-react.md](deployment-react.md) |
| Required environment variables listed | Met | Tested against the code |
| Secret management documented | Met | "No secrets exist"; where they would go |
| Build and startup commands | Met | Verified |
| Persistent storage requirements | Met | One disk, one process |
| Backup and recovery addressed | Met | Documented; command proven today |
| Health checks and logging considered | Met | `GET /api/health`; logs in the demo folder; no monitoring |
| Cost considerations documented | Partly | Free tiers and plan terms are noted; **no prices were checked** |
| Rollback procedures | Met | [deployment-react.md](deployment-react.md) section 5 |
| Container configuration tested if introduced | Met | None introduced for the API (the Streamlit `Dockerfile` is stated as untested) |
| Deployment not claimed unless verified | Met | Every guide line is labelled verified or untested |
| Documentation set (14 items) | Met | [docs/README.md](README.md): architecture, setup, run, environment, database, API, methodology, import format, testing, deployment, readiness checklist, limitations, changelog, handover |

## 9. Testing and acceptance criteria

### Regression and financial

| Item | Status | Evidence |
|---|---|---|
| Original suite run before modifications | Met | Phase 0: 102 passed |
| 102-test baseline preserved | Met | All still present |
| Changed, removed or skipped tests explained | Met | None removed; a few tests skip only when the optional model files are absent; 1 strict expected failure (the Assistant's accuracy bar), documented |
| Allocation-weight constraints | Met | `test_weights_respect_sum_and_limits` |
| Invalid and missing inputs | Met | Profile and API validation tests |
| Infeasible optimisation | Met | "unless flagged" tests and invariants |
| Expected-return calculations | Met | Golden master |
| Drawdown and CVaR | Met | Hand example and golden master |
| Liquidity coverage and haircuts | Met | Hand calculation test, golden master |
| Stress-scenario losses | Met | Exact ₹137.5 Cr check, scenario tests |
| Inflation and spending assumptions | Met | Projection and outflow tests |
| Illiquid-asset treatment | Met | Engine and import tests |
| Strategy comparisons | Met | Comparison tests |
| Hand-worked calculation checks | Met | Several |
| Behavioural sanity checks for risk aversion | Met | "higher risk aversion never raises volatility" and similar |
| Independent cross-check where practical | Not met | No second optimiser |

### Security

| Item | Status | Evidence |
|---|---|---|
| Unauthenticated access rejected | Met | Walked over every operation |
| Invalid sessions handled | Met | Tests |
| Cross-user and cross-family access blocked | Met | 14 profile-scoped operations all answer 404 |
| Manipulated identifiers do not bypass | Met | Same |
| Malformed requests rejected safely | Met | 415, 413, 422 tests |
| Invalid and oversized uploads rejected | Met | Parser and browser tests |
| Secrets not exposed in bundles or logs | Met | Bundle scan today; error handler never logs request bodies |

### End-to-end in a real browser

| Item | Status | Evidence |
|---|---|---|
| Launch the complete local application | Met | Browser tests start API and web servers |
| Sign in through the supported flow | Met | Browser tests |
| Open a synthetic family profile | Met | Browser tests |
| Complete the guided planning flow | Partly | Component tests and a manual walk through a real browser today; **no automated browser test of the whole wizard** |
| Generate and inspect strategy comparisons | Partly | Same |
| Inspect recommendation explanations | Met | Browser test of the "Why?" panel and the Assistant |
| Run stress scenarios | Partly | API and component tests; the scenarios page was read in a real browser today; not in the automated browser suite |
| Inspect risk and liquidity outputs | Partly | Every page is loaded by the policy test; values asserted at API and component level |
| Select exactly four dashboard modules | Met | Browser test |
| Reorder and save the dashboard | Partly | Replace-and-save is in the browser suite; reordering is covered by unit tests |
| Reload and verify saved preferences | Met | Browser test |
| Navigate to all eight modules | Partly | All pages are visited by the policy test; each module is checked at component level |
| Import a valid holdings file | Met | Browser test |
| Reject an invalid holdings file safely | Met | Browser tests |
| Switch light and dark themes | Met | Browser test |
| Missing-data and calculation-failure behaviour | Partly | Component tests of error states; no browser test |

### Final build

| Item | Status | Evidence |
|---|---|---|
| Frontend production build succeeds | Met | Today |
| Backend starts correctly | Met | Today |
| Database initialisation and migrations | Met | Verified |
| Tests run from documented commands | Met | Clean-room run |
| Local setup works in a clean environment | Met | Fresh clone (Windows) |
| Deployment configuration tested where feasible | Partly | The tunnel and gate were run today; no host, no Linux, no container |
| Unverified checks and blockers reported | Met | [limitations.md](limitations.md), the audit |

## 10. Change control

| Item | Status | Evidence |
|---|---|---|
| Inspected before implementing | Met | Phase 0 |
| Significant architecture changes approved | Met | Decisions D1 to D10, ADRs 0017 to 0021 |
| Financial-model changes approved | Met | None made |
| Paid external services approved | Met | None used |
| Sending data to external APIs approved | Met | None; one model download, approved |
| Real family data prohibited until the gate | Met | Everywhere |
| Existing functionality not silently removed | Met | Streamlit untouched on `main`; one early scaffold page replaced by design |
| Tests not deleted to pass | Met | No test file was ever deleted |
| A changelog and verification report per phase | Met | `CHANGELOG.md`, `docs/migration/phase-1` to `phase-8-report.md` |
| Waited for approval between phases | Met | Each phase started on the owner's word |

## 11. Final deliverables

| Item | Status | Evidence |
|---|---|---|
| Working application, locally | Met | Running |
| Preserved financial engine | Met | Golden master |
| Complete product workflows | Met | Guided plan, analyst pages, eight modules, customisation |
| Holdings import | Met | |
| Persistence | Met | |
| Test evidence | Met | 924 Python, 548 web, 29 browser (last run), the backup drill and the tunnel checks; the table near the top |
| Environment and setup | Met | |
| Deployment preparation | Met | Documented; not deployed |
| Technical documentation | Met | |
| Final limitations report | Met | [limitations.md](limitations.md) |

## What to fix next, in order

1. **Show on screen that the liquidity requirement does not shape the mix** when it does not (section 4). One sentence from `liquidity_binding`; no number changes.
2. **Add browser tests** for the guided plan from start to strategies, the stress scenarios and a calculation failure (section 9). They need the demo stopped, because the browser tests use port 5181.
3. **Confirm or revert "In a severe market crash"** with the owner (section 4).
4. **Raise the password hashing cost** with a versioned hash, which needs a decision about the database shared with Streamlit (section 7).
5. **Install `pip-audit`** (a development tool) and re-run the Python advisory check (section 7).
6. **Try Chrome and a phone**, then a Linux run, before any real host (sections 1 and 8).
7. **Price a host** (section 8) once the owner chooses one.

None of the "Not met" or "Deferred" items blocks the synthetic-data demo; every one of them blocks real family data.
