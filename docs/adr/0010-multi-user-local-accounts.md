# ADR-0010: Multi-user local accounts

**Date**: 2026-10-17
**Status**: accepted
**Deciders**: Project owner, facilitated by Claude (grill-me session, Q13, Q14, Q15)

## Context

The owner added a requirement for multiple users after the first scoping rounds. It conflicts with an earlier
"no login, no database" choice. It costs an estimated 12 to 20 of the roughly 100 core hours. Free Streamlit
hosting has a disk that resets, which would wipe a local SQLite database.

## Decision

Support separate accounts, each with private family profiles; the market-data snapshot is shared. No roles and
no sharing between accounts. Basic username-and-password login with hashed passwords (standard library
scrypt), a few pre-made demo accounts, and simple self-registration with no email verification and no password
reset. Store data in SQLite. The demo runs locally on one laptop; online hosting is a stretch goal. The app
states that it accepts synthetic data only and that users should not reuse a real password. The walk-forward
backtest was demoted to stretch to pay for this work.

## Alternatives Considered

### Alternative 1: Roles and sharing (CIO edits, family members view)
- **Pros**: Closer to a real family office.
- **Cons**: A sharing model and permission checks.
- **Why not**: Noticeably more work; kept as stretch.

### Alternative 2: Several saved profiles, no logins
- **Pros**: Cheapest.
- **Cons**: Does not meet the multi-user requirement.
- **Why not**: The owner wants separate users.

## Consequences

### Positive
- Per-user data isolation is demonstrable in the demo.

### Negative
- Hours that would have gone to the backtest.

### Risks
- Account work can balloon. Mitigation: cut order #3 drops self-registration; week-4 checkpoint.
