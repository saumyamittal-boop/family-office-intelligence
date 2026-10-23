# ADR-0022: Sign-in: keep our own for now, decide on a managed provider before real data

**Date**: 2026-10-23
**Status**: proposed (nothing has been built or tried; the project owner has not decided)
**Deciders**: Project owner. Input wanted from the mentor. Drafted by Claude.
**Builds on**: [ADR-0010](0010-multi-user-local-accounts.md), [ADR-0016](0016-hosting-and-public-link-protections.md), [ADR-0017](0017-react-fastapi-migration.md). Evidence for the current state: [Phase 7 report](../migration/phase-7-report.md), [production-readiness.md](../production-readiness.md). The plan this belongs to: [plan-sharing-and-deployment.md](../plan-sharing-and-deployment.md).

## Context

The app signs people in itself: usernames and passwords in a SQLite file, scrypt hashes (cost N=2^14, below today's guidance of 2^17), server-side sessions
(only a hash of the token is stored), a CSRF header, per-address and per-username throttles. That design is tested and documented, and it is adequate for a
prototype on synthetic data. Known gaps: no password reset, no email verification, no second factor, no common-password check, a ten-minute lock-out anyone can
trigger by guessing, 12-hour sessions with no idle timeout, and the same database and password format shared with the Streamlit app on `main` (so the hash cost cannot
change without breaking it). The mentor's stack list includes Clerk, a hosted sign-up and sign-in service. Password reset and email verification also need
an email-sending service whichever way we go, so "keep our own" is not free of third parties.

## Decision (proposed)

1. **Until real family data is in scope**, including a shared link for the mentor or a friendly family, **keep our own sign-in**, and put an access gate in front of
   any public address (a proxy password, or an app-level access code) so strangers cannot create accounts.
2. **Make a managed-provider decision a gate item** in [production-readiness.md](../production-readiness.md) section A (item A4), to be taken before any real family is
   invited. Clerk is the leading candidate; the alternatives below are weighed then.
3. **Keep the swap local.** Sign-in is read in one place (`api/deps.py::current_user`) and one module (`api/sessions.py`). Do not spread identity assumptions further.

## Alternatives considered

### Alternative 1: Keep our own and harden it
- **Pros**: no third party holds users' emails; no change to the strict Content-Security-Policy; tests stay simple; works offline.
- **Cons**: we own the security of passwords forever; reset and verification need an email provider anyway; second factor is more work (an authenticator-app standard would be built by hand); a versioned password hash and an end to sharing the database with Streamlit are prerequisites.
- **Why not (yet)**: not rejected. It is the right size for a prototype and the wrong size for a pilot with real families.

### Alternative 2: Clerk (hosted)
- **Pros** (from Clerk's published material, not tried here): reset, email verification, second factor and social sign-in without building them; maintained by specialists; a published free tier (Clerk's own article of February 2026 states 50,000 monthly retained users on the free plan and about $20 to $25 a month for Pro; **check the current pricing page**); React components exist.
- **Cons**:
  - **Users' emails and names sit with a third party**: a data-protection decision (who processes, where, on what terms) before any real person signs up.
  - **Our strict Content-Security-Policy must be loosened.** Clerk's documentation asks for its own front-end API host and Cloudflare's bot-protection host in script sources, its host in connection sources, Cloudflare in frame sources, Clerk's image host, and `worker-src 'self' blob:`. Today the app allows scripts from itself only.
  - **A secret key and a publishable key appear** where none exist today; the API must verify Clerk's session tokens on every request (they are signed tokens checked against the instance's public keys). Clerk's search-visible documentation was JavaScript-focused; **whether its Python support is adequate is unverified** and would be the first thing to test.
  - Our `users` table needs a link to the provider's user id (a migration); throwaway demo accounts would stay ours; the Streamlit app, which shares the database, would not know about Clerk users.
  - Browser tests would need the provider's test mode and keys; the "no outbound calls at run time" statement in [architecture.md](../architecture.md) would stop being true.
  - Vendor lock-in and a recurring cost once the free tier is passed.
- **Why not (yet)**: it solves problems we only have once real people sign up, and it costs us the simplicity and offline behaviour that make the current demo robust.

### Alternative 3: Another managed or self-hosted provider
- **Pros**: some (for example a self-hosted open-source identity server) keep user data on our own machine; others bundle a database.
- **Cons**: self-hosting an identity server is an operations burden larger than the application itself; other managed providers have the same third-party and policy trade-offs as Clerk.
- **Why not**: not compared in detail. Worth a short comparison at the gate, with Clerk as the benchmark.

### Alternative 4: No sign-in for the shared demo (access code only)
- **Pros**: fastest; mirrors the Streamlit app's access-code gate.
- **Cons**: no per-person data, so the mentor could not keep his own edits; the app is built around accounts.
- **Why not**: demo families already give private copies; the gate in point 1 above is this alternative's good part, used on top of our sign-in.

## Consequences

### Positive
- The mentor link can be shared without waiting for an identity decision, and no new third party is introduced for a synthetic-data demo.
- The decision is tied to a clear trigger (real families), and the work is scoped before it is needed.

### Negative
- The password and recovery gaps stay open for the shared-link phase; the access gate limits who can reach them but is not a substitute.
- Doing the managed-provider work later means one more phase before a pilot.

### Risks
- **Someone treats the shared link as safe for real data.** Mitigation: the sign-in page already says "synthetic data only"; the gate is documented as a convenience, not as protection for real data; the readiness checklist stays the gate.
- **The mentor expects Clerk now.** Mitigation: show this record and the trigger; ask whether the expectation is a requirement or a suggestion.
- **Clerk's Python verification or policy changes prove awkward.** Mitigation: a one-day spike (verify a Clerk token in a throwaway FastAPI route, with the loosened policy, in a copy of the app) before committing.

## What would change this decision

Real families being invited; the mentor or an examiner requiring a managed provider; a decision to retire the Streamlit app (which frees the password hash and database); or a data-protection review that rules a third party in or out.
