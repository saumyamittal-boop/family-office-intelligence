# Phase 7 report: Security and regression hardening

**Date**: 2026-10-22 · **Branch**: `react-migration` (Phases 1 to 6 are committed; Phase 7 is **not committed yet**, as agreed: commit only when asked) ·
**State**: reviewed, tested and fixed; nothing is pushed. **The approval gate for this phase is "Read the unresolved-limitations list and decide what must be closed before any real family uses this"**.
The deliverable the master plan asks for is *test evidence and a list of unresolved security and correctness limitations*: both are below. No financial assumption, number or engine file was changed.

## What was done

| Area | Done |
|---|---|
| Authentication and authorisation | Read the session, CSRF, sign-in, password, throttle, request-guard and error code; turned every claim into a test that walks the API's own OpenAPI document, so a new endpoint cannot be added without being classified (`tests/test_security_review.py`, 52 tests) |
| User and family isolation | Every profile-scoped route (14 operations) tried by a second account, in tests and in two real browsers: always "not found", never changed, never leaking a name |
| Imports, errors, configuration, secrets | Hostile-file tests from Phase 5 re-run; error shape and leakage tests; configuration parsing with garbage values; a scan of the working tree **and all ten commits** for secrets; dependency audits (npm, Python); a static scan for string-built SQL |
| Financial tests | 14 random but valid family profiles analysed through the real API under both cover bases (28 analyses), checking that allocations add up, the person's own class limits hold, held-fixed assets stay fixed, cover requirements are met or declared infeasible, no number is missing, and no profile crashes the server (`tests/test_financial_invariants.py`); the golden-master parity tests re-run |
| End-to-end tests | 29 browser tests in real Microsoft Edge against a real API and engine on separate ports with a throwaway database (`npm run e2e`): sign-in, lock-out, session handling, isolation between two browsers, the main journeys, hostile input, phone width, keyboard-only use, and the production Content-Security-Policy |
| Regression | Full Python suite, full web unit suite, type checks (app and browser tests), production build |
| Fixes | Seven real weaknesses found and fixed (below), none touching financial logic |

## Evidence

| Check | Result |
|---|---|
| Python suite | **774 passed, 1 expected failure** (708 before this phase; the expected failure is the router's accuracy bar from Phase 6, kept visible). The 66 new tests: 52 security, 14 financial |
| Web unit suite | **548 passed** in 24 files; type checks clean for the app and for the browser tests; production build succeeds |
| End-to-end suite | **29 passed** in about a minute (Edge, headless): `auth` 6, `flows` 5, `isolation` 2, `security` 7, `responsive` 3, `keyboard` 3, `csp` 3 |
| Every operation is classified | 32 API operations: 8 are public by design (health, meta, plan configuration, the question catalogue, the holdings template, sign-in, sign-up, demo) and **all 24 others refuse a caller who is not signed in**; the test fails if either list changes unannounced |
| CSRF | All 16 state-changing operations other than the three sign-in ones demand the token even when signed in; a token from one session is useless on another; a foreign `Origin` (including `null`) is refused |
| Isolation | All 14 profile-scoped operations answer "Profile not found." to another account, in the *same words and status as for a profile that does not exist*, and change nothing. In two real browsers, a private marker in one account's profile name never appeared on any of the other's screens, nor in an assistant answer |
| Sessions | 32-byte random tokens; only the SHA-256 hash is stored (the token appears nowhere in the database); expired sessions are refused; logout ends the session on the server (a copied cookie stops working); the cookie is `HttpOnly`, `SameSite=Lax`, and now `Secure` over HTTPS; a CSRF token is bound to one session; signing in always issues a new token and retires the browser's previous one |
| Passwords | scrypt with a random 16-byte salt, constant-time comparison, the same work for unknown usernames, identical answers for "wrong password" and "no such user", never in a response or a log; five wrong guesses lock a username (429) even against the right password |
| Real server (not the test client) | Run against uvicorn with raw sockets: an oversized *chunked* upload with no length answered 413, a chunked non-JSON body 415, garbage, a 70 KB header, a bad method, a double `Content-Length`, a path traversal: all answered or closed cleanly; a client that stalls mid-body did not block others |
| Mutation checks | **13 deliberate breakages of security controls, each caught by a test, then reverted**: CSRF never compared; profile ownership checked against the wrong user; expired sessions accepted; body guard off; origin check removed; cookie readable by scripts; cookie sent cross-site; login lock-out removed; security headers removed; session tokens stored in the clear; sign-in keeping the old session; the assistant's rate limit removed; errors leaking the exception |
| Dependencies | `npm audit`: **0 vulnerabilities** (production and development). `pip-audit` (OSV): **28 advisories, all in Pillow 12.3.0, fixed in 13.0.0** (see limitation 8). `bandit` over `api`, `fo`, `tools`: 2 findings, both false positives (the migration runner assembles SQL from our own committed files and an integer; a seeded test-data generator uses `random`) |
| Secrets | None in the working tree or in any commit (private keys, cloud keys, tokens, assigned passwords); the database file, `.env` files, the model folder and `secrets.toml` are all ignored; only `secrets.toml.example` is tracked |
| Production CSP | The built web app served with `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; …; frame-ancestors 'none'` runs every page, a chart, the "Why?" panel and the assistant with **zero policy violations**, and an injected inline script is blocked |

## Weaknesses found and fixed

| # | Found | Why it mattered | Fix | Proof |
|---|---|---|---|---|
| 1 | The size limit and the "JSON only" rule trusted the `Content-Length` header | A chunked upload declares none, so it skipped **both** checks and the server would read it all into memory | A plain ASGI guard (`api/guards.py`) reads the body itself, counts the bytes that arrive, refuses over 256 KB (413) or non-JSON (415) | Test in-process and against the real server |
| 2 | The session cookie was only `Secure` if an environment variable was set | A site put on HTTPS without that setting would send the cookie in the clear | `Secure` whenever the request is HTTPS (or the flag is set); `Strict-Transport-Security` added over HTTPS | Test |
| 3 | API answers carried no Content-Security-Policy | An API answer should never be treated as a page | `default-src 'none'; frame-ancestors 'none'` on every `/api` answer | Test, live check |
| 4 | Signing in kept the browser's previous session alive and never tidied expired ones | Stale and planted sessions lingered; the table only shrank on demo sign-ins | Every sign-in, sign-up and demo issues a fresh token, retires the one the browser held, and purges expired rows | Two tests |
| 5 | The throttle's memory grew without limit | A stream of one-off usernames (each a new key) could use memory until restart | Expired keys are swept on a timer and by size; at most 20,000 keys are held | Test (20,000 keys, then expiry) |
| 6 | `/analysis`, `/history` and `/scenarios` had no rate limit | One signed-in person could keep the single allocation thread busy and make everyone else see "busy" | Per-person limits of 240 and 90 a minute (generous for dragging a slider, not for a loop) | Test |
| 7 | The page contained an inline theme script | A strict Content-Security-Policy would have blocked it, and the dark theme with it | Moved to `/theme-init.js`; the production policy is defined once (`web/security-headers.ts`) and tested | The browser CSP test failed first, then passed |

Everything else the review looked for held: no endpoint is open by accident, no state-changing call skips CSRF, no route confuses one account's data with another's, nothing secret is stored or returned, and no query is built from text.

## Unresolved limitations (security)

Ordered by how much they matter *before real data is used*. None is a financial matter.

| # | Limitation | Severity for a real pilot | What closing it takes |
|---|---|---|---|
| 1 | **Data is not encrypted at rest.** Profiles, imported holdings and sessions sit in a plain SQLite file | **High** if real family data is ever used | Disk or database encryption on the host, restricted file permissions; a decision for the privacy gate |
| 2 | **Rate limits and lock-outs are per process and in memory.** They reset on restart, and with several workers each keeps its own count | High for a hosted, multi-process pilot; none locally | A shared store (SQLite table or Redis); small change, needs your decision on hosting first |
| 3 | **Behind a reverse proxy every visitor shares the proxy's address**, so the per-address limits (30 sign-in tries per 10 minutes, 10 sign-ups an hour, 30 demos an hour) would apply to everyone together; forwarded-address headers are deliberately not trusted | High if proxied without configuration | Trust the proxy's forwarded address only from a known proxy (a deployment setting), Phase 8 |
| 4 | **Password storage is below today's guidance**: scrypt with N = 2^14 (current guidance is 2^17). It uses a random salt and constant-time comparison, so it is sound, only cheaper to attack offline if the database leaks | Medium | Changing the cost changes the stored hash format, and **the same database is shared with the Streamlit app on `main`**, which would then fail to verify passwords. Needs a versioned hash and a decision about the shared database |
| 4b | No password reset, no email check, no second factor, no common-password check (minimum length 8) | Medium | Product work; out of scope for a prototype |
| 5 | **Sessions**: 12 hours, no idle timeout, no cap on sessions per account; logging out in one browser leaves the account's sessions in other browsers valid | Low to medium | Idle timeout and a "sign out everywhere" action |
| 6 | **Demo sign-in is on by default** and creates throwaway accounts for anyone who can reach the site (bounded by the per-address limit, deleted after 24 hours) | Medium on a public link; fine for a mentor demo | Set `FO_API_DEMO_LOGIN=0` for any real-data pilot |
| 7 | **Interactive API docs are on by default** (`/docs`, `/openapi.json`) and uvicorn announces itself in a `Server` header | Low | Set `FO_API_DOCS=0`; run uvicorn with the server header off (deployment checklist) |
| 8 | **Pillow 12.3.0 has 28 published advisories** (fixed in 13.0.0). Both Streamlit and the embedding library require Pillow below 13, so it cannot be upgraded here. Nothing in the API opens or processes an image | Low (no code path reaches it) | Re-run the audit when Streamlit and fastembed allow 13; do not add image handling meanwhile |
| 9 | **Slow-client attacks are not stopped by the app** (a client that sends a body very slowly holds a connection); `HEAD` on API routes answers 405, which some health probes use | Low locally; relevant when hosted | Reverse-proxy timeouts, a `HEAD` route for health (Phase 8) |
| 10 | **No audit trail** the person can see (sign-ins, imports, who changed a profile), and **no account deletion or data export** | Medium for a pilot with real families (data-protection rights) | Product work for the pilot |
| 11 | **Targeted lock-out is possible**: anyone who knows a username can lock it for ten minutes by guessing | Low (accepted trade-off, recorded since Phase 1) | Per-address plus per-username limits together, once the shared store exists |
| 12 | **Linux and macOS are untested.** WSL and Docker are not installed here, so the suite and the golden master (compared to 1e-9) were only ever run on Windows; the solver's thread problem found in Phase 4 was seen on Windows only | Medium for a hosted pilot | Run the suite on Linux: a CI workflow on a Linux runner would do it, which needs the branch pushed (your decision) |
| 13 | **Browser coverage is Edge (Chromium) only**; Firefox and Safari are untested | Low | Add projects to the Playwright configuration |
| 14 | **The Streamlit app on `main` was not part of this review** and is unchanged; it shares the account database, and it may freeze on Windows because of the solver finding | Medium if it stays live | Retire it at cutover, or review it separately |
| 15 | **The production Content-Security-Policy is proven under `vite preview`**, not on a real host | Low | Re-run `e2e/csp.spec.ts` against the real host in Phase 8 |

## Unresolved limitations (correctness)

* **The liquidity-cover requirement never limits the mix** (it did not bind in any of 24 portfolios in Phase 0; the random-profile tests accept an option being flagged infeasible, but check that it is flagged and never hidden). The screens say so; the model is unchanged. Whether that is acceptable is your call.
* **The golden master covers four families and two cover bases.** The random invariant tests widen that to arbitrary valid profiles but test *properties* (adds up, limits held, no crash), not exact values.
* **"Crash like 2020" and the other scenarios are stylised shocks**, not replays; the wording "In a severe market crash" is still unconfirmed.
* **A profile with zero spending and no commitment in the safety-net window still divides by zero inside the protected engine.** The API refuses it with a clear message (422) instead of crashing.
* **Market history is sample data**, not a licensed feed; every historical figure inherits that.
* **The assistant's router is 79% accurate on fresh questions** (bar 85%); see the Phase 6 report. It never answers with a wrong *number*, only occasionally with a neighbouring question's answer.

## Not done and not verified

* **No Linux run** (limitation 12) and **no hosted run**: everything was exercised locally.
* **No penetration test by another person**, no fuzzing beyond the cases written here, no review by a security professional. This is a careful self-review with executable evidence, not an audit.
* **Visual and manual review is yours**; the browser pane was hidden, so nothing here was judged by eye.
* **`pip-audit` could not use PyPI's advisory feed** (repeated read timeouts); it ran against OSV instead. A second run later is sensible.
* The comprehension check for the assistant (Phase 6) has still not been run by people.

## Decisions needed before Phase 8

1. **Which limitations must be closed before any real family uses the app?** My recommendation: 1 (encryption at rest), 2 and 3 (shared limits and proxy trust, once hosting is chosen), 6 and 7 (settings), and 10 (account deletion and export) are the ones to close; 4 only after deciding what to do about the shared database.
2. **Password hashing cost** (limitation 4): raise it with a versioned hash and stop sharing the database with the Streamlit app, or leave it for the prototype.
3. **Linux verification**: push the branch so a CI workflow can run the suite on Linux, or install WSL or Docker here.
4. **Approve the commit** of Phase 7 to `react-migration` (not pushed).
5. **Approve Phase 8** (documentation and final verification: a clean setup from scratch, builds and migrations, the deployment checklist, known limitations).
6. Open from before: the assistant's accuracy plan; push the branch?; the liquidity-cover fix; the "In a severe market crash" wording; the target-customer decision with the mentor.

## Run it

```powershell
.\.venv\Scripts\python.exe -m pytest -q                      # everything in Python, including the security and financial tests
cd web
npm run typecheck; npm test; npm run build                   # types (app and browser tests), unit tests, production build
npm run e2e                                                  # 29 browser tests in Edge (starts its own servers on ports 8110, 5180, 5181)
```

The browser tests need Microsoft Edge (already on this machine; nothing is downloaded) and use a throwaway database, so they touch no family's data.
