# Phase 4 report: Personalised dashboard and analyst workspace

**Date**: 2026-10-19 · **Branch**: `react-migration` (Phases 1 to 3 are committed; Phase 4 is **not committed yet**, as agreed: commit only when asked) ·
**State**: built and verified by tests, measurements and a real-browser pass. Nothing is pushed. **The approval gate for this phase is "Verify the
dashboard behaviour and the analyst workspace"**: the numbers are checked against the engine and the golden master; the look, the wording and the
choice of what a module shows are yours to review.

## What was built

| Area | Delivered |
|---|---|
| Dashboard | Four headline tiles, the warnings bar, a mix switch (Current, Growth, Balanced, Defensive), and **the four modules the person picked**, in their order |
| Customise | A panel with four slots (choose a module for each; picking one already used swaps the two), move up and down, a layout preview, a list of all eight modules with where each lives, Save, Cancel and Restore default |
| Per-account memory | The choice is stored on the account (migration `002`), restored after sign-out or a restart, and private to that account; default: allocation, liquidity, risk, stress scenarios |
| Seven modules | Allocation and actions · Liquidity and commitments · Risk exposure · Stress scenarios · Net worth and projection · Historical performance · Why this recommendation. Each has a glance size (on the dashboard) and a full size (on the analyst pages) |
| Eighth module | Holdings consolidation: listed, marked "arrives in phase 5", refused by the server until then |
| Analyst pages | **Recommendation** (mixes side by side, a measures table, buy and sell, projection, reasons, the method and its limits) · **Risk and liquidity** (drawdown against the person's limit, 95% CVaR, liquidity ladder, outflows, value history, calendar-year returns, a typical year) · **Scenarios** (five built-in scenarios with what each assumes, six custom dials, every option compared under any one scenario, all results) |
| Family profile | Every input editable in the units people use (percent, years, ₹ Cr), several profiles per account, new, save, save as new, delete with a confirmation; checks as you type; the server's refusals are shown |
| New API | `GET/PUT/DELETE /api/dashboard` · `GET /api/profiles/{id}/history` · `POST /api/profiles/{id}/scenarios`; `/api/meta` now carries the built-in scenarios and the dial limits; the analysis carries `current_ladder` and `current_scenarios` |

## Evidence

| Check | Result |
|---|---|
| Python suite | **390 passed in 227 s** (298 before this phase), run under the stack-dumping watchdog; nothing stalled. New: dashboard API (31), analyst API (55), engine-thread pooling and the stall regression test, recorded profile verdicts, plus the golden-master and contract updates |
| Web suite | **486 tests in 22 files** passed (255 before this phase); type check clean; production build succeeds at about 933 KB of JavaScript (278 KB gzipped; 861 KB / 259 KB after Phase 3). Splitting the bundle by page is a later optimisation |
| Golden master | Extended **additively** (two new fields per family and basis): every existing value was first re-checked and reproduced; 1,040 lines added, none removed. The engine file `fo/engine.py` is untouched in this phase |
| Numbers through the real API | Every built-in scenario, for the current mix and each option, equals the analysis endpoint's own result (which the golden master covers); a custom scenario equals both a hand calculation and the engine called directly; the value curves equal an independent replay, and the deepest point on the drawdown chart equals the engine's worst drawdown to within a millionth |
| Editor against the server | 115 profiles recorded with the server's verdict (edges included); the editor reaches the same verdict on every one |
| Mutation checks | Four deliberate breakages (mid-cap multiplier, history thinning, curve scale, "four different modules" rule) were each caught by a test, then reverted |
| Warnings never hidden | A test runs seven different four-module choices and requires the liquidity-shortfall warning and the headline tiles in each |
| Accessibility (axe, WCAG 2.2 AA) | Dashboard (pictures, tables, other modules), the customise panel (also showing a save error), the three analyst pages (pictures and tables), the assumptions table, the profile page (loaded, with problems, with an added row): zero violations in light and dark |
| Contrast in the real browser | About 1,000 text elements on five pages in both themes, plus the customise panel in both: zero failures |
| Real-browser pass | Customised (replace and swap), saved, reloaded: restored; moved the equity dial from −25% to −50%: the result went from −12.8% to −17.0% and the drawdown check flipped to "breached"; edited a corpus in the profile editor: the list, the dashboard subtitle and the donut all showed the new figure; no page overflowed sideways at 375 px |

## The test stall: found and fixed

The intermittent test stall open since Phase 1 (and recorded in the Phase 3 report) has a cause, and it was not where I had been looking.

1. **Caught.** A watchdog loop over the API tests stopped making progress in one of six runs and wrote every thread's stack. The only Python code running was the main thread, stuck
   starting a new thread (the test client's helper); no engine thread, no request. The process was spending one full core (1,499 CPU-seconds in about 25 minutes) across 48 threads.
2. **Located.** I sampled the busy thread's instruction pointer eight times: always inside a 14-byte stretch of `scipy/optimize/_highspy/_core.pyd`, which is **HiGHS**, the linear-programming
   solver bundled with SciPy and used by the engine (`linprog`, `fo/engine.py:201`). A tight loop like that is a spin-wait.
3. **Reproduced with no application code.** A 40-line script that runs `linprog` in a fresh thread that then exits, over and over, **hung in 27 of 30 runs** (and crashed with a segmentation fault in one more).
   The same script with a thread that stays alive (one shared thread, or threads that park instead of exiting): **0 hangs and 0 crashes in 30 runs each**.
4. **Fixed in the API layer, not the engine.** An engine thread now never exits: when a service closes, its thread goes to a pool and the next service reuses it
   (`api/analysis.py`). In normal running there is one thread for the life of the process, as before. The solver, the engine and every number are untouched.
5. **Checked.** After the fix the API test files (264 tests) were run 10 times in a row under the watchdog, and the whole suite once: no stall. Before the fix, one of five comparable runs stalled. Ten clean runs alone would not prove much
   (if the old chance were one in five, ten clean runs would still happen about one time in nine); the evidence that carries the weight is the bare-script experiment (27 of 30 hung, against 0 of 30) and the regression test.
6. **Guarded.** Unit tests for the pooling (reuse, no growth over 25 open-and-close cycles, a busy thread is not reused until it finishes), and a regression test that runs the failing pattern
   in a separate process with a time limit. Against the old behaviour that test froze in every run I tried (5 of 5, the full 120 s each); against the fix it passes in 3 to 5 seconds.

What I have **not** established is the exact mechanism inside HiGHS and Windows. My hypothesis is that HiGHS shuts its worker threads down from a thread-exit routine while Windows holds the lock that
those workers also need, so the next thread creation waits forever; I had no native debugger to confirm it, and the fix rests on the experiment, not on the hypothesis. It was seen with SciPy 1.18.1
on this Windows machine (8 cores). It was not tested on Linux.

**Consequences worth knowing.**
- The Streamlit app runs the same solver on Streamlit's own short-lived script threads, so it could freeze in the same way when run locally on Windows. The deployed copy runs on Linux and has been
  running without complaint; I have not touched the app on `main`.
- The earlier containment (single engine thread, request timeout) turned the symptom into a "busy" answer only when a solve was slow; it could not help when thread creation itself froze. The earlier phase
  reports described the cause as "a native optimiser spin" and that was right about the library and wrong about the trigger.

## Changes to existing code

| File | Change | Effect on numbers |
|---|---|---|
| `api/analysis.py` | Engine threads pooled and never exit (above); the cache now keeps the portfolios as well as the response, so history and scenarios reuse them; `current_ladder` and `current_scenarios` added | none |
| `api/schemas.py`, `api/routers/*`, `api/main.py`, new `api/{dashboard,history,scenarios}.py`, migration `002` | New endpoints and models (ADR-0019) | none (new read-only calculations on engine results) |
| `tests/golden/engine_golden.json`, `tools/make_golden.py` | Two new keys per family and basis, added without regenerating the rest | none: all existing values re-verified first |
| `web/` | Dashboard, modules, analyst pages, profile editor, charts, tests | none |
| `NumberField`, `Card` | `NumberField` accepts an empty value; `Card` can nest its heading level | none |

## Findings

1. **The stall's cause (above).** The single most useful thing this phase did.
2. **A screen-reader fault, found by a test, in two places.** A hidden span after a link's visible text carried its own leading space, which assistive-technology name computation trims, so
   "Net worth and projection in Recommendation" could be read as "projectionin Recommendation". The same pattern was in the profile list and the amount-field labels. The space now sits outside the span.
3. **The editor and the server disagreed at the edge.** A holdings total of exactly 99.5% or 100.5% is refused by the server (Python 3.12's `sum` is compensated, so the total differs from a plain
   JavaScript sum in the last digit), and the 60-character name limit was not enforced in the editor. Found by the recorded verdicts; both fixed.
4. **The first regression test for the stall could not fail.** It gave the exiting thread a few milliseconds of grace that the real failure does not get; it passed on the old behaviour too. Rebuilt to mirror the failing pattern, and checked against both behaviours.
5. **The profile editor lost unsaved edits when the window regained focus.** The query library re-fetches stale data on focus, and my form restarted whenever its data changed. Found by reviewing my own code, reproduced with a
   test (the profile was fetched a second time), fixed: the profile is no longer re-fetched in the background, and the form restarts only after a save, from what the server stored.
6. **A page I had not ported.** The Streamlit Recommendation page has a measures table and a short "how these numbers are produced" explanation that my first version of the page lacked; both are now there, and the 75/50/25 positions are quoted from a constant the golden master guards.
7. **Still true and still open.** The liquidity-cover requirement never limits the mix (0 of 24 portfolios); the screens say so, the model is unchanged. Zero spending with no commitment in the safety-net window still divides by zero in the protected engine; the API refuses it with a clear message.

## Not done and not verified

- **Visual review is yours.** I could not take screenshots (the browser pane is hidden in this environment). I verified the dashboard, the three analyst pages and the profile editor through the page's own structure,
  measured layout at desktop, tablet and phone widths, scanned colour contrast in both themes, and drove the customise panel, the dials and the editor with scripted input. I did not see the pages by eye.
- Reordering is by move buttons and slot pickers, not drag and drop (see ADR-0019 for why).
- Holdings consolidation (module 8) waits for Phase 5.
- No Playwright end-to-end run yet (Phase 7); a keyboard-only run by a person is still to do.
- The history response is about 60 KB per profile; fine locally, worth compressing before a hosted pilot.
- The strategy and scenario limits are per process (Phase 7 item).
- The HiGHS finding is for this Windows machine; a Linux run of the minimal script would tell whether the hosted app needs the same care (it now has it anyway).

## Decisions needed before Phase 5

1. Review the dashboard and the three analyst pages in both themes, at desktop and phone width, and say what to change.
2. Approve the commit of Phase 4 to `react-migration` (not pushed).
3. Approve Phase 5 (holdings import and the database for it). It is the first phase that touches data shaped like real holdings, so the privacy gate applies: synthetic files only until you say otherwise.
4. Open from before: push the branch?; the liquidity-cover fix; the "In a severe market crash" wording; the target-customer decision with the mentor on Saturday 24 October.

## Run it

See the README section "React + FastAPI version". Start the API (`uvicorn api.main:app --port 8100`) and `npm run dev` in `web/`, open http://localhost:5173, choose a demo family and use **Customise dashboard**, or open
Recommendation, Risk and liquidity, Scenarios and Family profile from the menu.
