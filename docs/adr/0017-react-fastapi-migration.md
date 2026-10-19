# ADR-0017: React and FastAPI front and back end over the unchanged engine

**Date**: 2026-10-19
**Status**: accepted (Phase 1 built; later phases pending approval)
**Deciders**: Project owner, facilitated by Claude (decisions D1 to D10 approved after the Phase 0 report)
**Builds on**: [ADR-0009](0009-streamlit-app-and-stack.md), [ADR-0010](0010-multi-user-local-accounts.md), [ADR-0014](0014-app-structure-and-visual-direction.md) and [ADR-0016](0016-hosting-and-public-link-protections.md)

## Context

The Streamlit prototype works and is deployed, but the project owner wants a personalised dashboard, light and dark
themes, holdings import, a copilot and a path to a hosted pilot, which Streamlit's page model makes awkward. The
financial engine (`fo/`) is the valuable part and must not change. Phase 0 found that the engine, plan, personas,
data, accounts and security modules import no Streamlit, so a backend can wrap them directly. It also found logic
inside the Streamlit pages, a solver-failure flag that nothing read, and two hard-coded assumption sets that were
not on the protected list (see [../protected-assumptions.md](../protected-assumptions.md)).

## Decision

1. **Branch** `react-migration`; Streamlit stays on `main`, live and untouched until the owner approves a cutover (D1).
2. **Golden master first**: `tools/make_golden.py` froze every engine output (4 families x 2 cover bases x scenarios,
   plus the guided plan) before any change. Tests compare the live engine and the HTTP API to it at 1e-9 (D2).
3. **Shared logic moves out of pages** into pure modules both apps use, starting with `fo/profile_form.py` (D3).
4. **Solver failure is visible**: `Portfolio.optimiser_converged` reads `Solution.success`; a failed solve adds an
   explanation line and a banner. No number changes (D4).
5. **The cover basis is explicit** in the API (`basis=all|strict`) and shown in the UI. Defaults are unchanged:
   guided plan strict, analyst views all (D5).
6. **SQLite with numbered SQL migrations** (`api/migrations`, `schema_version`), WAL mode. PostgreSQL is deferred until a
   hosted multi-process pilot needs it; SQL stays inside `api/db.py` and `fo/accounts.py` (D6).
7. **Copilot: rule-based and grounded first**; an LLM only later, optional, off by default, with separate approval (D7).
8. **Dashboard preferences per account**, four featured modules (D8). Built in Phase 4.
9. **Demo sign-ins are private throwaway copies** of a pristine family, deleted after 24 hours (D9).
10. **React 19, Vite, TypeScript, TanStack Query, Recharts, Radix primitives and our own CSS tokens**; no UI kit (D10).

Also decided while building:
- Sessions are server-side; only a SHA-256 hash of the token is stored. The cookie is HttpOnly, SameSite=Lax (Secure over
  HTTPS). State-changing calls need an `X-CSRF-Token` derived from the session by HMAC; JSON only; an Origin allowlist.
- The engine runs on **one dedicated daemon thread** with a request timeout (default 90 s), and answers 503 "busy"
  instead of hanging (see the Phase 1 report for why).
- API dependencies live in `requirements-api.txt`, never the root `requirements.txt` that Streamlit Cloud installs.
- TypeScript is pinned to 5.9.3 because `openapi-typescript` does not yet support TypeScript 7.
- Money is rounded half up in both apps, like percentages (display only; exact ties only).

## Alternatives Considered

### Alternative 1: Keep Streamlit and add FastAPI later
- **Pros**: No rewrite risk; the mentor link keeps working.
- **Cons**: Streamlit cannot deliver the dashboard, theming and import experience asked for.
- **Why not**: The owner chose the React front end; the live link is protected by D1 instead.

### Alternative 2: A full-stack framework (Next.js)
- **Pros**: One repo language, server rendering.
- **Cons**: The engine is Python, so a second backend would be needed anyway.
- **Why not**: Two runtimes with no benefit over a thin API.

### Alternative 3: PostgreSQL from the start
- **Pros**: Concurrency, managed backups.
- **Cons**: A service to run and secure, for a single-user local prototype.
- **Why not**: Not needed until a hosted pilot; the migration path is kept short.

### Alternative 4: An LLM copilot first
- **Pros**: Natural conversation.
- **Cons**: Hallucinated numbers, cost, and client data leaving the machine.
- **Why not**: Explanations can be grounded in engine output deterministically; an LLM may only rephrase later.

## Consequences

### Positive
- The financial numbers are protected by a frozen reference and by tests of the real HTTP API.
- Sign-in survives a page reload, which the Streamlit app cannot do.

### Negative
- Two UIs coexist for a while; some logic is duplicated until the Streamlit pages are retired.
- A hosted React pilot needs a host with a persistent disk; Streamlit Community Cloud cannot run it.

### Risks
- Intermittent unexplained test stalls were seen once during Phase 1; the engine thread and timeout contain the effect, but
  the cause is not found. Mitigation: monitor; move the solver to a worker process if it recurs (Phase 7).
- The throttle is per process and in memory. Mitigation: a shared store in Phase 7.
