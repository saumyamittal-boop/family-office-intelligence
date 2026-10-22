# Project overview and architecture

**Family Office Intelligence** is a capital-allocation decision-support prototype for a family office, built as a 12-week BCom Financial
Analytics capstone. It shows a family's whole picture, proposes three mixes that fit the family's own limits, checks risk and liquidity, and
stress-tests the result. It runs on **synthetic data only** and is an **illustrative simulation, not investment advice**. Results depend on the
data, assumptions and methodology used; historical outcomes do not guarantee future performance. Requirements: [requirements.md](requirements.md).

Two front ends exist over one financial engine:

| | Streamlit app | React + FastAPI app |
|---|---|---|
| Branch | `main` (the live demo; the branch itself has not been touched by the migration) | `react-migration` |
| Entry | `app.py` | `api/main.py` (back end), `web/` (front end) |
| State | Python session | server-side sessions, JSON API |
| Docs | [deployment.md](deployment.md) | everything else in this folder |

The engine (`fo/engine.py`, `fo/plan.py`, `fo/data.py`, `fo/personas.py`) is shared. **Its numbers are unchanged by the migration**, which a golden
master proves. Its source differs from `main` in one place: a seven-line `optimiser_converged` flag (and one extra sentence in the explanation when
it is false), so a solver failure is no longer silent. On the `react-migration` branch the Streamlit pages were also slightly refactored to
share profile validation with the API (`fo/profile_form.py`; changes in `app_pages/profile.py` and `fo/ui.py`); the Streamlit tests still pass.

## Components

```
 Browser (React 19 + Vite + TypeScript)
   |  one origin: /           -> static files from web/dist
   |              /api/...    -> JSON, session cookie + CSRF header
   v
 Reverse proxy (production)  or  Vite dev server / `vite preview` (development)
   v
 FastAPI app  (api/main.py, one uvicorn process)
   |-- middleware: Origin check, body guard (size, JSON only), security headers, CORS
   |-- routers: auth, profiles (+analysis, history, scenarios), plan, dashboard, holdings, explain, meta
   |-- AnalysisService: ONE long-lived engine thread, small result cache (api/analysis.py)
   |-- Explainer: reviewed templates + figures from the engine; optional local embedding model
   v
 Engine (fo/): estimation, SLSQP allocation, drawdown replay, liquidity, scenarios   <- pure functions, no I/O
   v
 SQLite file (data/app.db): users, sessions, profiles, imports, dashboard choices
```

| Layer | Where | Responsibility |
|---|---|---|
| Engine | `fo/engine.py`, `fo/plan.py`, `fo/data.py`, `fo/personas.py` | All finance. Protected: see [protected-assumptions.md](protected-assumptions.md). |
| Shared rules | `fo/profile_form.py`, `fo/holdings_import.py`, `fo/accounts.py`, `fo/security.py` | Profile validation, holdings parser, accounts and password hashing, throttling. Used by both apps. |
| Assistant routing | `fo/question_match.py`, `fo/question_embed.py`, `fo/question_hybrid.py` | Decide which reviewed answer a typed question maps to, or decline. |
| API | `api/` | HTTP shapes (`*_schemas.py`), routers, sessions, guards, cached engine service, migrations. No finance of its own. |
| Explainer | `api/explain_*.py` | Fills reviewed answer templates with engine figures and says where each came from. No language model. |
| Web app | `web/src/` | Pages, charts, forms, accessibility, themes. Types are generated from the API contract. |
| Streamlit app | `app.py`, `app_pages/` | The original front end, kept as it was. |
| Tools | `tools/` | Golden-master, OpenAPI, API-reference, formatter-vector and question-evaluation generators; model fetcher. |

## One request, end to end

1. The browser calls `/api/profiles/7/analysis?basis=strict` with its session cookie.
2. Middleware checks the `Origin`, limits the body, and adds security headers on the way out.
3. The route finds the signed-in account from the **server-side session** (never from anything the client sends), loads profile 7 *for that
   account only* (404 if it is someone else's), and counts the call against that account's rate limit.
4. `AnalysisService` looks for a cached result keyed by the profile's content and the cover basis. If none, it sends the job to the single
   engine thread and waits up to `FO_API_ANALYSIS_TIMEOUT` seconds (then answers 503 "busy").
5. The engine returns the current mix and three recommendations; the API converts them to the response shape and returns JSON.

## Design decisions that matter to an operator

- **One engine thread, never exiting.** SciPy's HiGHS solver can hang or crash the process on Windows when a thread that used it exits, and SLSQP
  should not run twice at once. So all engine work is serialised on one long-lived thread. Consequence: one analysis at a time per process
  (about a second each), and the per-process cache and rate limits are not shared between processes. Evidence: [Phase 4 report](migration/phase-4-report.md).
- **One API process per database file.** SQLite plus in-memory throttles and cache. See [database.md](database.md) and [deployment-react.md](deployment-react.md).
- **API and web on one origin.** The built web app calls the relative path `/api`. In production a reverse proxy serves the static files and
  forwards `/api`; that keeps the cookie `SameSite=Lax`, avoids CORS, and lets one Content-Security-Policy cover the page.
- **Contract first.** `web/src/api/openapi.json` is generated from the running API, the TypeScript types are generated from it, and tests fail if
  either is stale. [api.md](api.md) is generated the same way.
- **No outbound calls at run time.** The server does not call any external service. The optional embedding model is fetched by a separate command
  and read from disk; the server never downloads anything.

## Security model in one paragraph

Server-side sessions (only a SHA-256 hash of the cookie's token is stored; cookie is `HttpOnly`, `SameSite=Lax`, `Secure` over HTTPS), a CSRF
header on every state-changing call, an `Origin` allowlist, JSON-only and size-limited bodies counted as they arrive, scrypt password hashes,
per-account ownership checks on every profile route (another account's id answers 404 exactly like a missing one), per-route rate limits, generic
500 errors that never echo input, a strict Content-Security-Policy and security headers on the web app, and a defensive file parser for uploads. These
are tested ([Phase 7 report](migration/phase-7-report.md)) but **have not been reviewed by an outside specialist**, and several limits remain
([production-readiness.md](production-readiness.md)).

## What the app does, by page

Sign-in and demo families; **Overview** (a personalised dashboard of four modules chosen from eight); **Plan my money** (a six-step guided flow that
recalculates live); **Recommendation**, **Risk and liquidity** and **Scenarios** (the analyst pages); **Family profile** (every input, several
profiles per account); **Holdings** (CSV/Excel import and consolidation, [holdings-import.md](holdings-import.md)); **Assistant** (questions
answered from the model's own figures, [ADR-0021](adr/0021-grounded-explainer-copilot.md)). What is built and what is only planned:
[limitations.md](limitations.md).

## Repository map

| Path | What |
|---|---|
| `fo/` | Engine and shared Python code |
| `api/` | FastAPI back end (`routers/`, `migrations/`) |
| `web/` | React front end (`src/`, `e2e/` browser tests, `public/`, `security-headers.ts`) |
| `app.py`, `app_pages/`, `.streamlit/` | Streamlit app |
| `tools/` | Generators and evaluation scripts |
| `tests/` | Python tests (`tests/golden/` holds the frozen engine output and the Assistant's question sets) |
| `data/` | Local state: `app.db`, optional `models/` and `snapshot/` (all git-ignored) |
| `docs/` | This documentation; `adr/` decision records; `migration/` phase reports |
| `requirements*.txt` | Python dependencies (runtime, API extras, dev) |
| `Dockerfile` | For the Streamlit app only; **not build-tested** |
