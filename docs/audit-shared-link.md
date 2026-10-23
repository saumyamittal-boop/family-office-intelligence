# Audit: can the React version be put behind a shareable link?

> Illustrative simulation, not investment advice. Synthetic data only. An engineering triage, not a security certification or a compliance review.
> Dated 2026-10-23, commit `abcb93f` plus the uncommitted demo kit. Method: the production-audit checklist, using local evidence only (no outside scanner, nothing uploaded).

**Production audit: 74/100 for a password-gated, synthetic-data demo link (launchable with caveats); under 50/100 for real family data (blocked).**
The first score assumes the gate in `demo/gate.py` is in front of the app. Without it the first would be about 55 ("risky"): any visitor could create accounts.

## Blockers for a shared link (and what was done)

| # | Finding | Evidence | Status |
|---|---|---|---|
| 1 | **No access gate.** The Streamlit version has an access code; the React version has none, so a public address lets anyone open demos or sign up | `fo/settings.py` has `FO_ACCESS_CODE`; nothing in `api/` or `web/` does | **Fixed for a demo**: `demo/gate.py` (password, 10 wrong tries a minute, origin check, 512 KB body cap), 10 unit tests and 15 browser-style checks through a real API |
| 2 | **Per-visitor rate limits would collapse to one address** behind any proxy that does not pass the visitor's address | `request.client.host` is used by `deps.client_ip`; verified earlier that uvicorn honours `X-Forwarded-For` from 127.0.0.1 | **Fixed in the gate**: it sends the tunnel's visitor address to the API; checked (visitor A blocked at the 11th sign-up try, visitor B not) |
| 3 | **Session cookie must be `Secure` on https** | `api/main.py`, `api/routers/auth.py` | **Fixed**: shared mode sets `FO_API_COOKIE_SECURE=1` and the gate sends `X-Forwarded-Proto: https`; checked: `HttpOnly; Secure; SameSite=Lax` |
| 4 | **Interactive API pages on by default** | `api/config.py` | **Fixed**: off in shared mode; the gate never forwards `/docs`; checked |
| 5 | **Sign-ups unbounded** (200 default) | `FO_MAX_ACCOUNTS` | **Fixed**: 20 in shared mode (demo copies do not count) |
| 6 | **The link depends on one laptop** being awake and online | by construction | Accepted for a demo; stated on screen and in the docs |

## High-value fixes (not done)

- **No CI and no Linux run.** There is no `.github/` folder, and everything has only ever run on Windows. Caps this score below 85 and is the largest unknown for any real host. Needs a push or WSL.
- **No outside review** of the security controls (a careful self-review with executable tests, `docs/migration/phase-7-report.md`).
- **The gate is a convenience, not a control for real data**: one shared password, no per-person identity, no audit trail, and a tunnel operator who can see the traffic. See [production-readiness.md](production-readiness.md) section A.
- The gate and the tunnel are only as available as a free, best-effort Cloudflare quick tunnel.
- Browsers other than Edge, and phones over a real network, were not tried.

## Evidence checked

- Git: branch `react-migration`, 10 commits ahead of `origin/main` (271 files), nothing pushed; no CI workflow, no `render.yaml`, `vercel.json`, `fly.toml` or `Procfile`; only the Streamlit `Dockerfile`.
- Secrets: a pattern scan of every tracked file (cloud keys, `sk-`, `ghp_`, private keys, hard-coded passwords) found none; no database, `.env`, snapshot or model file is tracked; `data/` is ignored; `demo/bin/` is now ignored too.
- Dependencies: `npm audit --omit=dev`: 0 vulnerabilities (re-run today). Python: the Phase 7 result stands (advisories in Pillow only; not re-run today).
- Tests: 910 Python (plus 1 expected failure), 548 web, 29 browser; re-run before this audit. Tests for the gate and the demo kit added today.
- Runtime: the demo kit cold-starts in about 20 seconds; the gate was exercised end to end against a separate test API (cookie flags, CSRF, origin, rate limits, headers, lock-out).
- Migrations: forward-only, verified on four database states in Phase 8; the demo uses a fresh database each start.
- Health check: `GET /api/health` opens the database (HEAD answers 405).

## Evidence missing

- A run through the real tunnel from **another device and network** (a phone on mobile data). The tunnel was run on 2026-10-23 and 13 checks through the public address from this laptop passed, but that is still the same machine.
- A Linux or container run; any deployment on a host; any outside reviewer.
- A restore drill for the database (irrelevant to a throwaway demo database, essential for anything real).

## Rollback

For the shared demo: `demo\stop-demo.cmd` closes the link and the demo at once; the database is a throwaway file. Nothing in the repository or the development database is touched by sharing.

## Next action

Open the link on a phone over mobile data (not the home Wi-Fi) and sign in with the password; that is the one check left. Then close it with `demo\stop-demo.cmd`. How the link was made, and the download verification: section 5b of [plan-sharing-and-deployment.md](plan-sharing-and-deployment.md).
