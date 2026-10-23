# Plan: sharing the app, deploying it, and the sign-in question

> **Status: a proposal.** Nothing in this plan has been built, and none of the third-party services has been tried. Dated 2026-10-23.
> Illustrative simulation, not investment advice. All data in the app is synthetic.

## 1. Where things stand

- The **Streamlit app** on `main` is live from Streamlit Community Cloud (deployed 18 Oct 2026). The remote repository holds only that branch.
- The **React + FastAPI version** (`react-migration`, commit `abcb93f`) runs on the owner's laptop only. It has never been pushed, never run on Linux, never run on a host.
- The mentor is **coming in person on Saturday 24 Oct 2026**, so tomorrow's demo needs no link ([demo-script.md](demo-script.md) for the Streamlit story; a React version of it is step 0 below).
- On 17 Oct he asked for a link he can open on any day, to be deployed by the end of October ([backlog item 10](backlog-from-mentor-feedback.md)). The live Streamlit app already is that link. This plan is about putting the **React version** behind a link as well.
- The tools named for discussion: **Vercel** (deployment), **Cursor** (an AI code editor), **Clerk** (sign-up and sign-in).

## 2. What each tool can and cannot do for us

Facts about the vendors below come from their public documentation as found on 2026-10-23 and have **not been tried**; confirm each on the vendor's own page before relying on it (limits and prices change).

| Tool | Fit | Evidence and caveats |
|---|---|---|
| **Vercel** | **Good for the web app** (a static build). **Poor for our API as it is written** | Python/FastAPI is supported, but functions have a read-only file system with a writable `/tmp` of up to 500 MB, and a bundle limit of 500 MB uncompressed (older pages say 250 MB). Our API keeps a SQLite file, one long-lived engine thread, an in-memory cache and in-memory rate limits; none of these survives serverless functions. A rewrite to an outside address works like a reverse proxy, but Vercel overwrites `X-Forwarded-For`, so on ordinary plans the API would see Vercel, not the visitor (the per-address limits would count everyone as one address) |
| **Clerk** | A real option for sign-in, **not needed for a synthetic-data demo**; see [ADR-0022](adr/0022-authentication-own-or-managed.md) | Hosted sign-up/sign-in with reset, email verification and second factor. Needs a looser Content-Security-Policy (its own hosts plus Cloudflare's bot protection in script, connect and frame sources), a secret key, token verification in the API, a table migration, test keys, and a data-protection decision because users' emails go to a third party. A free tier exists (Clerk states 50,000 monthly retained users from February 2026; Pro about $20 to $25 a month). The search found no Python-specific verification guide, so that is the first thing to test |
| **Cursor** | Just an editor. No role at run time | Fine to use. It sends code to its servers, which is acceptable for this public, synthetic repository and **not** for anything holding real data. Add a rules file (section 6) so any AI editor respects the protected parts |

## 3. Goal and non-goals

**Goal:** by the end of October, the mentor (and later one friendly family-office contact) can open a link to the React version, sign in or choose a demo family, and use every page, with
synthetic data, behind a gate so that strangers cannot.

**Non-goals:** real family data; any claim of compliance, validation or production security; a mobile app; a language model. These stay blocked by
[production-readiness.md](production-readiness.md) section A.

## 4. Hosting options

| | H1. One small host | H2. Vercel for the web app, a separate host for the API | H3. Everything on Vercel |
|---|---|---|---|
| What runs where | One virtual machine or container with a persistent disk: Caddy (or nginx) serves `web/dist` and forwards `/api` to uvicorn on the same machine | `web/dist` on Vercel; `/api` rewritten to the API host; the API host as in H1 without the web files | Web on Vercel; API as Vercel functions |
| Fit with the code as written | **Exact**: this is the layout [deployment-react.md](deployment-react.md) describes, and a same-machine proxy already gives the real visitor address (checked with a hand-sent header) | Needs work: the per-visitor address is lost behind Vercel (see section 2), so either the per-address limits are accepted as shared, or the API reads `x-vercel-forwarded-for` **and** can be sure the request really came through Vercel (a shared secret header, or the API reachable only from Vercel). Untested | Does not fit: needs PostgreSQL, a shared limiter, no single engine thread, and a bundle that fits (numpy, pandas, scipy; the optional embedding library would not) |
| Extra tools | Domain, certificate (Caddy does it), a process manager | Vercel project, the API host, domain; GitHub link or the Vercel command line | Plus a managed database |
| Effort (estimate) | 1 to 2 days including the Linux run | 2 to 3 days plus the spike below | Weeks; not recommended |
| Cost | A small VM; **not priced here** | Vercel plan (check terms for a student project) plus the API host | Vercel plus a database |
| Verdict | **Recommended** for the first link | Only if the mentor specifically wants Vercel. Do a one-day spike first: deploy the built web app and a stub rewrite, send a request, and **read what the API receives** | Reject |

**Choosing the API host** (for H1 and H2) is open. Criteria: a **persistent disk** (or a plan to move to PostgreSQL), one instance only, Linux, a price the owner accepts, and a
region acceptable for a demo. Candidates to compare when the time comes: a small VPS, or one of the container platforms that sell persistent disks. Prices were not checked.

**Pushing the code:** hosts usually deploy from GitHub, and the repository is **public**, so pushing `react-migration` publishes all of it (it contains no secrets; a scan at Phase 7 found none).
Alternatives that avoid a push: upload from the laptop with a host's command-line tool, or copy files to a VM. This is the owner's decision.

## 5. The access gate for a shared link

The Streamlit app has an access code in front of everything; the React version has **no gate**. Anyone who knows an address could open a demo family or create an account (limited by the
rate limits and the 200-account cap, and everything is synthetic, so the harm is small but real: clutter, a held-up engine, someone using it as a free calculator).

| Gate | Needs | Notes |
|---|---|---|
| A password at the proxy (H1) | Two lines of Caddy configuration (basic authentication) | No code change. The mentor types one shared password before the app loads. Recommended |
| An access code inside the app | A small code change mirroring the Streamlit `FO_ACCESS_CODE` | Needed for H2, or if the proxy is not under our control |
| A host feature (password protection on some Vercel plans) | A plan that includes it | Not checked |

Also on any shared deployment: `FO_API_DOCS=0`, `FO_API_COOKIE_SECURE=1`, `FO_API_CORS_ORIGINS` set to the public address, a small `FO_MAX_ACCOUNTS` (for example 20), one API process, a
backup taken and restored once, and a note on the sign-in page that the data is synthetic (already there).

## 5b. A temporary link from the laptop (built 2026-10-23)

For a short-lived link before any real hosting exists. The audit that led to it: [audit-shared-link.md](audit-shared-link.md).

```
 visitor --https--> Cloudflare quick tunnel --> demo/gate.py (127.0.0.1:8200: password, origin check)
                                                   |-- /api/*  -> the API (127.0.0.1:8100, shared-mode settings, fresh private database)
                                                   `-- the rest -> the built web app (127.0.0.1:5181)
```

- **What you run:** double-click `demo\share-demo.cmd`. It stops any running demo, restarts it in shared mode (secure cookie, no interactive API pages, at most 20 sign-ups, fresh database), opens the tunnel, starts the gate with the tunnel's address, **proves from outside that no password is refused and the password works**, then prints a link and a random password and copies both to the clipboard. `demo\stop-demo.cmd` closes everything.
- **One-time setup (needs your approval):** the tunnel program, `cloudflared.exe` (release 2026.10.3, a 55,329,336-byte file) from `https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe`, saved as `demo\bin\cloudflared.exe`. It is git-ignored. After downloading, check its size and its digital signature (`Get-AuthenticodeSignature demo\bin\cloudflared.exe` should say the publisher is Cloudflare) before first use. No account is needed.
- **What the tunnel operator can see:** everything, since it terminates the https connection. That is acceptable only because the data is synthetic.
- **Limits:** the link changes every run; it works only while the laptop is awake and online; a free quick tunnel has no uptime promise; one shared password, no per-person identity; the gate is not a control for real data.
- **Download notes (2026-10-23):** the connection dropped repeatedly after about 2 MB, so two plain downloads were truncated (1.7 MB and 2.4 MB, unsigned). Resuming with `curl -C -` in a loop reached the published size in five rounds. The finished file matched Cloudflare's published size (55,329,336 bytes) and SHA-256 (`76b2805253d0d6ffacb092a7acfbee99e7af6917835c0c5410e23f3ef5052da2`, in the release notes and the release API) and carries a valid Authenticode signature from "Cloudflare, Inc.". If a download is shorter than 55,329,336 bytes, do not run it.
- **Verified (2026-10-23):** `demo\share-demo.cmd` ran end to end; 13 checks through the real public address from this laptop passed (no password refused, wrong password refused, app and JavaScript served with the strict security headers, `/docs` and the API contract not exposed, demo sign-in, `HttpOnly; Secure; SameSite=Lax` cookie, the analysis in 2.5 seconds, a change without the CSRF token refused, with it accepted, a foreign origin refused).
- **Not yet done:** a run from another device and network (a phone on mobile data); a long soak of the free tunnel.

## 6. Ways of working with Cursor (or any AI editor)

Add one short **rules file** at the project root (the same text works as `AGENTS.md`, `CLAUDE.md` or a Cursor rules file):

- Never change an assumption in `fo/engine.py`, `fo/plan.py` or `tests/golden/` without the owner's written approval; the golden-master tests exist to catch it.
- Synthetic data only; never put real client data, a real statement or a real password anywhere.
- Run the three test commands in [testing.md](testing.md) before saying anything works; regenerate the contract and API reference after an API change.
- Do not push, and do not commit unless asked.
- Wording: say "illustrative simulation", not "optimal", "guaranteed" or "compliant".

This also makes it easier to bring in a second engineer: [handover.md](handover.md) and the tests are written for that.

## 7. Work plan

Estimates are mine and rough. "Owner" means you; "Claude" means I can do it in a session once you say so.

| # | When | Step | Who | Done when |
|---|---|---|---|---|
| 0 | Fri 23 to Sat 24 | **In-person demo kit** (built 2026-10-23): `demo\start-demo.cmd` and `stop-demo.cmd`, [demo-script-react.md](demo-script-react.md) with every number checked against the running app (`tools/demo_check.py`, `tests/test_demo_script.py`), and the rehearsal checklist inside it. Still to do: the screen recording | Done by Claude; owner rehearses and records | A cold start takes about 20 seconds and reports "41 of 41 figures … match" (measured once on the development laptop) |
| 1 | Sat 24 | **Ask the mentor**: who the product is for; whether Vercel and Clerk are requirements or suggestions; a friendly family-office contact; the data-licensing route; what he expects by the end of October | Owner | Answers written down in [backlog-from-mentor-feedback.md](backlog-from-mentor-feedback.md) |
| 2 | Sun 25 to Mon 26 | **Linux run.** Either install WSL on the laptop (a Windows feature; needs administrator rights and a restart) or run the tests on the host once it exists. First make the browser-test configuration portable: `web/playwright.config.ts` hard-codes Windows paths (`.venv\Scripts\python.exe`) and the Edge channel, so it cannot start on Linux today | Owner (WSL) and Claude (config change, run, fixes) | `pytest` and the web tests pass on Linux; the golden master matches; the browser tests run with Chromium; any difference found is fixed or written down |
| 3 | Mon 26 | **Decisions**: H1 or H2; the host; the gate; whether to push or upload; the domain name | Owner | Written in an ADR (hosting) |
| 4 | Tue 27 to Wed 28 | **Deploy a staging copy** following [deployment-react.md](deployment-react.md), with the gate and the settings in section 5. Run the smoke tests in that guide. Make `web/e2e/csp.spec.ts` accept a base address so the security-policy check can run against the real host. Back up and restore the database once | Owner (accounts, host), Claude (configuration, tests) | Every item of the smoke list passes on the host; the policy check shows no violation on any page; a restore is proven |
| 5 | Thu 29 to Fri 30 | **Share the link** with the mentor and the password; watch the logs; fix what he hits | Both | The mentor has used it from his own device without help |
| 6 | After | **Sign-in decision** at the readiness gate ([ADR-0022](adr/0022-authentication-own-or-managed.md)), starting with a one-day spike of verifying a Clerk token in a throwaway route | Owner decides, Claude spikes | A recorded decision, with the spike's findings |
| 7 | After | Close the rest of [production-readiness.md](production-readiness.md) section A, in the order the owner chooses | Both | Each item closed or accepted in writing |

If the mentor wants Vercel, replace step 4 with the H2 spike first and add one day.

## 8. Decisions needed from you

1. **Saturday:** is a laptop demo (plus the Streamlit link) enough, with the React link to follow? (Recommended: yes.)
2. **Hosting shape:** H1, or H2 because the mentor wants Vercel? (Recommended: H1 unless he insists; then the H2 spike.)
3. **Push or upload** the React branch, given that the repository is public?
4. **WSL on the laptop** for the Linux run, or run it on the host? (Recommended: WSL, so problems are found before money is spent.)
5. **Gate:** a proxy password (needs H1) or a small in-app code?
6. **Sign-in:** accept ADR-0022 (own sign-in now, provider decision at the real-data gate), or move Clerk forward?

## 9. Risks

- **First Linux run may surface problems** (paths, line endings, the solver's thread behaviour was only ever seen on Windows). Mitigation: step 2 happens before any money or domain is committed, and the tests are the detector.
- **Vercel's address handling** may make per-visitor limits meaningless. Mitigation: H1 by default; the H2 spike measures it.
- **A shared password leaks.** Mitigation: it protects synthetic data only; change it after the mentor's review.
- **Scope creep before Saturday.** Mitigation: step 0 is the only step before the meeting.
- **The link is mistaken for approval for real data.** Mitigation: the sign-in page, the README and the readiness checklist all say otherwise; keep saying it.

## 10. Sources (checked 2026-10-23; not tried)

- Vercel Functions limits: https://vercel.com/docs/functions/limitations
- Vercel FastAPI: https://vercel.com/docs/frameworks/backend/fastapi
- Vercel rewrites and request headers: https://vercel.com/docs/rewrites and https://vercel.com/docs/headers/request-headers
- Clerk pricing: https://clerk.com/articles/clerk-pricing-explained
- Clerk token validation: https://clerk.com/docs/request-authentication/validate-session-tokens
- Clerk Content-Security-Policy: https://clerk.com/docs/guides/secure/best-practices/csp-headers
