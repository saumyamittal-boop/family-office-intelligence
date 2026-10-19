# Phase 1 report: Foundation

**Date**: 2026-10-19 · **Branch**: `react-migration` (from `main` at `24e2bcb`; `main` is untouched) ·
**State**: built and verified on this machine. Nothing is committed or pushed. Waiting for approval to start Phase 2.

## What was built

| Area | Delivered |
|---|---|
| Safety net | `tools/make_golden.py` froze every engine output **before any code change**; `tests/test_golden.py` compares the live engine to it (14 tests) |
| Backend | FastAPI app in `api/`: health, meta, sign-up, log-in, private demo copies, log-out, profile CRUD, and a full analysis endpoint with an explicit cover basis |
| Database | Numbered SQL migrations (`api/migrations`), WAL mode, server-side sessions; the Streamlit tables are upgraded in place |
| Contract | OpenAPI exported to `web/src/api/openapi.json`; TypeScript types generated from it; a test fails if either drifts |
| Frontend | Vite + React 19 + TypeScript shell: sign-in, demo families, profile and cover-basis pickers, allocation, liquidity cover, explanation and scenario comparison |
| Formatting | A TypeScript formatter checked against 1,350 cases recorded from the Python one |

## Changes to existing code

| File | Change | Effect on numbers |
|---|---|---|
| `fo/engine.py` | +7 lines: `Portfolio.optimiser_converged` reads the solver's `success`; a failed solve adds one explanation line (D4) | none (golden master unchanged) |
| `fo/profile_form.py` (new) | Profile validation moved out of the Streamlit page; both apps call it (D3) | none |
| `app_pages/profile.py` | Calls `fo.profile_form` instead of its own copy | none |
| `fo/accounts.py` | Added `connect`, `create_throwaway_demo`, `purge_throwaways` (D9). Existing functions untouched | none |
| `fo/ui.py` | Rupee amounts now round half up, like percentages; ties such as 137.25 show 137.3 (was 137.2) | display only |
| `.gitignore`, `README.md`, `docs/adr` | New ignores; a stray form-feed in the README setup line fixed (it read `D:amily-office-intelligence`); run instructions; ADR-0017 | none |

Root `requirements.txt`, `app.py`, `.env` and `main` were not touched. API packages are in `requirements-api.txt`.

## Evidence

| Check | Result |
|---|---|
| Python suite | **229 passed** in 119 s (the original 102 + 127 new) |
| Web unit and component tests | **24 passed**; type check clean; production build succeeds (267 KB JS, 83 KB gzipped) |
| Engine vs golden master | all 4 families x 2 bases and 2 guided cases match at 1e-9 |
| **HTTP API vs golden master** | all 8 family/basis combinations match field by field, through the real API |
| Slide figures through the API | cover 50 of 120 Cr; equities -25% costs -137.5 Cr; all three options restore the cover |
| Tests can fail | removing the ownership check, and making the CSRF comparison always pass, were each caught (done in memory, nothing written); a one-point haircut change shows as 1 assumption diff and 316 downstream diffs |
| Real browser (Vite + API) | sign-in, analysis, reload keeps the session, logout ends it on the server, 375 px mobile layout has no horizontal scroll; JavaScript cannot read the session cookie; nothing is in localStorage |
| Security tests | 401 on every protected route; cross-user read/update/delete/analyse all return 404, identical to a missing profile; manipulated ids; user id never taken from the client; CSRF; Origin allowlist; JSON-only; body-size limit; throttle; expired and forged cookies; error bodies never echo input; generic 500 |
| Secrets | the access code exists only in the git-ignored `.env`; no secret in the OpenAPI file or the frontend bundle |

## Findings and open issues

1. **Intermittent test stalls, cause not found.** Three of the first five whole-file runs of `tests/test_api_parity.py` stalled until a limit I had set
   (70 s, 100 s and 10 min; the longest had used 630 CPU-seconds). The two I could locate were at different tests (business/all, then nextgen/all).
   Afterwards it did not recur in 191 standalone app-plus-analysis cycles and about 20 further runs of the file, including 3 under heavy CPU load, and
   not in the final full-suite run. Containment, built and tested: the engine runs on one daemon thread, a request waits at most 90 s and
   then gets a 503 "busy". If it recurs, run the solver in a worker process (Phase 7). **Unresolved; please treat as an open risk.**
2. pytest printed "Windows fatal exception: access violation" in 3 of 8 runs while the run still passed; the stack pointed at pytest's own
   temp-path code. Probably a first-chance exception reported by faulthandler; not confirmed.
3. A component test caught a real bug in my sign-in hook (clearing the whole cache orphaned the session query); fixed.
4. `openapi-typescript` does not support TypeScript 7, so TypeScript is pinned to 5.9.3.
5. Starlette's test client warns that `httpx` is deprecated in favour of `httpx2`. Harmless today; revisit when upgrading.
6. The browser console shows one 401 before sign-in. That is the expected "who am I" probe.
7. Carried from Phase 0 and unchanged: the liquidity-cover constraint never binds; illiquid holdings accrue smoothly; "a crash like 2020" is a
   stylised shock ([protected-assumptions.md](../protected-assumptions.md)).

## Not done and not verified

- Browser end-to-end tests with Playwright (planned for Phase 7); the real-browser check above was manual.
- A clean-machine install (fresh venv and fresh `npm install`) has not been tried.
- No hosted deployment, no Docker build, no HTTPS check. Cookie `Secure` is tested only as a setting.
- The throttle is per process and in memory; the body limit trusts `Content-Length` (fine for JSON, must be revisited for uploads in Phase 5);
  no password reset; no accessibility audit yet.
- Not started by design: design system, guided plan, dashboard, holdings import, copilot.

## Decisions needed before Phase 2

1. Approve Phase 2 (design system, navigation, light/dark themes, overview) on this branch.
2. Commit the Phase 1 work to `react-migration` (nothing is committed yet).
3. Confirm Recharts, or name another charting library, before the first chart is built.
4. Still open from before: how to fix the dormant liquidity constraint, and the "2020" wording.

## Run it

See the README section "React + FastAPI version". Short form: `uvicorn api.main:app --port 8100` and `npm run dev` in `web/`, then open http://localhost:5173.
