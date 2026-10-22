# Production-readiness checklist

> **Genuine family data stays blocked.** This application is a prototype on synthetic data. It must not be given real client data, real
> account statements or a real password until every item in section A is closed (or consciously accepted in writing by the project owner and
> whoever is responsible for the family's data). Passing this checklist would still not make the model's output investment advice, and nothing
> here is a claim of regulatory compliance or of independent validation.

Status words: **Done** (built and tested), **Config** (a setting or step on the host; documented, not yet done anywhere), **Open** (work or
a decision still to do), **Not done** (nobody has done it). Evidence: [Phase 7 report](migration/phase-7-report.md) for security, [testing.md](testing.md)
for test results.

## A. Gate: close before any real family data

| # | Item | Status | Detail |
|---|---|---|---|
| A1 | Encrypt data at rest | **Open** | Profiles, imported holdings and sessions sit in a plain SQLite file. Needs disk or volume encryption and restricted file permissions on the host, or a database with encryption. |
| A2 | Account deletion and data export | **Open** | No way for a person to delete their account or export their data (data-protection rights). |
| A3 | Audit trail | **Open** | No record of sign-ins, imports or who changed a profile. |
| A4 | Password handling | **Open (decision)** | scrypt N=2^14 (below current guidance of 2^17), no reset, no email check, no second factor, no common-password check (minimum length 8). Raising the cost needs a versioned hash and ends sharing the database with the Streamlit app. |
| A5 | Demo sign-in off | **Config** | `FO_API_DEMO_LOGIN=0`. |
| A6 | Interactive API pages off | **Config** | `FO_API_DOCS=0` (the proxy in [deployment-react.md](deployment-react.md) does not forward them anyway). |
| A7 | HTTPS, secure cookie | **Config** | `FO_API_COOKIE_SECURE=1` and a certificate. Not tried on a real host. |
| A8 | Data-protection and legal review | **Not done** | Who operates the server, where data sits, consent, retention, breach process, and what rules apply to the people whose data it is. Nothing in this repository addresses regulation or compliance. |
| A9 | Backups with a tested restore | **Not done** | The command exists ([database.md](database.md)); no schedule, off-site copy or restore drill. |
| A10 | Outside security review | **Not done** | Phase 7 was a careful self-review with executable tests, not an audit or penetration test. |
| A11 | Run on the target operating system | **Open** | Everything was run on Windows only. Linux needs a run of the suites (a CI workflow on a Linux runner needs the branch pushed, or WSL or Docker on the development machine). The solver's thread problem was only seen on Windows. |
| A12 | Streamlit app on `main` | **Open (decision)** | Not part of any review; shares the account database; may freeze on Windows because of the solver finding. Retire it at cutover or review it. |

## B. Hosting and operations

| # | Item | Status | Detail |
|---|---|---|---|
| B1 | One API process only | **Config** | Rate limits, cache and the engine thread are per process, SQLite is one file. Do not run several workers or instances. |
| B2 | Real client address behind the proxy | **Config** | Verified with a simulated header: uvicorn trusts `X-Forwarded-For` from 127.0.0.1 by default. Behind a proxy on another machine use `--forwarded-allow-ips`. Not verified with a real proxy. |
| B3 | Proxy time-outs and body cap | **Config** | The app does not stop a deliberately slow client. Set header and body time-outs and a body limit at the proxy. |
| B4 | Security headers on the web files | **Config** | The Content-Security-Policy and others in `web/security-headers.ts`, set by the proxy. Proven with `vite preview` (a browser test), not on a real host. |
| B5 | Health probes use GET | **Config** | `HEAD /api/health` answers 405. |
| B6 | Server banner off | **Config** | `uvicorn … --no-server-header` (verified locally). |
| B7 | Process supervision and restart | **Open** | Nothing is set up; choose a service wrapper or systemd. |
| B8 | Logs, monitoring, alerts | **Open** | Unexpected errors are logged by the `fo.api` logger (method, path and traceback; never the request body); there is no log shipping, metric, uptime check or alert. |
| B9 | Shared limit store | **Open** | Only needed if more than one process is ever run. |
| B10 | Hosting choice | **Open (decision)** | Not chosen. See [deployment-react.md](deployment-react.md). |
| B11 | Idle timeout, "sign out everywhere" | **Open** | Sessions last 12 hours, no idle timeout; signing out in one browser leaves other browsers' sessions valid. |

## C. Evidence of quality

| # | Item | Status | Detail |
|---|---|---|---|
| C1 | Engine unchanged and protected | **Done** | Golden master for 4 families x 2 cover bases, and the API compared with it ([methodology.md](methodology.md)). |
| C2 | Automated tests | **Done** | Python, web unit and browser tests; counts and dates in [testing.md](testing.md). |
| C3 | Clean setup from a fresh clone | **Done (Windows)** | Phase 8; steps in [setup.md](setup.md). |
| C4 | Migrations on empty, partial and copied databases | **Done** | Phase 8; [database.md](database.md). |
| C5 | Dependency audit | **Open** | npm: 0 vulnerabilities at Phase 7. Python: advisories in Pillow 12.3.0 only, no code path reaches it, and it cannot be upgraded while Streamlit and the embedding library cap it. Re-run before any deployment. |
| C6 | Browsers | **Open** | Edge (Chromium) only; Firefox and Safari untested. |
| C7 | Accessibility | **Partly done** | Automated checks (axe) on pages and dialogs, keyboard-only flows, contrast tokens checked. No manual screen-reader test and no claim of conformance to any standard. |
| C8 | Visual and manual review by a person | **Open** | The browser pane was hidden during development, so nothing was judged by eye by the developer; the project owner reviews the screens. |
| C9 | Assistant comprehension check | **Not done** | Planned with real people; has not been run. |
| C10 | Assistant routing accuracy | **Open (decision)** | 79% of fresh questions routed correctly against a bar of 85%. It never invents a figure; a miss gives a neighbouring question's answer or a decline. |

## D. Model and product

| # | Item | Status | Detail |
|---|---|---|---|
| D1 | Real market data | **Not done** | Everything runs on synthetic returns. A snapshot loader exists; no data, licence or quality checks. |
| D2 | Independent validation of method and assumptions | **Not done** | Priors, haircuts, thresholds and shock sizes are drafts. No out-of-sample test or cross-check against another optimiser. |
| D3 | Liquidity-cover constraint that never binds | **Open (decision)** | For the demo families the class limits already hold more cover than needed. |
| D4 | Two default cover bases | **Open (decision)** | Guided plan uses `strict`, analyst pages `all`. Results agree today only because of D3. |
| D5 | "In a severe market crash" wording | **Open (decision)** | Copy-only change from "A crash like 2020"; not separately confirmed. |
| D6 | Target customer | **Open (decision)** | To settle with the mentor. |
| D7 | Language-model features | **Not built** | Deferred by decision; would need separate approval and its own review (ADR-0021). |

## How to read a "ready" claim

If someone asks "is it production-ready?", the accurate answer today is: **no**. It is a working, tested prototype on synthetic data that is
reasonable to demonstrate and to test with synthetic files. Section A lists what stands between it and a pilot with real families.
