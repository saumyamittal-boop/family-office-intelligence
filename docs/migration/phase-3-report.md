# Phase 3 report: Guided planning

**Date**: 2026-10-19 · **Branch**: `react-migration` (Phases 1 and 2 are committed as `88fae33` and `bdf1494`; Phase 3 is in the commit that adds this report) ·
**State**: built and verified by tests, a real-browser walk-through and measurements. Nothing is pushed. **The approval gate for this phase is "Verify
financial outputs"**: the numbers below are checked against the frozen golden master, but the wording and the feel are yours to review.

## What was built

| Area | Delivered |
|---|---|
| The six steps | About you, What's coming (up to three commitments), Comfort with a bad year, Safety net, What you own, then Your strategies |
| Live read-out | "What this means so far" follows every answer: wealth, the safety net needed, how the money divides, outflows by year, and plain sentences on how the answers shape the plan |
| Strategies | Strategy A, B and C cards (typical year, worst year, a severe market crash in rupees, safety net, return goal), a year-range chart with a table view, the chosen strategy's donut, what to buy and sell by kind of fund, the reasons, and an assumptions and limits card |
| Dynamic controls | A "Try a change" card (comfort, safety net, spending) whose changes flow into the strategies; an "Your answers" list where every answer can be edited and returns straight to the strategies |
| Navigation | A progress bar (any reached step can be revisited), the browser's Back button moves between steps, the plan resumes after a reload, "Start over", and a brand-new account lands on the plan |
| API | `GET /api/plan/config`, `POST /api/plan/preview`, `/strategies`, `/save` (ADR-0018) |

## How "dynamic" it is, measured

| Interaction | Result |
|---|---|
| Typing in an answer | The read-out says "Updating…" at once and keeps the old figure; it follows about 0.4 s after typing stops; the server answers in about 7 ms |
| First calculation of three strategies | 3.0 to 3.4 s (three optimiser runs), with a working state and skeleton cards |
| Switching comfort level | 117 ms, **zero** requests (the strategies do not depend on it, so the cards update from data already on the page) |
| Changing the safety net or spending | "Updating…" at once, all three cards stay visible (dimmed), one request, then settles |
| Invalid value | Message and a blocked Continue at once; the value is never sent to the server |
| Reload mid-plan | Resumes at the same step with the same answers (this tab only) |

Not included, by design: live market data. That needs your approval, a licence for the data, and the privacy gate.

## Changes to existing code

| File | Change | Effect on numbers |
|---|---|---|
| `fo/formatting.py` (new), `fo/ui.py` | Rounding helpers moved into a pure module shared by both apps; `ui.py` re-exports them | none (the 1,350 formatter vectors still match) |
| `api/analysis.py`, `api/schemas.py` | Every analysis option now carries `year_range` (typical year, median, worst, best) | none (additive) |
| `api/routers/profiles.py` | A stored profile that makes the engine divide by zero returns a clear 422 instead of a 500 | none |
| `api/main.py` | A per-person limit of 40 strategy calculations a minute | none |
| `web/` | Plan pages and components; "Plan my money" is no longer marked "Soon" | none |
| Tests | One Foundation assertion that "Plan my money" was a placeholder now checks "Recommendation"; one timing-dependent Phase 1 test now polls instead of sleeping | n/a |

The engine (`fo/engine.py`) was not touched in this phase.

## Evidence

| Check | Result |
|---|---|
| Plan API tests | **60 passed** (`tests/test_api_plan.py`): auth, CSRF, validation, the preview against the engine, the strategies, saving, isolation, limits |
| Financial parity | The strategies for both guided golden cases match the frozen golden master field by field, through the real HTTP API; the saved profile analyses to exactly the strategy's numbers |
| Python suite | **289 passed in 168 s** (the earlier 229 plus 60 new), run with nothing else running |
| Web suite | **240 passed in 16 files**; type check clean; production build succeeds (861 KB JavaScript, 259 KB gzipped) |
| Accessibility (axe, WCAG 2.2 AA) | Every question step, the results as pictures and as tables, and after saving: zero violations in light and dark |
| Contrast in the real browser | 196 text elements on the results and 69 on step 5: zero failures in both themes |
| Real-browser walk-through | Sign-up lands on the plan; all six steps, validation, adding and removing commitments, comfort, the safety net, an amount that breaks the 95% rule, results, comfort switch, safety-net change, saving twice, editing an answer and returning, browser Back |
| Hand checks | 3 + 3.135 of indexed spending + an 8 Cr commitment = 14.1 Cr for 24 months; 17.4 Cr of outflows is 10% of the 175 Cr that can be invested |

## Findings

1. **A real production bug, found by a test:** the heading did not take focus on a new step in a production build. The "do not steal focus on first open" guard
   reset every time a step remounted; it only worked in development because React runs effects twice there. Fixed: the page now tells each step whether
   the person has navigated.
2. **Invalid markup, found by the audit:** the answer review was a `<dl>` containing buttons. Now a list.
3. The step buttons read "Step 1 of 6:About you" to screen readers (the space was collapsed). They now carry an explicit label, including "(done)".
4. **A latent engine defect** (protected, not changed): with zero spending and no commitment inside the safety-net window, `scenario_row` divides by zero. The
   Streamlit app would hit it too. The API refuses such answers with a clear message.
5. A Phase 1 test slept a fixed time and failed once on a busy machine; it now polls.
6. Bundle size is now 861 KB (259 KB gzipped). Route-level code splitting is a later optimisation.

## Not done and not verified

- **Visual review of the wizard is yours.** I saw the results cards, the year-range chart and the first step (dark theme) on screen. I did not see the question
  steps in the light theme or the whole wizard at phone width; those are checked by measurement and tests, not by eye.
- A keyboard-only run with real key presses (focus moves are tested, not driven by a person's keyboard); no Playwright browser tests yet (Phase 7).
- The strategy-calculation limit and queue are per process; a shared limiter is a Phase 7 item. An analysis in flight cannot be cancelled when newer answers arrive.
- The "crash" wording change was applied on the strength of the Phase 2 recommendation, without a separate yes from you. Reverting is one line.
- Still open from before: the liquidity-cover requirement never limits the mix; the screens say so, the model is unchanged.

## Decisions needed before Phase 4

1. Review the plan (both themes, desktop and phone) and say what to change.
2. Confirm or reverse the "In a severe market crash" wording.
3. Approve Phase 4 (the personalised dashboard and the analyst workspace). Module 8, Holdings Consolidation, depends on Phase 5, so Phase 4 will ship seven
   modules and the picker will mark the eighth "arrives in phase 5".
4. Decide whether to push the branch, once you are happy. Nothing has been pushed.

## Run it

See the README section "React + FastAPI version". Start the API (`uvicorn api.main:app --port 8100`) and `npm run dev` in `web/`, open http://localhost:5173, create an
account (it opens on the plan) or choose a demo family and open "Plan my money".
